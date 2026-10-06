"""Transparent validation and applicability diagnostics for Materia results."""
from __future__ import annotations

import math
import numpy as np


EXTERNAL_PP_REFERENCE = {
    'title': 'Aging Study of Plastics to Be Used as Radiative Cooling Wind-Shields for Night-Time Radiative Cooling—Polypropylene as an Alternative to Polyethylene',
    'doi': '10.3390/en15228340',
    'url': 'https://www.mdpi.com/1996-1073/15/22/8340',
    'scope': 'Film PP-35 de 35,8 µm, exposition naturelle 90 jours à Lleida, ISO 527, n=5.',
    'decision': 'EXCLUE DE LA VALIDATION NUMÉRIQUE',
    'reason': ('Les valeurs publiées à 0 et 90 jours ne conservent pas toujours la même orientation '
               'd’éprouvette et cette formulation en film n’est pas le PP H301 retransformé du corpus principal.'),
}


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _error_metrics(details: list[dict]) -> dict:
    observed=np.asarray([row['observed_mpa'] for row in details],dtype=float)
    predicted=np.asarray([row['predicted_mpa'] for row in details],dtype=float)
    residual=observed-predicted
    denominator=float(np.sum((observed-observed.mean())**2))
    return {
        'mae_mpa':float(np.mean(np.abs(residual))),
        'rmse_mpa':float(np.sqrt(np.mean(residual**2))),
        'mape_pct':float(np.mean(np.abs(residual)/observed)*100),
        'r2':float(1-np.sum(residual**2)/denominator) if denominator>0 else None,
        'max_relative_error_pct':float(np.max(np.abs(residual)/observed)*100),
    }


def _pp_anchor_values(group: list[dict]) -> tuple[float,float,float] | None:
    """Return the exact 0/30/120-day anchors, independently of row order or extra times."""
    by_time={float(row['time_days']):float(row['modulus_mpa']) for row in group
             if _finite(row.get('time_days')) and _finite(row.get('modulus_mpa'))}
    if not {0.,30.,120.}.issubset(by_time) or any(by_time[time]<=0 for time in (0.,30.,120.)):
        return None
    return by_time[0.],by_time[30.],by_time[120.]


