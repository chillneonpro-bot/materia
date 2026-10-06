"""Readable Excel exports for simulations, comparisons and tabular data."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import math
from typing import Any, Iterable

import xlsxwriter

from materia.modeling import curve_value_origin, curve_value_origins
from materia.readiness import comparison_assessment
from materia.validation import validity_diagnostic


MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

BLUE = "#235ABE"
TEAL = "#13958B"
INK = "#172033"
MUTED = "#5F6B7A"
PALE = "#F3F6FB"
PALE_TEAL = "#E8F6F3"
AMBER = "#F5A524"
PALE_AMBER = "#FFF7E6"
RED = "#B42318"


INPUT_LABELS = {
    "material": "Matériau",
    "grade_reference": "Grade / référence commerciale",
    "process_state": "Procédé / état de conditionnement",
    "e0": "Module initial E₀ (MPa)",
    "temperature": "Température d'exposition (°C)",
    "humidity_RH": "Humidité relative (%)",
    "thickness_mm": "Épaisseur (mm)",
    "horizon": "Horizon (jours)",
    "horizon_days": "Horizon (jours)",
    "horizon_years": "Horizon (années)",
    "threshold": "Seuil de module conservé (%)",
    "exposure": "Milieu d'exposition",
    "spread": "Dispersion de sensibilité (%)",
    "seed": "Graine aléatoire",
}


def _safe(value: Any) -> Any:
    """Keep exported text from being interpreted as an Excel formula."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value if math.isfinite(float(value)) else "Non disponible"
    text = str(value)
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def _formats(workbook: xlsxwriter.Workbook) -> dict[str, Any]:
    workbook.set_properties({
        "title": "Résultats Materia",
        "subject": "Vieillissement des polymères et évolution du module de Young",
        "author": "Materia",
        "company": "Materia",
        "comments": "Export scientifique traçable généré par Materia",
    })
    return {
        "title": workbook.add_format({"font_name": "Arial", "font_size": 16, "bold": True, "font_color": INK}),
        "subtitle": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": MUTED, "italic": True}),
        "section": workbook.add_format({"font_name": "Arial", "font_size": 11, "bold": True, "font_color": "#FFFFFF", "bg_color": BLUE, "align": "left", "valign": "vcenter"}),
        "section_teal": workbook.add_format({"font_name": "Arial", "font_size": 11, "bold": True, "font_color": "#FFFFFF", "bg_color": TEAL, "align": "left", "valign": "vcenter"}),
        "label": workbook.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "font_color": INK, "bg_color": PALE, "valign": "top", "text_wrap": True}),
        "value": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "valign": "top", "text_wrap": True}),
        "value_num": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "num_format": "#,##0.00", "valign": "top"}),
        "key": workbook.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "font_color": BLUE, "bg_color": PALE, "border": 1, "border_color": "#DCE3EF", "align": "center", "valign": "vcenter", "text_wrap": True}),
        "big": workbook.add_format({"font_name": "Arial", "font_size": 14, "bold": True, "font_color": INK, "align": "center", "valign": "vcenter"}),
        "big_wrap": workbook.add_format({"font_name": "Arial", "font_size": 12, "bold": True, "font_color": INK, "align": "center", "valign": "vcenter", "text_wrap": True}),
        "small": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": MUTED, "text_wrap": True, "valign": "top"}),
        "warning": workbook.add_format({"font_name": "Arial", "font_size": 9, "font_color": "#7A4E00", "bg_color": PALE_AMBER, "text_wrap": True, "valign": "top"}),
        "status": workbook.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "font_color": "#096B61", "bg_color": PALE_TEAL, "text_wrap": True, "valign": "vcenter"}),
        "url": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": BLUE, "underline": True, "text_wrap": True, "valign": "top"}),
        "header": workbook.add_format({"font_name": "Arial", "font_size": 10, "bold": True, "font_color": "#FFFFFF", "bg_color": BLUE, "align": "center", "valign": "vcenter", "text_wrap": True, "border": 1, "border_color": "#FFFFFF"}),
        "body": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "valign": "top"}),
        "number": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "num_format": "#,##0.00", "valign": "top"}),
        "percent": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "num_format": "0.0", "valign": "top"}),
        "integer": workbook.add_format({"font_name": "Arial", "font_size": 10, "font_color": INK, "num_format": "#,##0", "valign": "top"}),
    }


def _prepare_sheet(sheet: Any, tab_color: str = BLUE) -> None:
    sheet.hide_gridlines(2)
    sheet.set_tab_color(tab_color)
    sheet.set_margins(0.4, 0.4, 0.55, 0.55)
    sheet.set_header("&L&9Materia&C&9Résultats de simulation&R&9Page &P / &N")
    sheet.set_footer("&L&8Export traçable&C&8Les limites et la source sont indiquées dans le classeur&R&8Materia")
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)


def _display_axis(result: dict) -> tuple[list[float], str, float]:
    """Return display values, French unit label and days per displayed unit."""
    manifest = result.get("manifest", {})
    model = str(manifest.get("model", ""))
    times = [float(v) for v in result.get("time", [])]
    if model.startswith("datasheet-screening-"):
        unit = manifest.get("inputs", {}).get("horizon_display", {}).get("unit", "years")
        if unit == "days":
            return [v * 365.25 for v in times], "jours", 1.0
        if unit == "months":
            return [v * 12 for v in times], "mois", 365.25 / 12
        return times, "années", 365.25
    return times, "jours", 1.0


