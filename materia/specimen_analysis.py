"""Lot- and specimen-level summaries for prospective validation campaigns."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np


MIN_OUTLIER_GROUP_SIZE = 5
ROBUST_Z_THRESHOLD = 3.5
CONSENSUS_RELATIVE_THRESHOLD_PCT = 5.0


def analyse_specimens(observations: list[dict]) -> dict:
    """Describe dispersion and flag candidates without excluding any measurement.

    Outliers are screened inside each ``(lot, time)`` group.  The primary rule is
    the usual modified z-score based on the median absolute deviation (MAD).
    Small groups are deliberately left unevaluated and flagged values remain in
    every validation metric until a documented laboratory investigation decides
    otherwise.
    """
    grouped: dict[tuple[str, float], list[dict]] = defaultdict(list)
    rows: list[dict] = []
    for index, source in enumerate(observations, 1):
        day = float(source["time_days"])
        value = float(source["modulus_mpa"])
        if not math.isfinite(day) or not math.isfinite(value) or day < 0 or value <= 0:
            raise ValueError("Temps ou module invalide dans l’analyse par éprouvette.")
        replicate = str(source.get("replicate_id") or f"M{index}").strip()
        specimen = str(source.get("specimen_id") or replicate).strip()
        lot = str(source.get("lot_id") or "Lot non renseigné").strip()
        row = {
            "time_days": day,
            "lot_id": lot,
            "specimen_id": specimen,
            "replicate_id": replicate,
            "modulus_mpa": value,
            "outlier_candidate": False,
            "outlier_label": "Non évalué",
            "outlier_reason": "",
            "robust_z": None,
            "included_in_validation": True,
        }
        rows.append(row)
        grouped[(lot, day)].append(row)

    group_rows: list[dict] = []
    unevaluated_groups = 0
    for (lot, day), part in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        values = np.asarray([row["modulus_mpa"] for row in part], dtype=float)
        count = len(values)
        mean = float(np.mean(values))
        sd = float(np.std(values, ddof=1)) if count > 1 else 0.0
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        q1, q3 = (float(value) for value in np.percentile(values, [25, 75]))
        iqr = q3 - q1
        method = "Non évalué : moins de 5 éprouvettes"
        evaluated = count >= MIN_OUTLIER_GROUP_SIZE
        flagged = 0
        if not evaluated:
            unevaluated_groups += 1
            for row in part:
                row["outlier_reason"] = f"Groupe de {count} éprouvette(s) ; minimum {MIN_OUTLIER_GROUP_SIZE} pour le dépistage automatique."
        elif mad > 1e-12:
            method = "Score z modifié sur la MAD · seuil |z| > 3,5"
            for row in part:
                score = 0.6745 * (row["modulus_mpa"] - median) / mad
                row["robust_z"] = float(score)
                row["outlier_candidate"] = abs(score) > ROBUST_Z_THRESHOLD
                row["outlier_label"] = "À vérifier" if row["outlier_candidate"] else "Cohérent"
                row["outlier_reason"] = (
                    f"|z robuste|={abs(score):.2f} > {ROBUST_Z_THRESHOLD:g}." if row["outlier_candidate"]
                    else f"|z robuste|={abs(score):.2f} ≤ {ROBUST_Z_THRESHOLD:g}."
                )
                flagged += int(row["outlier_candidate"])
        elif iqr > 1e-12:
            method = "Règle de Tukey sur l’IQR · bornes Q1−1,5×IQR et Q3+1,5×IQR"
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            for row in part:
                row["outlier_candidate"] = not low <= row["modulus_mpa"] <= high
                row["outlier_label"] = "À vérifier" if row["outlier_candidate"] else "Cohérent"
                row["outlier_reason"] = (
                    f"Valeur hors [{low:.2f} ; {high:.2f}] MPa." if row["outlier_candidate"]
                    else f"Valeur dans [{low:.2f} ; {high:.2f}] MPa."
                )
                flagged += int(row["outlier_candidate"])
        else:
            method = "Consensus répété · écart relatif à la médiane > 5 %"
            for row in part:
                relative_gap = abs(row["modulus_mpa"] - median) / max(abs(median), 1e-12) * 100
                row["outlier_candidate"] = relative_gap > CONSENSUS_RELATIVE_THRESHOLD_PCT
                row["outlier_label"] = "À vérifier" if row["outlier_candidate"] else "Cohérent"
                row["outlier_reason"] = (
                    f"Écart relatif de {relative_gap:.2f} % > {CONSENSUS_RELATIVE_THRESHOLD_PCT:g} % dans un groupe à dispersion robuste nulle."
                    if row["outlier_candidate"] else
                    f"Écart relatif de {relative_gap:.2f} % ≤ {CONSENSUS_RELATIVE_THRESHOLD_PCT:g} %."
                )
                flagged += int(row["outlier_candidate"])

        group_rows.append({
            "time_days": day,
            "lot_id": lot,
            "specimens": count,
            "mean_mpa": mean,
            "sd_mpa": sd,
            "cv_pct": sd / mean * 100 if mean else 0.0,
            "median_mpa": median,
            "minimum_mpa": float(np.min(values)),
            "maximum_mpa": float(np.max(values)),
            "outlier_candidates": flagged,
            "outlier_method": method,
            "outlier_evaluable": evaluated,
        })

    lots = []
    for lot in sorted({row["lot_id"] for row in rows}):
        lot_rows = [row for row in rows if row["lot_id"] == lot]
        lots.append({
            "lot_id": lot,
            "specimens": len(lot_rows),
            "distinct_times": len({row["time_days"] for row in lot_rows}),
            "mean_mpa": float(np.mean([row["modulus_mpa"] for row in lot_rows])),
            "outlier_candidates": sum(bool(row["outlier_candidate"]) for row in lot_rows),
        })

    flagged_count = sum(bool(row["outlier_candidate"]) for row in rows)
    return {
        "method": "Dépistage par lot et par temps : score z modifié fondé sur la MAD ; repli sur l’IQR, puis seuil relatif conservateur de 5 % si les deux dispersions robustes sont nulles.",
        "threshold": f"|z robuste| > {ROBUST_Z_THRESHOLD:g}",
        "minimum_group_size": MIN_OUTLIER_GROUP_SIZE,
        "policy": "Un signalement déclenche une vérification de saisie, d’éprouvette et de protocole. Aucune valeur n’est exclue automatiquement ; toutes restent incluses dans les métriques.",
        "flagged_count": flagged_count,
        "evaluated_groups": len(group_rows) - unevaluated_groups,
        "unevaluated_groups": unevaluated_groups,
        "groups": group_rows,
        "lots": lots,
        "observations": rows,
    }