def pp_model_benchmark(rows: list[dict]) -> dict:
    """Compare honest 0/30 -> 120 day strategies with leave-one-formulation-out transfer."""
    groups={experiment_id:sorted((r for r in rows if r['experiment_id']==experiment_id),
                                  key=lambda r:float(r['time_days']))
            for experiment_id in sorted({r['experiment_id'] for r in rows})}
    groups={key:value for key,value in groups.items() if _pp_anchor_values(value) is not None}
    if len(groups)<3:
        raise ValueError('Au moins trois formulations PP complètes sont requises pour comparer les modèles.')
    methods={
        'hierarchical_two_phase':{'label':'Deux phases, transfert hiérarchique'},
        'persistence':{'label':'Palier après 30 jours'},
        'peer_median_retention':{'label':'Rétention médiane des formulations paires'},
        'exponential':{'label':'Exponentiel ajusté sur 0 et 30 jours'},
        'linear':{'label':'Tendance linéaire 0-30 jours'},
    }
    for method in methods:
        methods[method]['details']=[]
    for experiment_id,group in groups.items():
        e0,e30,e120=_pp_anchor_values(group)
        peers=[peer for key,peer in groups.items() if key!=experiment_id]
        phase_ratios=[]
        for peer in peers:
            p0,p30,p120=_pp_anchor_values(peer)
            early_loss=p0-p30
            if early_loss>0:
                phase_ratios.append((p30-p120)/early_loss)
        if not phase_ratios:
            raise ValueError('Les formulations paires ne permettent pas d’estimer le ralentissement après 30 jours.')
        phase_ratio=float(np.median(phase_ratios))
        peer_retention=float(np.median([float(peer[2]['modulus_mpa'])/float(peer[0]['modulus_mpa']) for peer in peers]))
        predictions={
            'hierarchical_two_phase':e30-phase_ratio*(e0-e30),
            'persistence':e30,
            'peer_median_retention':e0*peer_retention,
            'exponential':e30*np.exp(np.log(e30/e0)/30*90),
            'linear':e30+(e30-e0)/30*90,
        }
        sd=float(group[2].get('standard_deviation_mpa') or 0)
        for method,predicted in predictions.items():
            error=float(predicted-e120)
            methods[method]['details'].append({
                'formulation':experiment_id,'observed_mpa':e120,'predicted_mpa':float(predicted),
                'error_mpa':error,'absolute_error_mpa':abs(error),
                'relative_error_pct':abs(error)/e120*100,
                'within_reported_sd':bool(sd and abs(error)<=sd),'test_sd_mpa':sd,
                'phase_ratio_from_peers':phase_ratio if method=='hierarchical_two_phase' else None,
            })
    ranking=[]
    for method,payload in methods.items():
        payload.update(_error_metrics(payload['details']))
        payload['within_reported_sd_count']=sum(row['within_reported_sd'] for row in payload['details'])
        ranking.append({'method':method,'label':payload['label'],
                        **{key:payload[key] for key in ('mae_mpa','rmse_mpa','mape_pct','r2','max_relative_error_pct','within_reported_sd_count')}})
    ranking.sort(key=lambda row:row['mae_mpa'])
    best=ranking[0]['method']
    return {
        'methods':methods,'ranking':ranking,'recommended_method':best,
        'protocol':'Chaque formulation cible utilise ses valeurs à 0 et 30 jours. Le ralentissement 30-120 jours est estimé uniquement sur les autres formulations.',
        'limitation':'Quatre formulations d’une seule publication : comparaison interne, sans validation sur un autre grade ni une autre campagne.',
    }


def pp_short_term_prediction(initial_mpa: float, day30_mpa: float, rows: list[dict]) -> dict:
    """Predict the 120-day mean after a 30-day anchor using the audited phase-ratio model."""
    if not _finite(initial_mpa) or not _finite(day30_mpa) or initial_mpa<=0 or day30_mpa<=0:
        raise ValueError('Les modules à 0 et 30 jours doivent être positifs.')
    if day30_mpa>initial_mpa*1.25:
        raise ValueError('La hausse à 30 jours dépasse 25 % ; ce cas sort du domaine PP audité.')
    groups=[]
    for experiment_id in sorted({r['experiment_id'] for r in rows}):
        group=sorted((r for r in rows if r['experiment_id']==experiment_id),key=lambda r:float(r['time_days']))
        anchors=_pp_anchor_values(group)
        if anchors is not None:
            e0,e30,e120=anchors
            if e0>e30 and e30>0:
                groups.append((e30-e120)/(e0-e30))
    if len(groups)<3:
        raise ValueError('Corpus PP insuffisant pour l’estimation en deux phases.')
    ratio=float(np.median(groups)); predicted=float(day30_mpa-ratio*(initial_mpa-day30_mpa))
    benchmark=pp_model_benchmark(rows); half_width_pct=benchmark['methods']['hierarchical_two_phase']['max_relative_error_pct']
    return {
        'predicted_120_mpa':predicted,
        'lower_120_mpa':predicted*(1-half_width_pct/100),
        'upper_120_mpa':predicted*(1+half_width_pct/100),
        'retention_120_pct':predicted/initial_mpa*100,
        'phase_ratio':ratio,'empirical_half_width_pct':half_width_pct,
        'status':'ESTIMATION INTERNE PP - VALIDATION EXTERNE REQUISE',
        'meaning':'Enveloppe empirique construite avec les erreurs hors formulation du corpus ; elle ne couvre pas le transfert vers un autre grade.',
    }