def _time_days(result: dict) -> list[float]:
    manifest = result.get("manifest", {})
    model = str(manifest.get("model", ""))
    factor = 365.25 if model.startswith("datasheet-screening-") else 1.0
    return [float(v) * factor for v in result.get("time", [])]


def _material_name(result: dict) -> str:
    manifest = result.get("manifest", {})
    inputs = manifest.get("inputs", {})
    return str(manifest.get("material_name") or manifest.get("experiment_id") or inputs.get("material") or manifest.get("dataset") or "Résultat Materia")


def _crossing_text(result: dict) -> str:
    manifest = result.get("manifest", {})
    model = str(manifest.get("model", ""))
    value = result.get("crossing_estimate_years") if model.startswith("datasheet-screening-") else result.get("crossing")
    if value is None:
        return "Non atteint"
    value = float(value)
    if model.startswith("datasheet-screening-"):
        months = int(round(value * 12))
        years, remaining = divmod(months, 12)
        parts = []
        if years:
            parts.append(f"{years} an" + ("s" if years > 1 else ""))
        if remaining:
            parts.append(f"{remaining} mois")
        return " et ".join(parts) if parts else "Moins d'un mois"
    return f"{value:,.1f} jours"


def _source(result: dict) -> dict[str, Any]:
    source = dict(result.get("manifest", {}).get("source") or {})
    points = result.get("observed_points") or []
    if points:
        point = points[0]
        source.setdefault("id", point.get("source_id"))
        source.setdefault("title", point.get("source_title") or point.get("source"))
        source.setdefault("url", point.get("source_url"))
        source.setdefault("doi", point.get("source_doi"))
        source.setdefault("location", point.get("source_location") or point.get("location"))
    return source


def _write_title(sheet: Any, fmt: dict[str, Any], title: str, subtitle: str, width: int = 5) -> None:
    sheet.merge_range(0, 0, 0, width, _safe(title), fmt["title"])
    sheet.merge_range(1, 0, 1, width, _safe(subtitle), fmt["subtitle"])
    sheet.set_row(0, 25)
    sheet.set_row(1, 22)


def _section(sheet: Any, fmt: dict[str, Any], row: int, title: str, end_col: int = 5, teal: bool = False) -> int:
    sheet.merge_range(row, 0, row, end_col, title, fmt["section_teal" if teal else "section"])
    sheet.set_row(row, 21)
    return row + 1


def _write_pair(sheet: Any, fmt: dict[str, Any], row: int, label: str, value: Any, end_col: int = 5, value_format: Any | None = None) -> int:
    sheet.write(row, 0, label, fmt["label"])
    sheet.merge_range(row, 1, row, end_col, _safe(value), value_format or fmt["value"])
    sheet.set_row(row, max(20, 15 * (1 + str(value).count("\n"))))
    return row + 1


def _table(sheet: Any, start_row: int, start_col: int, headers: list[str], rows: list[list[Any]], name: str) -> None:
    if not rows:
        return
    sheet.add_table(start_row, start_col, start_row + len(rows), start_col + len(headers) - 1, {
        "name": name,
        "style": "Table Style Medium 2",
        "columns": [{"header": h} for h in headers],
        "data": [[_safe(v) for v in row] for row in rows],
    })


