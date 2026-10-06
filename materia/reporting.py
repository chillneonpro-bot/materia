"""Human-readable, reproducible reports for simulations and observations."""
from __future__ import annotations

from datetime import datetime, timezone

from materia.modeling import (curve_value_origin, evidence_assessment,
                              format_years_months, sampled_curve_rows)


def _clean(value: object) -> str:
    return str(value if value is not None else 'Non renseigné').replace('\n',' ').strip()


def markdown_report(result: dict, title: str = 'Rapport Materia') -> bytes:
    manifest=result.get('manifest',{}); inputs=manifest.get('inputs',{}); model=str(manifest.get('model','inconnu'))
    title=_clean(title)[:200]; status=_clean(manifest.get('status','Statut inconnu'))
    display=inputs.get('horizon_display',{}) if model.startswith('datasheet-screening-') else {}
    unit={'days':'jours','months':'mois','years':'années'}.get(display.get('unit'),'années' if model.startswith('datasheet-screening-') else 'jours')
    lines=[f'# {title}','',f'**Généré le :** {datetime.now(timezone.utc).isoformat()}',
           f'**Modèle :** `{model}`',f'**Statut :** {status}',f'**Empreinte :** `{_clean(result.get("fingerprint"))}`','']
    if model.startswith('datasheet-screening-'):
        assessment=evidence_assessment(result)
        crossing=result.get('crossing_estimate_years'); lo,hi=result.get('crossing_interval',[None,None])
        horizon_text=display.get('label') or f"{float(inputs['horizon_years']):g} ans"
        lines += ['## Résultat', '', f"- Matériau : {_clean(manifest.get('material_name'))}",
                  f"- Grade / référence : {_clean(inputs.get('grade_reference'))}",
                  f"- Procédé / état : {_clean(inputs.get('process_state'))}",
                  f"- Niveau de preuve : {assessment['level']} — {assessment['label']}",
                  f"- Module initial : {float(inputs['e0']):g} MPa",
                  f"- Module conservé à l’horizon : {float(result['retention'][-1]):.1f} %",
                  f"- Origine de la valeur à l’horizon : {curve_value_origin(result)}",
                  f"- Franchissement central : {format_years_months(float(crossing))}",
                  f"- Plage de sensibilité : {format_years_months(float(lo))} à {format_years_months(float(hi))}",
                  '', '## Paramètres', '',
                  f"- Température : {float(inputs['temperature']):g} °C",
                  f"- Humidité relative : {float(inputs['humidity_RH']):g} %",
                  f"- Épaisseur : {float(inputs['thickness_mm']):g} mm",
                  f"- Milieu : {_clean(inputs['exposure'])}",
                  f"- Horizon saisi : {_clean(horizon_text)}",
                  f"- Seuil : {float(inputs['threshold']):g} %",'']
    elif model.startswith('piecewise-linear-published-'):
        lines += ['## Résultat', '', f"- Série : {_clean(manifest.get('experiment_id'))}",
                  f"- Module initial : {float(inputs['e0']):g} MPa",
                  f"- Module conservé à l’horizon : {float(result['retention'][-1]):.1f} %",
                  f"- Origine de la valeur à l’horizon : {curve_value_origin(result)}",
                  f"- Horizon : {float(inputs['horizon_days']):g} jours",
                  '- Méthode : interpolation linéaire entre les temps publiés, sans extrapolation','']
    else:
        crossing=result.get('crossing')
        lines += ['## Résultat pédagogique', '',
                  f"- Module initial : {float(inputs.get('e0',result['modulus'][0])):g} MPa",
                  f"- Module conservé à l’horizon : {float(result['retention'][-1]):.1f} %",
                  f"- Origine de la valeur à l’horizon : {curve_value_origin(result)}",
                  f"- Franchissement : {float(crossing):g} jours" if crossing is not None else '- Franchissement : non atteint',
                  '- Nature : scénario synthétique, sans validation matérielle','']
    warnings=manifest.get('warnings',[])
    if warnings:
        lines += ['## Limites','']+[f'- {_clean(item)}' for item in warnings]+['']
    if manifest.get('prohibited_use'):
        lines += [f"**Usage interdit :** {_clean(manifest['prohibited_use'])}",'']
    source=manifest.get('source') or {}
    if source:
        lines += ['## Source','',f"- {_clean(source.get('title') or source.get('id'))}",
                  f"- {_clean(source.get('url') or source.get('location'))}",'']
    rows=sampled_curve_rows(result,time_unit=None if model.startswith('datasheet-screening-') else unit)
    lines += ['## Valeurs principales','',f'| Temps ({unit}) | Module central (MPa) | Borne basse | Borne haute | Conservation (%) | Origine |',
              '|---:|---:|---:|---:|---:|:---|']
    lines += [f"| {row['temps']:g} | {row['module_mpa']:g} | {row['module_min_mpa']:g} | {row['module_max_mpa']:g} | {row['retention_pct']:g} | {row['origine']} |" for row in rows]
    lines += ['', '---', 'Ce rapport décrit le calcul et les données disponibles dans Materia. Il ne constitue pas une qualification industrielle.','']
    return '\n'.join(lines).encode('utf-8')