def pp_temporal_holdout(rows: list[dict]) -> dict:
    """Return the best audited internal model while retaining all baselines."""
    benchmark=pp_model_benchmark(rows); selected=benchmark['methods'][benchmark['recommended_method']]
    return {
        'method':selected['label'],'split':benchmark['protocol'],
        'independence':'Validation croisée interne par formulation : quatre formulations, une seule publication',
        **{key:selected[key] for key in ('mae_mpa','rmse_mpa','mape_pct','r2','within_reported_sd_count')},
        'test_count':len(selected['details']),'details':selected['details'],
        'empirical_half_width_pct':selected['max_relative_error_pct'],
        'status':'MODÈLE INTERNE AMÉLIORÉ - VALIDATION EXTERNE REQUISE',
        'conclusion':('Le modèle en deux phases tient compte du ralentissement après 30 jours. '
                      'Il réduit fortement l’erreur interne, mais exige une mesure à 30 jours et ne démontre pas le transfert à un autre grade.'),
        'benchmark':benchmark,'external_reference':EXTERNAL_PP_REFERENCE,
    }


def uncertainty_budget(result: dict) -> list[dict]:
    """Separate the uncertainty sources that the result actually contains."""
    manifest=result.get('manifest',{}); model=str(manifest.get('model',''))
    rows=[]
    center=float(result['modulus'][-1]); lower=float(result['lower'][-1]); upper=float(result['upper'][-1])
    shown=(upper-lower)/(2*center)*100 if center else None
    uncertainty=manifest.get('uncertainty') or {}
    if uncertainty:
        rows.append({'component':'Mesure / éprouvettes','value':uncertainty.get('label','Bande publiée'),
                     'quantified':True,'meaning':uncertainty.get('interpretation') or 'Composante déclarée dans la source.'})
    else:
        rows.append({'component':'Mesure / éprouvettes','value':'Non quantifiée','quantified':False,
                     'meaning':'Aucune répétition compatible n’est disponible pour ce résultat.'})
    rows.append({'component':'Bande affichée à l’horizon','value':f'± {shown:.1f} % autour de la courbe centrale' if shown is not None else 'Non calculable',
                 'quantified':shown is not None,'meaning':'Largeur provenant du calcul actuellement affiché.'})
    if model.startswith('datasheet-screening-'):
        assumptions=manifest.get('assumptions',{}); multiple=assumptions.get('extrapolation_multiple')
        rows.append({'component':'Extrapolation temporelle','value':f'× {multiple:.1f} la durée observée' if _finite(multiple) else 'Non quantifiée',
                     'quantified':_finite(multiple),'meaning':'Cette composante n’est pas incluse dans un intervalle statistique validé.'})
        rows.append({'component':'Transfert de formulation','value':'Non quantifié', 'quantified':False,
                     'meaning':'Le grade, les additifs et le procédé peuvent modifier la cinétique.'})
    else:
        rows.append({'component':'Transfert à un autre matériau ou milieu','value':'Non quantifié', 'quantified':False,
                     'meaning':'La bande ne couvre pas le changement de formulation, de lot, de géométrie ou de climat.'})
    return rows