def result_workbook(result: dict, title: str = "Résultat Materia") -> bytes:
    """Build a complete result workbook with summary, curve, source data and limits."""
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True, "constant_memory": False})
    fmt = _formats(workbook)
    summary = workbook.add_worksheet("Synthèse")
    curve = workbook.add_worksheet("Courbe")
    details = workbook.add_worksheet("Origine et méthode")
    points = result.get("observed_points") or []
    observations = workbook.add_worksheet("Mesures source") if points else None
    for sheet, color in ((summary, BLUE), (curve, TEAL), (details, AMBER)):
        _prepare_sheet(sheet, color)
    if observations:
        _prepare_sheet(observations, TEAL)

    manifest = result.get("manifest", {})
    inputs = manifest.get("inputs", {})
    status = manifest.get("status", "Statut non renseigné")
    times, time_label, _ = _display_axis(result)
    modules = [float(v) for v in result.get("modulus", [])]
    lowers = [float(v) for v in result.get("lower", [])]
    uppers = [float(v) for v in result.get("upper", [])]
    retentions = [float(v) for v in result.get("retention", [])]
    outer_lowers = result.get("outer_lower") or []
    outer_uppers = result.get("outer_upper") or []
    has_outer = bool(outer_lowers and outer_uppers and len(outer_lowers) == len(times) == len(outer_uppers))
    if not times or not (len(times) == len(modules) == len(lowers) == len(uppers) == len(retentions)):
        workbook.close()
        raise ValueError("La courbe est incomplète et ne peut pas être exportée.")

    _write_title(summary, fmt, title, "Résultats, paramètres d'origine, source et données de la courbe")
    summary.set_column("A:A", 27)
    summary.set_column("B:F", 16)
    summary.set_column("G:M", 13)
    row = _section(summary, fmt, 3, "Résultats clés", end_col=9)
    summary.write(row, 0, "Matériau / formulation", fmt["key"])
    summary.write(row, 2, "Module initial", fmt["key"])
    summary.write(row, 4, "Module à l'horizon", fmt["key"])
    summary.write(row, 6, "Module conservé", fmt["key"])
    summary.write(row, 8, "Temps au seuil", fmt["key"])
    summary.merge_range(row + 1, 0, row + 2, 1, _safe(_material_name(result)), fmt["big_wrap"])
    summary.merge_range(row + 1, 2, row + 2, 3, modules[0], fmt["big"])
    summary.merge_range(row + 1, 4, row + 2, 5, modules[-1], fmt["big"])
    summary.merge_range(row + 1, 6, row + 2, 7, retentions[-1] / 100, workbook.add_format({"font_name": "Arial", "font_size": 14, "bold": True, "font_color": INK, "align": "center", "valign": "vcenter", "num_format": "0.0%"}))
    summary.merge_range(row + 1, 8, row + 2, 9, _safe(_crossing_text(result)), fmt["big_wrap"])
    summary.write(row + 3, 2, "MPa", fmt["small"])
    summary.write(row + 3, 4, "MPa", fmt["small"])
    row += 5
    row = _section(summary, fmt, row, "Statut et lecture du résultat", end_col=9)
    row = _write_pair(summary, fmt, row, "Statut", status, end_col=9, value_format=fmt["status"])
    row = _write_pair(summary, fmt, row, "Modèle", manifest.get("model", "Non renseigné"), end_col=9)
    row = _write_pair(summary, fmt, row, "Empreinte du calcul", result.get("fingerprint", "Non renseigné"), end_col=9)
    summary.freeze_panes(3, 0)

    curve.set_column("A:A", 16)
    curve.set_column("B:E", 22)
    curve.set_column("F:F", 20)
    curve.set_column("G:G", 16)
    _write_title(curve, fmt, "Courbe de vieillissement", f"Temps en {time_label}. Les bornes représentent l'incertitude ou la plage de sensibilité déclarée.")
    curve_headers = [f"Temps ({time_label})", "Module central (MPa)", "Borne basse (MPa)", "Borne haute (MPa)", "Module conservé (%)", "Seuil (%)", "Origine de la valeur"]
    if has_outer:
        curve_headers += ["Minimum observé du corpus (MPa)", "Maximum observé du corpus (MPa)"]
        curve.set_column("H:I", 24)
    curve.write_row(3, 0, curve_headers, fmt["header"])
    threshold = float(inputs.get("threshold", 80))
    origins = curve_value_origins(result)
    curve_rows = []
    for index,(t,m,lo,hi,r,origin) in enumerate(zip(times,modules,lowers,uppers,retentions,origins)):
        values=[t,m,lo,hi,r,threshold,origin]
        if has_outer:
            values += [outer_lowers[index],outer_uppers[index]]
        curve_rows.append(values)
    for index, values in enumerate(curve_rows, 4):
        curve.write_number(index, 0, values[0], fmt["number"])
        for col in range(1, 4):
            curve.write_number(index, col, values[col], fmt["number"])
        curve.write_number(index, 4, values[4], fmt["percent"])
        curve.write_number(index, 5, values[5], fmt["percent"])
        curve.write(index, 6, values[6], fmt["status"] if values[6] in {"Observé", "Interpolé"} else fmt["warning"])
        if has_outer:
            for col in (7,8):
                if values[col] is None:
                    curve.write_blank(index,col,None,fmt["number"])
                else:
                    curve.write_number(index,col,float(values[col]),fmt["number"])
    last = 3 + len(curve_rows)
    curve.add_table(3, 0, last, len(curve_headers)-1, {"name": "CourbeMateria", "style": "Table Style Medium 2", "columns": [{"header": h} for h in curve_headers]})
    curve.freeze_panes(4, 1)
    chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
    for name, col, color, dash, width in (("Module central", 1, BLUE, "solid", 2.5), ("Borne basse", 2, "#91A3BF", "dash", 1.25), ("Borne haute", 3, TEAL, "dash", 1.25)):
        chart.add_series({
            "name": name,
            "categories": ["Courbe", 4, 0, last, 0],
            "values": ["Courbe", 4, col, last, col],
            "line": {"color": color, "width": width, "dash_type": dash},
        })
    if has_outer:
        for name,col,color in (("Minimum observé",7,"#C7A65B"),("Maximum observé",8,"#7B61FF")):
            chart.add_series({
                "name":name,
                "categories":["Courbe",4,0,last,0],
                "values":["Courbe",4,col,last,col],
                "line":{"color":color,"width":1,"dash_type":"dot"},
            })
    chart.set_title({"name": "Module de Young en fonction du temps"})
    chart.set_x_axis({"name": f"Temps ({time_label})", "major_gridlines": {"visible": False}})
    chart.set_y_axis({"name": "Module de Young (MPa)", "major_gridlines": {"visible": True, "line": {"color": "#E6EAF0"}}, "min": 0})
    chart.set_legend({"position": "top"})
    chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
    chart.set_plotarea({"border": {"color": "#DCE3EF"}, "fill": {"color": "#FFFFFF"}})
    chart.set_size({"width": 760, "height": 410})
    summary.insert_chart("A16", chart)

    _write_title(details, fmt, "Origine et méthode", "Les informations qui permettent de comprendre et de reproduire l'export")
    details.set_column("A:A", 34)
    details.set_column("B:F", 22)
    row = _section(details, fmt, 3, "Paramètres d'origine")
    if manifest.get("material_name"):
        row = _write_pair(details, fmt, row, "Matériau", manifest["material_name"])
    for key, value in inputs.items():
        if key == "horizon_display" and isinstance(value, dict):
            row = _write_pair(details, fmt, row, "Horizon saisi", value.get("label") or f"{value.get('value', '')} {value.get('unit', '')}")
        elif isinstance(value, (dict, list)):
            row = _write_pair(details, fmt, row, INPUT_LABELS.get(key, key), str(value))
        else:
            row = _write_pair(details, fmt, row, INPUT_LABELS.get(key, key), value)
    readiness = manifest.get("input_readiness") or {}
    if readiness:
        row += 1
        row = _section(details, fmt, row, "Préparation des entrées")
        row = _write_pair(details, fmt, row, "Score documentaire", f"{readiness.get('score', 0)}/100 · {readiness.get('label', '')}", value_format=fmt["status"])
        for check in readiness.get("checks", []):
            row = _write_pair(details, fmt, row, check.get("criterion", "Critère"),
                              f"{check.get('status', '')} · {check.get('finding', '')}",
                              value_format=fmt["value"] if check.get("status") == "Prêt" else fmt["warning"])
    row += 1
    source = _source(result)
    row = _section(details, fmt, row, "Source et traçabilité", teal=True)
    for key, label in (("title", "Référence"), ("doi", "DOI"), ("location", "Emplacement dans la source"), ("id", "Identifiant interne")):
        if source.get(key):
            row = _write_pair(details, fmt, row, label, source[key])
    if source.get("url"):
        details.write(row, 0, "Lien source", fmt["label"])
        details.merge_range(row, 1, row, 5, "", fmt["value"])
        details.write_url(row, 1, source["url"], fmt["url"], string=source.get("title") or source["url"])
        row += 1
    validity = manifest.get("validity") or {}
    for key, value in validity.items():
        row = _write_pair(details, fmt, row, {"protocol": "Protocole", "time_days": "Domaine temporel (jours)", "exposure_mode": "Mode d'exposition", "material_scope": "Périmètre matériau"}.get(key, key), value)
    diagnostic = validity_diagnostic(result)
    row += 1
    row = _section(details, fmt, row, "Validité scientifique du résultat", teal=True)
    row = _write_pair(details, fmt, row, "Niveau de preuve", diagnostic["level"], value_format=fmt["status"])
    row = _write_pair(details, fmt, row, "Conclusion", diagnostic["conclusion"])
    for check in diagnostic["checks"]:
        row = _write_pair(
            details,
            fmt,
            row,
            check["criterion"],
            f"{check['status'].upper()} - {check['finding']}",
            value_format=fmt["warning"] if check["status"] != "bon" else fmt["value"],
        )
    row = _write_pair(details, fmt, row, "Expérience recommandée", diagnostic["recommended_experiment"])
    row += 1
    row = _section(details, fmt, row, "Budget d'incertitude")
    for item in diagnostic["uncertainty_budget"]:
        row = _write_pair(
            details,
            fmt,
            row,
            item["component"],
            f"{item['value']} - {item['meaning']}",
            value_format=fmt["value"] if item["quantified"] else fmt["warning"],
        )
    uncertainty = manifest.get("uncertainty") or {}
    if uncertainty:
        row += 1
        row = _section(details, fmt, row, "Incertitude affichée")
        for key in ("label", "interpretation", "coverage", "sample_count", "excludes"):
            if key in uncertainty:
                row = _write_pair(details, fmt, row, {"label": "Nature", "interpretation": "Interprétation", "coverage": "Couverture", "sample_count": "Nombre d'éprouvettes", "excludes": "Non inclus"}[key], uncertainty[key])
    warnings = manifest.get("warnings") or []
    if warnings:
        row += 1
        row = _section(details, fmt, row, "Limites à respecter")
        for index, warning in enumerate(warnings, 1):
            row = _write_pair(details, fmt, row, f"Limite {index}", warning, value_format=fmt["warning"])
    row += 1
    row = _section(details, fmt, row, "Reproductibilité", teal=True)
    row = _write_pair(details, fmt, row, "Date de l'export (UTC)", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    row = _write_pair(details, fmt, row, "Version du modèle", manifest.get("model", "Non renseigné"))
    row = _write_pair(details, fmt, row, "Jeu de données", manifest.get("dataset", "Non renseigné"))
    _write_pair(details, fmt, row, "Empreinte SHA-256", result.get("fingerprint", "Non renseigné"))
    details.freeze_panes(3, 0)

    if observations:
        _write_title(observations, fmt, "Mesures source", "Valeurs d'origine conservées séparément de l'interpolation")
        preferred = [
            "experiment_id", "time_days", "time_hours", "modulus_mpa", "modulus_MPa",
            "standard_deviation_mpa", "sample_count", "initial_modulus_mpa", "initial_modulus_MPa",
            "residual_property", "temperature_C", "humidity_RH", "thickness_mm",
            "measurement_temperature_C", "exposure_mode", "protocol", "source_location",
        ]
        headers = []
        for key in preferred:
            if any(key in p for p in points) and key not in headers:
                headers.append(key)
        obs_rows = [[p.get(key) for key in headers] for p in points]
        header_labels = {
            "experiment_id": "Expérience / formulation", "time_days": "Temps (jours)",
            "time_hours": "Temps (heures)", "modulus_mpa": "Module moyen (MPa)",
            "modulus_MPa": "Module moyen (MPa)", "standard_deviation_mpa": "Écart-type (MPa)",
            "sample_count": "Nombre d'éprouvettes", "initial_modulus_mpa": "Module initial (MPa)",
            "initial_modulus_MPa": "Module initial (MPa)", "residual_property": "Module conservé (E/E₀)",
            "temperature_C": "Exposition (°C)", "humidity_RH": "Humidité relative (%)",
            "thickness_mm": "Épaisseur (mm)", "measurement_temperature_C": "Température d'essai (°C)",
            "exposure_mode": "Mode d'exposition", "protocol": "Protocole d'essai",
            "source_location": "Emplacement dans la source",
        }
        displayed_headers = [header_labels.get(key, key) for key in headers]
        _table(observations, 3, 0, displayed_headers, obs_rows, "MesuresSourceMateria")
        for row_index, point in enumerate(points, 4):
            for col, key in enumerate(headers):
                value = point.get(key)
                cell_format = fmt["small"] if key in {"protocol", "source_location"} else (fmt["number"] if isinstance(value, (int, float)) else fmt["body"])
                observations.write(row_index, col, _safe(value), cell_format)
            observations.set_row(row_index, 32)
        for col, header in enumerate(headers):
            samples = [str(p.get(header, "")) for p in points]
            observations.set_column(col, col, min(42, max(14, len(displayed_headers[col]) + 2, *(len(v) + 1 for v in samples))))
        observations.freeze_panes(4, 2)

    workbook.close()
    return output.getvalue()


def comparison_workbook(results: list[tuple[str, dict]], title: str = "Comparaison Materia") -> bytes:
    """Build a comparison workbook with one native retention chart and full provenance."""
    if not results:
        raise ValueError("Aucun résultat à comparer.")
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    fmt = _formats(workbook)
    summary = workbook.add_worksheet("Synthèse")
    data = workbook.add_worksheet("Comparaison")
    details = workbook.add_worksheet("Origine et limites")
    compatibility = workbook.add_worksheet("Compatibilité")
    for sheet, color in ((summary, BLUE), (data, TEAL), (details, AMBER), (compatibility, TEAL)):
        _prepare_sheet(sheet, color)

    _write_title(summary, fmt, title, "Comparaison des résultats avec leurs paramètres et sources d'origine")
    summary.set_column("A:A", 28)
    summary.set_column("B:F", 20)
    summary.set_column("G:M", 13)
    headers = ["Scénario", "Matériau / formulation", "Module initial (MPa)", "Module final (MPa)", "Conservé (%)", "Temps au seuil", "Origine à l'horizon", "Statut"]
    rows = []
    for name, result in results:
        manifest = result.get("manifest", {})
        rows.append([name, _material_name(result), float(result["modulus"][0]), float(result["modulus"][-1]), float(result["retention"][-1]), _crossing_text(result), curve_value_origin(result), manifest.get("status", "")])
    _table(summary, 3, 0, headers, rows, "SyntheseComparaisonMateria")
    summary.set_column("A:B", 25)
    summary.set_column("C:E", 19)
    summary.set_column("F:F", 22)
    summary.set_column("G:G", 20)
    summary.set_column("H:H", 34)
    summary.freeze_panes(4, 2)

    _write_title(data, fmt, "Courbes comparées", "Temps normalisé en jours pour conserver une unité commune")
    data.set_column("A:A", 27)
    data.set_column("B:B", 16)
    data.set_column("C:F", 21)
    data.set_column("G:G", 16)
    data.write_row(3, 0, ["Scénario", "Temps (jours)", "Module central (MPa)", "Borne basse (MPa)", "Borne haute (MPa)", "Module conservé (%)", "Origine de la valeur"], fmt["header"])
    chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
    colors = [BLUE, TEAL, AMBER, "#7B61FF"]
    current_row = 4
    all_rows: list[list[Any]] = []
    series_ranges = []
    for index, (name, result) in enumerate(results):
        start = current_row
        rows_for_result = []
        for values in zip(_time_days(result), result["modulus"], result["lower"], result["upper"], result["retention"], curve_value_origins(result)):
            row_values = [name, *[float(v) for v in values[:-1]], values[-1]]
            rows_for_result.append(row_values)
            all_rows.append(row_values)
            data.write(current_row, 0, _safe(name), fmt["body"])
            for col, value in enumerate(row_values[1:], 1):
                if col == 6:
                    data.write(current_row, col, value, fmt["status"] if value in {"Observé", "Interpolé"} else fmt["warning"])
                else:
                    data.write_number(current_row, col, value, fmt["percent"] if col == 5 else fmt["number"])
            current_row += 1
        series_ranges.append((name, start, current_row - 1, colors[index % len(colors)]))
    data.add_table(3, 0, current_row - 1, 6, {"name": "ComparaisonMateria", "style": "Table Style Medium 2", "columns": [{"header": h} for h in ["Scénario", "Temps (jours)", "Module central (MPa)", "Borne basse (MPa)", "Borne haute (MPa)", "Module conservé (%)", "Origine de la valeur"]]})
    for name, start, end, color in series_ranges:
        chart.add_series({"name": name, "categories": ["Comparaison", start, 1, end, 1], "values": ["Comparaison", start, 5, end, 5], "line": {"color": color, "width": 2.25}})
    chart.set_title({"name": "Module conservé en fonction du temps"})
    chart.set_x_axis({"name": "Temps (jours)", "major_gridlines": {"visible": False}, "min": 0})
    chart.set_y_axis({"name": "Module conservé (%)", "major_gridlines": {"visible": True, "line": {"color": "#E6EAF0"}}, "min": 0})
    chart.set_legend({"position": "top"})
    chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
    chart.set_plotarea({"border": {"color": "#DCE3EF"}, "fill": {"color": "#FFFFFF"}})
    chart.set_size({"width": 760, "height": 410})
    summary.insert_chart("I4", chart)
    data.freeze_panes(4, 2)

    compatibility_report=comparison_assessment(results)
    _write_title(compatibility, fmt, "Compatibilité de la comparaison", "Différences contrôlées avant le tracé")
    compatibility.set_column("A:A", 25); compatibility.set_column("B:B", 18); compatibility.set_column("C:C", 65)
    compatibility.write(3,0,"Score",fmt["label"])
    compatibility.merge_range(3,1,3,2,f"{compatibility_report['score']}/100 · {compatibility_report['label']}",
                              fmt["status"] if compatibility_report['tone']=='teal' else fmt["warning"])
    _table(compatibility,5,0,["Critère","Statut","Constat"],
           [[row['criterion'],row['status'],row['finding']] for row in compatibility_report['checks']],
           "CompatibiliteMateria")
    compatibility.freeze_panes(6,0)

    _write_title(details, fmt, "Origine et limites", "Paramètres, sources et avertissements propres à chaque scénario")
    details.set_column("A:A", 25)
    details.set_column("B:B", 30)
    details.set_column("C:F", 23)
    row = 3
    for name, result in results:
        manifest = result.get("manifest", {})
        row = _section(details, fmt, row, str(name), teal=True)
        row = _write_pair(details, fmt, row, "Matériau / formulation", _material_name(result))
        row = _write_pair(details, fmt, row, "Statut", manifest.get("status", "Non renseigné"), value_format=fmt["status"])
        row = _write_pair(details, fmt, row, "Modèle", manifest.get("model", "Non renseigné"))
        row = _write_pair(details, fmt, row, "Paramètres d'origine", ", ".join(f"{INPUT_LABELS.get(k, k)} = {v}" for k, v in manifest.get("inputs", {}).items() if k != "horizon_display"))
        source = _source(result)
        if source.get("title"):
            row = _write_pair(details, fmt, row, "Source", source["title"])
        if source.get("doi"):
            row = _write_pair(details, fmt, row, "DOI", source["doi"])
        if source.get("url"):
            details.write(row, 0, "Lien source", fmt["label"])
            details.merge_range(row, 1, row, 5, "", fmt["value"])
            details.write_url(row, 1, source["url"], fmt["url"], string=source.get("title") or source["url"])
            row += 1
        for warning in manifest.get("warnings", []):
            row = _write_pair(details, fmt, row, "Limite", warning, value_format=fmt["warning"])
        row = _write_pair(details, fmt, row, "Empreinte SHA-256", result.get("fingerprint", "Non renseigné"))
        row += 1
    details.freeze_panes(3, 0)

    workbook.close()
    return output.getvalue()


def table_workbook(rows: Iterable[dict], title: str, sheet_name: str = "Données") -> bytes:
    """Export a clean, filterable table when no curve is involved."""
    data_rows = list(rows)
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    fmt = _formats(workbook)
    sheet = workbook.add_worksheet(sheet_name[:31])
    _prepare_sheet(sheet, BLUE)
    _write_title(sheet, fmt, title, "Table filtrable exportée depuis Materia")
    if data_rows:
        headers = list(data_rows[0])
        rows_matrix = [[row.get(header) for header in headers] for row in data_rows]
        _table(sheet, 3, 0, headers, rows_matrix, "TableMateria")
        for col, header in enumerate(headers):
            sample = [str(row.get(header, "")) for row in data_rows[:100]]
            width = min(42, max(12, len(header) + 2, *(len(v) + 1 for v in sample)))
            sheet.set_column(col, col, width)
        sheet.freeze_panes(4, 1)
    else:
        sheet.write(3, 0, "Aucune donnée", fmt["value"])
    workbook.close()
    return output.getvalue()


def blind_validation_template_workbook() -> bytes:
    """Return the minimal prospective-measurement template used after a prediction is frozen."""
    output=BytesIO(); workbook=xlsxwriter.Workbook(output,{"in_memory":True})
    fmt=_formats(workbook); sheet=workbook.add_worksheet("Mesures futures"); guide=workbook.add_worksheet("Mode d'emploi")
    _prepare_sheet(sheet,TEAL); _prepare_sheet(guide,BLUE)
    _write_title(sheet,fmt,"Mesures pour validation aveugle","Une ligne par éprouvette et par temps ; conservez les valeurs brutes")
    headers=["time_days","modulus_mpa","replicate_id","lot_id","specimen_id"]
    samples=[[0,1100,"L1-T0-E1","L1","L1-T0-E1"],[0,1092,"L1-T0-E2","L1","L1-T0-E2"],
             [30,1060,"L1-J30-E1","L1","L1-J30-E1"],[60,1025,"L1-J60-E1","L1","L1-J60-E1"],
             [90,1002,"L1-J90-E1","L1","L1-J90-E1"],[120,980,"L1-J120-E1","L1","L1-J120-E1"]]
    _table(sheet,3,0,headers,samples,"MesuresValidationAveugle")
    sheet.set_column("A:B",20); sheet.set_column("C:E",24); sheet.freeze_panes(4,0)
    _write_title(guide,fmt,"Mode d'emploi","Ces mesures doivent être produites après le gel du fichier de prédiction")
    guide.set_column("A:A",28); guide.set_column("B:F",22)
    row=_section(guide,fmt,3,"Règles du contrôle prospectif")
    for label,value in [
        ("time_days","Temps réel d'exposition en jours, positif ou nul."),
        ("modulus_mpa","Module de Young mesuré en MPa, strictement positif."),
        ("replicate_id","Identifiant unique de l'éprouvette ou de la répétition."),
        ("lot_id","Lot matière indépendant. Utilisez le même identifiant pour toutes les éprouvettes d’un lot."),
        ("specimen_id","Identifiant physique unique de l’éprouvette ; il sert à la vue détaillée."),
        ("Répétitions","Gardez chaque éprouvette sur une ligne. Materia calcule la moyenne et l'écart-type par temps."),
        ("Gel","Ne modifiez jamais le fichier JSON de prédiction après le début des essais."),
    ]:
        row=_write_pair(guide,fmt,row,label,value)
    workbook.close(); return output.getvalue()


def blind_validation_workbook(snapshot: dict, report: dict) -> bytes:
    """Build a reviewable workbook comparing a frozen prediction with future measurements."""
    output=BytesIO(); workbook=xlsxwriter.Workbook(output,{"in_memory":True})
    fmt=_formats(workbook)
    summary=workbook.add_worksheet("Bilan"); curves=workbook.add_worksheet("Prédiction et mesures")
    lots=workbook.add_worksheet("Lots"); specimens=workbook.add_worksheet("Éprouvettes"); trace=workbook.add_worksheet("Traçabilité")
    for sheet,color in ((summary,BLUE),(curves,TEAL),(lots,TEAL),(specimens,BLUE),(trace,AMBER)): _prepare_sheet(sheet,color)
    _write_title(summary,fmt,"Validation aveugle Materia","La prédiction a été figée avant l'ajout des mesures")
    summary.set_column("A:A",30); summary.set_column("B:F",22); summary.set_column("G:M",14)
    row=_section(summary,fmt,3,"Verdict",end_col=7)
    validation=report.get("validation") or {}
    row=_write_pair(summary,fmt,row,"Conclusion",validation.get("label","Non disponible"),end_col=7,value_format=fmt["status"])
    metrics=[
        ("Temps distincts",report.get("distinct_timepoints",report.get("count"))),
        ("Mesures brutes",report.get("observation_count",report.get("count"))),
        ("MAPE",f"{float(report['mape_pct']):.2f} %"),
        ("MAE",f"{float(report['mae_mpa']):.2f} MPa"),
        ("RMSE normalisée",f"{float(report.get('nrmse_pct',0)):.2f} %"),
        ("Biais moyen",f"{float(report['bias_mpa']):+.2f} MPa"),
        ("Couverture P10–P90",f"{float(report['interval_coverage_pct']):.1f} %"),
    ]
    row=_section(summary,fmt,row+1,"Indicateurs",end_col=7,teal=True)
    for label,value in metrics: row=_write_pair(summary,fmt,row,label,value,end_col=7)
    row=_section(summary,fmt,row+1,"Portée de la conclusion",end_col=7)
    row=_write_pair(summary,fmt,row,"Règle",validation.get("scope","Une campagne ne prouve pas la généralisation."),end_col=7,value_format=fmt["warning"])
    analysis=report.get("specimen_analysis") or {}
    row=_section(summary,fmt,row+1,"Contrôle des éprouvettes",end_col=7,teal=True)
    row=_write_pair(summary,fmt,row,"Points à vérifier",analysis.get("flagged_count",0),end_col=7)
    _write_pair(summary,fmt,row,"Politique",analysis.get("policy","Aucune valeur n’est exclue automatiquement."),end_col=7,value_format=fmt["warning"])

    _write_title(curves,fmt,"Prédiction gelée et mesures","Les répétitions sont résumées par une moyenne et un écart-type à chaque temps")
    curves.set_column("A:A",17); curves.set_column("B:H",22)
    curve_times=[float(value)*365.25 for value in snapshot.get("time_years",[])]
    curve_rows=list(zip(curve_times,snapshot.get("central_mpa",[]),snapshot.get("lower_mpa",[]),snapshot.get("upper_mpa",[])))
    curves.write_row(3,0,["Temps prédit (jours)","Central (MPa)","P10 (MPa)","P90 (MPa)"],fmt["header"])
    for rindex,values in enumerate(curve_rows,4):
        for col,value in enumerate(values): curves.write_number(rindex,col,float(value),fmt["number"])
    prediction_last=3+len(curve_rows)
    curves.add_table(3,0,prediction_last,3,{"name":"PredictionGelee","style":"Table Style Medium 2","columns":[{"header":h} for h in ["Temps prédit (jours)","Central (MPa)","P10 (MPa)","P90 (MPa)"]]})
    observed_start=prediction_last+3
    observed_headers=["Temps mesuré (jours)","Moyenne mesurée (MPa)","Écart-type (MPa)","Répétitions","Prédit (MPa)","Erreur relative (%)","Dans P10–P90"]
    curves.write_row(observed_start,0,observed_headers,fmt["header"])
    details=report.get("details") or []
    for offset,item in enumerate(details,1):
        values=[item.get("time_days"),item.get("observed_mpa"),item.get("observed_sd_mpa",0),item.get("replicates",1),item.get("predicted_mpa"),item.get("relative_error_pct"),"Oui" if item.get("covered") else "Non"]
        for col,value in enumerate(values):
            curves.write(observed_start+offset,col,_safe(value),fmt["number"] if isinstance(value,(int,float)) else fmt["body"])
    if details:
        curves.add_table(observed_start,0,observed_start+len(details),len(observed_headers)-1,{"name":"MesuresValidation","style":"Table Style Medium 4","columns":[{"header":h} for h in observed_headers]})
    chart=workbook.add_chart({"type":"scatter","subtype":"straight"})
    for name,col,color,dash,width in (("Central",1,BLUE,"solid",2.5),("P10",2,"#91A3BF","dash",1.2),("P90",3,TEAL,"dash",1.2)):
        chart.add_series({"name":name,"categories":["Prédiction et mesures",4,0,prediction_last,0],"values":["Prédiction et mesures",4,col,prediction_last,col],"line":{"color":color,"dash_type":dash,"width":width}})
    if details:
        chart.add_series({"name":"Mesures futures","categories":["Prédiction et mesures",observed_start+1,0,observed_start+len(details),0],"values":["Prédiction et mesures",observed_start+1,1,observed_start+len(details),1],"line":{"none":True},"marker":{"type":"circle","size":7,"border":{"color":INK},"fill":{"color":AMBER}}})
    chart.set_title({"name":"Contrôle de la prédiction figée"}); chart.set_x_axis({"name":"Temps (jours)","min":0}); chart.set_y_axis({"name":"Module de Young (MPa)","min":0})
    chart.set_legend({"position":"top"}); chart.set_size({"width":780,"height":420}); summary.insert_chart("I4",chart)
    curves.freeze_panes(4,1)

    _write_title(lots,fmt,"Vue par lot et par temps","Dispersion calculée sur toutes les éprouvettes ; les signalements ne suppriment aucune valeur")
    lots.set_column("A:B",18); lots.set_column("C:J",20); lots.set_column("K:K",55)
    group_headers=["Temps (jours)","Lot","Éprouvettes","Moyenne (MPa)","Écart-type (MPa)","CV (%)","Médiane (MPa)","Minimum (MPa)","Maximum (MPa)","À vérifier","Méthode"]
    group_rows=[]
    for item in analysis.get("groups",[]):
        group_rows.append([item.get("time_days"),item.get("lot_id"),item.get("specimens"),item.get("mean_mpa"),item.get("sd_mpa"),item.get("cv_pct"),item.get("median_mpa"),item.get("minimum_mpa"),item.get("maximum_mpa"),item.get("outlier_candidates"),item.get("outlier_method")])
    _table(lots,3,0,group_headers,group_rows,"LotsValidation")
    lots.freeze_panes(4,2)

    _write_title(specimens,fmt,"Vue par éprouvette","Chaque valeur brute reste incluse dans les métriques ; vérifiez tout signalement dans le cahier de laboratoire")
    specimens.set_column("A:B",17); specimens.set_column("C:E",24); specimens.set_column("F:G",18); specimens.set_column("H:H",55); specimens.set_column("I:I",20)
    specimen_headers=["Temps (jours)","Lot","Éprouvette","Répétition","Module (MPa)","Statut atypique","z robuste","Justification","Incluse dans la validation"]
    specimen_rows=[]
    for item in analysis.get("observations",[]):
        specimen_rows.append([item.get("time_days"),item.get("lot_id"),item.get("specimen_id"),item.get("replicate_id"),item.get("modulus_mpa"),item.get("outlier_label"),item.get("robust_z"),item.get("outlier_reason"),"Oui" if item.get("included_in_validation",True) else "Non"])
    _table(specimens,3,0,specimen_headers,specimen_rows,"EprouvettesValidation")
    specimens.freeze_panes(4,2)

    _write_title(trace,fmt,"Traçabilité","Empreinte, date de gel, modèle et paramètres annoncés avant les essais")
    trace.set_column("A:A",30); trace.set_column("B:F",24)
    row=_section(trace,fmt,3,"Prédiction figée")
    for label,key in (("Titre","title"),("Gel UTC","frozen_at"),("Date de coupure documentaire","data_cutoff"),("Format","format"),("Modèle","model"),("Empreinte du modèle","model_fingerprint"),("Empreinte du fichier","lock_sha256")):
        row=_write_pair(trace,fmt,row,label,snapshot.get(key,"Non renseigné"))
    row=_section(trace,fmt,row+1,"Paramètres annoncés")
    for key,value in (snapshot.get("inputs") or {}).items(): row=_write_pair(trace,fmt,row,INPUT_LABELS.get(key,key),value)
    source=snapshot.get("source") or {}; row=_section(trace,fmt,row+1,"Corpus documentaire",teal=True)
    for label,key in (("Référence","title"),("DOI","doi"),("Emplacement","location")):
        if source.get(key): row=_write_pair(trace,fmt,row,label,source[key])
    if source.get("url"):
        trace.write(row,0,"Lien source",fmt["label"]); trace.merge_range(row,1,row,5,"",fmt["value"]); trace.write_url(row,1,source["url"],fmt["url"],string=source.get("title") or source["url"])
        row+=1
    row=_section(trace,fmt,row+1,"Détection des valeurs atypiques",teal=True)
    for label,value in (("Méthode",analysis.get("method")),("Seuil",analysis.get("threshold")),("Taille minimale par groupe",analysis.get("minimum_group_size")),("Politique",analysis.get("policy"))):
        row=_write_pair(trace,fmt,row,label,value or "Non renseigné",value_format=fmt["warning"] if label=="Politique" else fmt["value"])
    workbook.close(); return output.getvalue()
