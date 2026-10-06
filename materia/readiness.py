"""Input readiness and comparison compatibility checks for student workflows."""
from __future__ import annotations

from typing import Any


def _close(left: float, right: float) -> bool:
    return abs(left-right) <= max(1e-6, abs(right)*.005)


def _evidence_time_days(row: dict) -> float | None:
    if row.get('time_days') is not None:
        return float(row['time_days'])
    if row.get('time_hours') is not None:
        return float(row['time_hours'])/24
    return None


def preparation_assessment(material: dict, module_mpa: float, suggested_module_mpa: float,
                           grade_reference: str, process_state: str, horizon_days: float,
                           exposure: str, evidence_rows: list[dict],
                           immersion_medium: str | None = None) -> dict:
    """Score documentation completeness without claiming scientific confidence."""
    checks=[]; score=0
    grade=(grade_reference or '').strip(); process=(process_state or '').strip()
    if grade:
        score+=15; checks.append({'criterion':'Grade / référence','status':'Prêt','finding':grade[:120]})
    else:
        checks.append({'criterion':'Grade / référence','status':'À compléter','finding':'Préciser le grade ou la référence commerciale.'})
    if not _close(float(module_mpa),float(suggested_module_mpa)):
        score+=20; checks.append({'criterion':'Module initial','status':'Prêt','finding':'Valeur propre au matériau saisie.'})
    else:
        checks.append({'criterion':'Module initial','status':'À compléter','finding':'La valeur générique de famille est encore utilisée.'})
    if process:
        score+=10; checks.append({'criterion':'Procédé / état','status':'Prêt','finding':process[:120]})
    else:
        checks.append({'criterion':'Procédé / état','status':'À compléter','finding':'Préciser le procédé et l’état de conditionnement.'})

    source_count=len({row.get('source_id') or row.get('source_doi') or row.get('source_url')
                      for row in evidence_rows if row.get('source_id') or row.get('source_doi') or row.get('source_url')})
    if evidence_rows:
        score+=30
        checks.append({'criterion':'Données temporelles','status':'Prêt',
                       'finding':f"{len(evidence_rows)} valeurs · {source_count or 1} source(s)."})
        times=[value for row in evidence_rows if (value:=_evidence_time_days(row)) is not None]
        window=max(times) if times else 0
        if window and horizon_days<=window+1e-9:
            score+=15; horizon_status='Prêt'; finding=f"Horizon dans la fenêtre documentaire de {window:g} jours."
        else:
            horizon_status='À vérifier'; finding=f"Horizon au-delà de la fenêtre documentaire de {window:g} jours." if window else 'Fenêtre documentaire non déterminée.'
    else:
        window=0; horizon_status='Exploratoire'; finding='Aucune série temporelle compatible ; estimation de famille.'
        checks.append({'criterion':'Données temporelles','status':'Exploratoire','finding':'Aucune série temporelle compatible avec ce milieu.'})
    checks.append({'criterion':'Horizon','status':horizon_status,'finding':finding})

    if exposure!='immersion' or immersion_medium not in {None,'','unspecified'}:
        score+=10; checks.append({'criterion':'Milieu','status':'Prêt','finding':'Milieu suffisamment précisé pour le calcul.'})
    else:
        checks.append({'criterion':'Milieu','status':'À compléter','finding':'Préciser le liquide d’immersion.'})
    if score>=80:
        label='Entrées bien documentées'; tone='teal'
    elif score>=55:
        label='Calcul possible · éléments à préciser'; tone='amber'
    else:
        label='Préparation incomplète'; tone='amber'
    return {'score':score,'label':label,'tone':tone,'checks':checks,'evidence_window_days':window,
            'material_id':material.get('id'),'scientific_validation':False}


def _input(result: dict, key: str) -> Any:
    return (result.get('manifest',{}).get('inputs') or {}).get(key)


def _property(result: dict) -> str:
    manifest=result.get('manifest') or {}; source=manifest.get('source') or {}
    points=result.get('observed_points') or []
    return str(manifest.get('target_property') or source.get('target_property') or
               (points[0].get('property_name') if points else None) or 'Module de Young')


def _normalized(values: list[Any]) -> set[str]:
    return {str(value).strip().lower() for value in values if value not in {None,''}}


def comparison_assessment(results: list[tuple[str,dict]]) -> dict:
    """Report material differences before drawing a comparison."""
    if not results:
        raise ValueError('Aucun résultat à comparer.')
    checks=[]; score=100; blocked=False
    synthetic_only=all(str(result.get('manifest',{}).get('model','')).startswith('synthetic-') for _,result in results)
    properties=[_property(result) for _,result in results]
    if len(_normalized(properties))>1:
        blocked=True; score=0
        checks.append({'criterion':'Propriété comparée','status':'Bloqué','finding':'Les résultats ne portent pas sur la même propriété.'})
    else:
        checks.append({'criterion':'Propriété comparée','status':'Compatible','finding':properties[0]})
    rules=[
        ('Température','temperature','°C',18),('Humidité','humidity_RH','%',10),
        ('Épaisseur','thickness_mm','mm',10),('Milieu','exposure','',18),
        ('Seuil','threshold','%',10),
    ]
    for label,key,unit,penalty in rules:
        if synthetic_only and key in {'humidity_RH','thickness_mm','exposure'}:
            checks.append({'criterion':label,'status':'Non applicable','finding':'Paramètre absent de l’exercice synthétique.'})
            continue
        values=[_input(result,key) for _,result in results]
        known=[value for value in values if value not in {None,''}]
        distinct=_normalized(known)
        if len(distinct)<=1 and len(known)==len(values):
            finding=f"Valeur commune : {known[0]} {unit}".strip() if known else 'Valeur commune.'
            checks.append({'criterion':label,'status':'Compatible','finding':finding})
        elif not known:
            score-=penalty//2; checks.append({'criterion':label,'status':'Non renseigné','finding':'Information absente des résultats.'})
        else:
            score-=penalty
            shown=', '.join(f"{value} {unit}".strip() for value in known[:4])
            checks.append({'criterion':label,'status':'Différent','finding':shown})
    origins=[]
    for _,result in results:
        from materia.modeling import curve_value_origin
        origins.append(curve_value_origin(result))
    if len(_normalized(origins))>1:
        score-=15; checks.append({'criterion':'Origine des valeurs','status':'Différent','finding':', '.join(origins)})
    else:
        checks.append({'criterion':'Origine des valeurs','status':'Compatible','finding':origins[0]})
    score=max(0,score)
    if blocked:
        label='Comparaison bloquée'; tone='amber'
    elif score>=85:
        label='Conditions comparables'; tone='teal'
    elif score>=60:
        label='Comparaison avec réserves'; tone='amber'
    else:
        label='Comparaison exploratoire'; tone='amber'
    return {'score':score,'label':label,'tone':tone,'can_compare':not blocked,'checks':checks}