def validity_diagnostic(result: dict) -> dict:
    """Explain whether a result interpolates, extrapolates or only illustrates assumptions."""
    manifest=result.get('manifest',{}); model=str(manifest.get('model','')); inputs=manifest.get('inputs',{})
    checks=[]
    if model.startswith('piecewise-linear-published-'):
        horizon=float(inputs.get('horizon_days',0)); limit=float((manifest.get('validity',{}).get('time_days') or [0,0])[-1])
        checks=[
            {'criterion':'Source numérique','status':'bon','finding':'Valeurs publiées, source et protocole conservés.'},
            {'criterion':'Temps','status':'bon' if horizon<=limit else 'bloquant','finding':f'Horizon {horizon:g} jours ; observation jusqu’à {limit:g} jours.'},
            {'criterion':'Formulation','status':'attention','finding':'Valable uniquement pour la formulation exacte de l’article.'},
            {'criterion':'Transfert climatique','status':'attention','finding':'Les conditions météorologiques ne sont pas transférées à un autre site.'},
        ]
        level='Interpolation publiée' if horizon<=limit else 'Hors domaine'
        conclusion='Le résultat reste dans la fenêtre temporelle publiée.' if horizon<=limit else 'Le résultat dépasse le domaine publié.'
        recommendation='Tester le grade cible dans son environnement réel avec au moins trois temps et des répétitions.'
    elif model.startswith('piecewise-linear-observed-'):
        accepted=manifest.get('material_status')=='ACCEPTED'
        checks=[
            {'criterion':'Revue scientifique','status':'bon' if accepted else 'bloquant','finding':'Lot accepté.' if accepted else 'Lot encore en attente.'},
            {'criterion':'Temps et conditions','status':'bon','finding':'Interpolation aux conditions exactes, sans extrapolation.'},
            {'criterion':'Incertitude','status':'attention','finding':'La numérisation ne couvre pas toute la variabilité expérimentale.'},
        ]
        level='Corpus accepté limité' if accepted else 'Aperçu non validé'
        conclusion='Interpolation utilisable pour l’enseignement dans le domaine observé.' if accepted else 'Ce résultat ne peut pas servir de preuve.'
        recommendation='Ajouter une campagne indépendante et les données brutes par éprouvette.'
    elif model.startswith('datasheet-screening-'):
        calibrated=manifest.get('evidence_level') in {'calibrated_short_term','evidence_informed_short_term'}
        multiple=(manifest.get('assumptions') or {}).get('extrapolation_multiple')
        if calibrated and _finite(multiple):
            time_status='bon' if multiple<=1 else 'attention' if multiple<=3 else 'bloquant'
            time_finding=(f'Horizon dans la fenêtre comparable (× {multiple:.1f}).' if multiple<=1 else
                          f'Extrapolation limitée à × {multiple:.1f} la fenêtre observée.' if multiple<=3 else
                          f'Horizon × {multiple:.1f} la fenêtre observée : durée de vie non démontrée.')
        else:
            time_status='attention'; time_finding='Horizon couvert par une loi de famille, sans fenêtre expérimentale propre au grade.'
        checks=[
            {'criterion':'Module initial','status':'attention','finding':'Valeur de fiche ou valeur saisie ; le grade et le conditionnement doivent correspondre.'},
            {'criterion':'Cinétique','status':'attention','finding':'Profil en deux phases informé par un corpus court.' if calibrated else 'Meilleure estimation de famille, modulée par les conditions saisies.'},
            {'criterion':'Extrapolation','status':time_status,'finding':time_finding},
            {'criterion':'Formulation et procédé','status':'attention','finding':'Additifs, cristallinité, contraintes et lot non décrits.'},
        ]
        level='Extrapolation à confirmer' if calibrated else 'Estimation de présélection'
        conclusion=('Le calcul prolonge un profil documentaire ; la confiance diminue hors de la fenêtre publiée.' if calibrated else
                    'Le calcul fournit une estimation centrale utilisable en présélection, avec une confiance limitée par le transfert de famille.')
        recommendation='Mesurer E(t) sur le grade exact à 0, 25, 50, 75 et 100 % de l’horizon visé, avec au moins cinq éprouvettes par temps.'
    else:
        checks=[{'criterion':'Nature du cas','status':'bloquant','finding':'Paramètres synthétiques sans matériau réel.'}]
        level='Démonstration synthétique'; conclusion='Ce résultat sert uniquement à apprendre le fonctionnement du modèle.'
        recommendation='Sélectionner une fiche réelle ou importer une campagne expérimentale.'
    return {'level':level,'conclusion':conclusion,'checks':checks,'recommended_experiment':recommendation,
            'uncertainty_budget':uncertainty_budget(result)}
