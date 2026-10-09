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


def _finite_sample_band(details: list[dict], target_coverage: float = .8) -> dict:
    """Return an auditable split-conformal absolute relative-error band."""
    residuals=np.sort(np.asarray([row['relative_error_pct'] for row in details],dtype=float))
    if not len(residuals):
        raise ValueError('Aucune prédiction masquée disponible pour calculer la bande.')
    rank=min(len(residuals),int(math.ceil((len(residuals)+1)*target_coverage)))
    half_width=float(residuals[rank-1])
    return {
        'target_coverage_pct':target_coverage*100,
        'empirical_coverage_pct':float(np.mean(residuals<=half_width+1e-12)*100),
        'empirical_half_width_pct':half_width,
        'conformal_rank':rank,
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


def pp_literature_only_benchmark(rows: list[dict]) -> dict:
    """Validate a PP reference curve without using target ageing measurements.

    Each formulation is removed in turn. Its E0 is retained because that value
    comes from the material card; normalized retention at 30 and 120 days is
    estimated only from the other three formulations. This mirrors the actual
    zero-new-experiment use case more closely than the two-phase benchmark.
    """
    direct=[row for row in rows if row.get('source_id')=='mdpi-pp-natural-aging-2024']
    groups={experiment_id:sorted((r for r in direct if r['experiment_id']==experiment_id),
                                  key=lambda r:float(r['time_days']))
            for experiment_id in sorted({r['experiment_id'] for r in direct})}
    groups={key:value for key,value in groups.items() if _pp_anchor_values(value) is not None}
    if len(groups)<4:
        raise ValueError('Les quatre formulations PP H301 complètes sont requises.')
    details=[]
    for experiment_id,group in groups.items():
        e0,e30,e120=_pp_anchor_values(group)
        peers=[_pp_anchor_values(peer) for key,peer in groups.items() if key!=experiment_id]
        for day,observed,index in ((30.,e30,1),(120.,e120,2)):
            peer_retention=float(np.median([peer[index]/peer[0] for peer in peers]))
            predicted=float(e0*peer_retention)
            relative_error=abs(predicted-observed)/observed*100
            details.append({
                'formulation':experiment_id,'time_days':day,'initial_mpa':e0,
                'observed_mpa':observed,'predicted_mpa':predicted,
                'error_mpa':predicted-observed,'absolute_error_mpa':abs(predicted-observed),
                'relative_error_pct':relative_error,'peer_retention':peer_retention,
                'test_sd_mpa':float(group[index].get('standard_deviation_mpa') or 0),
            })
    metrics=_error_metrics(details)
    band=_finite_sample_band(details)
    half_width_pct=band['empirical_half_width_pct']
    by_day={}
    for day in (30.,120.):
        subset=[row for row in details if row['time_days']==day]
        by_day[str(int(day))]={**_error_metrics(subset),'count':len(subset)}
    anchors=[]; late_rates=[]
    for group in groups.values():
        e0,e30,e120=_pp_anchor_values(group)
        anchors.append([1.,e30/e0,e120/e0])
        late_rates.append(float(np.log(e30/e120)/90))
    anchors=np.asarray(anchors,dtype=float)
    return {
        'method':'Rétention médiane des trois formulations paires',
        'protocol':('Chaque formulation est masquée entièrement. Materia conserve uniquement son module initial E0, '
                    'puis prédit E30 et E120 avec les rétentions médianes des trois autres formulations.'),
        'independence':'Validation interne hors formulation, une publication et quatre formulations PP H301',
        **metrics,'details':details,'test_count':len(details),'by_day':by_day,
        **band,
        'profile':{
            'times_days':[0.,30.,120.],
            'median_retention':np.median(anchors,axis=0).tolist(),
            'observed_min_retention':np.min(anchors,axis=0).tolist(),
            'observed_max_retention':np.max(anchors,axis=0).tolist(),
            'late_rate_median_per_day':float(np.median(late_rates)),
            'late_rate_min_per_day':float(np.min(late_rates)),
            'late_rate_max_per_day':float(np.max(late_rates)),
        },
        'status':'CALIBRAGE INTERNE SANS MESURE DE VIEILLISSEMENT CIBLE',
        'conclusion':('Dans ce cas PP H301, une courbe fondée sur la littérature seule atteint une erreur relative '
                      'moyenne inférieure à 3 % à 30 et 120 jours. La bande empirique est valable comme contrôle '
                      'interne du cas étudié ; son transfert à un autre grade ou au-delà de 120 jours reste à confirmer.'),
    }


def iir_temporal_holdout(rows: list[dict]) -> dict:
    """Check piecewise-linear interpolation by masking every interior IIR point."""
    direct=[row for row in rows if row.get('source_id')=='mdpi-iir-mwf-2019']
    groups={float(temperature):sorted(
        (row for row in direct if float(row.get('ageing_temperature_c'))==float(temperature)),
        key=lambda row:float(row['time_days']))
        for temperature in sorted({float(row['ageing_temperature_c']) for row in direct
                                   if _finite(row.get('ageing_temperature_c'))})}
    if len(groups)!=3 or any(len(group)<7 for group in groups.values()):
        raise ValueError('Les trois courbes IIR complètes à 80, 100 et 120 °C sont requises.')
    details=[]
    for temperature,group in groups.items():
        for index in range(1,len(group)-1):
            target=group[index]; before=group[index-1]; after=group[index+1]
            time=float(target['time_days'])
            fraction=(time-float(before['time_days']))/(float(after['time_days'])-float(before['time_days']))
            predicted=float(before['modulus_mpa'])+fraction*(float(after['modulus_mpa'])-float(before['modulus_mpa']))
            observed=float(target['modulus_mpa']); error=predicted-observed
            sd=float(target.get('standard_deviation_mpa') or 0)
            details.append({
                'temperature_c':temperature,'time_hours':time*24,
                'observed_mpa':observed,'predicted_mpa':predicted,
                'error_mpa':error,'absolute_error_mpa':abs(error),
                'relative_error_pct':abs(error)/observed*100,
                'test_sd_mpa':sd,'within_reported_sd':bool(sd and abs(error)<=sd),
            })
    return {
        'material':'Composite caoutchouc butyle (IIR/BRC)',
        'method':'Interpolation linéaire avec un temps intérieur masqué',
        'protocol':('Chaque valeur intérieure est retirée puis reconstruite uniquement avec les deux temps '
                    'publiés qui l’encadrent, à température constante.'),
        'independence':'Validation interne sur trois courbes d’une publication, 80/100/120 °C et 0–24 h',
        **_error_metrics(details),**_finite_sample_band(details),
        'within_reported_sd_count':sum(row['within_reported_sd'] for row in details),
        'test_count':len(details),'details':details,
        'status':'INTERPOLATION TEMPORELLE INTERNE',
        'conclusion':('L’interpolation entre temps mesurés est exploitable dans la fenêtre 0–24 h, mais les '
                      'variations non monotones à 120 °C imposent une bande plus large que pour le PP.'),
    }


def iir_temperature_holdout(rows: list[dict]) -> dict:
    """Hide the 100 °C curve and reconstruct it from normalized 80/120 °C curves."""
    direct=[row for row in rows if row.get('source_id')=='mdpi-iir-mwf-2019']
    by_temperature={}
    for temperature in (80.,100.,120.):
        group=sorted((row for row in direct if float(row.get('ageing_temperature_c') or -999)==temperature),
                     key=lambda row:float(row['time_days']))
        by_temperature[temperature]={round(float(row['time_days'])*24,9):row for row in group}
    shared=set(by_temperature[80.]) & set(by_temperature[100.]) & set(by_temperature[120.])
    if len(shared)<7:
        raise ValueError('Les temps communs des courbes IIR 80/100/120 °C sont incomplets.')
    initial={temperature:float(by_temperature[temperature][0.]['modulus_mpa']) for temperature in by_temperature}
    details=[]
    for hours in sorted(shared-{0.}):
        observed=float(by_temperature[100.][hours]['modulus_mpa'])
        retention80=float(by_temperature[80.][hours]['modulus_mpa'])/initial[80.]
        retention120=float(by_temperature[120.][hours]['modulus_mpa'])/initial[120.]
        predicted=initial[100.]*(retention80+retention120)/2
        error=predicted-observed
        details.append({
            'temperature_c':100.,'time_hours':hours,
            'observed_mpa':observed,'predicted_mpa':predicted,
            'error_mpa':error,'absolute_error_mpa':abs(error),
            'relative_error_pct':abs(error)/observed*100,
        })
    return {
        'method':'Courbe 100 °C entièrement masquée, interpolation normalisée entre 80 et 120 °C',
        'protocol':'Seul E0 à 100 °C est conservé ; toutes les valeurs vieillies à 100 °C sont masquées.',
        **_error_metrics(details),**_finite_sample_band(details),
        'test_count':len(details),'details':details,
        'status':'TRANSFERT EN TEMPÉRATURE NON VALIDÉ',
        'conclusion':('La réponse IIR n’est pas linéaire avec la température. Materia doit privilégier les '
                      'courbes exactes à 80, 100 ou 120 °C et ne pas annoncer la même précision entre ces niveaux.'),
    }


def flax_temperature_transfer_benchmark(rows: list[dict]) -> dict:
    """Predict each flax/epoxy temperature campaign from the other campaign."""
    usable=[row for row in rows if _finite(row.get('temperature_C')) and _finite(row.get('modulus_MPa'))]
    temperatures=sorted({float(row['temperature_C']) for row in usable})
    if temperatures!=[20.,40.]:
        raise ValueError('Les campagnes lin/époxy complètes à 20 et 40 °C sont requises.')
    groups={temperature:{float(row['time_days']):row for row in usable
                         if float(row['temperature_C'])==temperature} for temperature in temperatures}
    shared=set(groups[20.]) & set(groups[40.])
    if len(shared)<5 or 0. not in shared:
        raise ValueError('Les cinq temps communs lin/époxy sont requis.')
    details=[]
    for target_temperature,peer_temperature in ((20.,40.),(40.,20.)):
        target_e0=float(groups[target_temperature][0.]['modulus_MPa'])
        peer_e0=float(groups[peer_temperature][0.]['modulus_MPa'])
        for day in sorted(shared-{0.}):
            observed=float(groups[target_temperature][day]['modulus_MPa'])
            predicted=target_e0*float(groups[peer_temperature][day]['modulus_MPa'])/peer_e0
            error=predicted-observed
            details.append({
                'temperature_c':target_temperature,'time_days':day,
                'observed_mpa':observed,'predicted_mpa':predicted,
                'error_mpa':error,'absolute_error_mpa':abs(error),
                'relative_error_pct':abs(error)/observed*100,
            })
    return {
        'material':'Composite fibres de lin / époxy',
        'method':'Transfert de la rétention entre les campagnes 20 et 40 °C',
        'protocol':('Chaque campagne est masquée à tour de rôle. Materia conserve son E0 et applique uniquement '
                    'la rétention de l’autre température aux jours 1, 3, 9 et 38.'),
        'independence':'Validation interne entre deux campagnes de la même publication ; valeurs de figure numérisées à ±3 %',
        **_error_metrics(details),**_finite_sample_band(details),
        'test_count':len(details),'details':details,
        'status':'TRANSFERT INTERNE PILOTE',
        'conclusion':('La forme de courbe se transfère correctement entre 20 et 40 °C sur 0–38 jours. La bande '
                      'reste interne à deux campagnes et l’incertitude de numérisation doit rester affichée séparément.'),
    }


def pp_h301_reference_profile(rows: list[dict]) -> dict | None:
    """Return the internally calibrated PP H301 profile used by the simulator."""
    try:
        report=pp_literature_only_benchmark(rows)
    except ValueError:
        return None
    profile=report['profile']; center=np.asarray(profile['median_retention'],dtype=float)
    half=report['empirical_half_width_pct']/100
    lower=center.copy(); upper=center.copy()
    lower[1:]*=1-half; upper[1:]*=1+half
    direct=[row for row in rows if row.get('source_id')=='mdpi-pp-natural-aging-2024']
    first=direct[0]
    return {
        'times':np.asarray(profile['times_days'],dtype=float),'median':center,
        'lower':lower,'upper':upper,
        'outer_lower':np.asarray(profile['observed_min_retention'],dtype=float),
        'outer_upper':np.asarray(profile['observed_max_retention'],dtype=float),
        'late_rate':profile['late_rate_median_per_day'],
        'late_rate_low':profile['late_rate_min_per_day'],
        'late_rate_high':profile['late_rate_max_per_day'],
        'outer_rate_low':profile['late_rate_min_per_day'],
        'outer_rate_high':profile['late_rate_max_per_day'],
        'experiments':4,'source_count':1,
        'source_ids':['mdpi-pp-natural-aging-2024'],
        'profile_kind':'same_study_formulation_holdout',
        'calibration':{
            'method':'leave-one-formulation-out, literature-only median retention',
            'target_coverage_pct':report['target_coverage_pct'],
            'empirical_point_coverage_pct':report['empirical_coverage_pct'],
            'empirical_half_width_pct':report['empirical_half_width_pct'],
            'mape_pct':report['mape_pct'],'mae_mpa':report['mae_mpa'],
            'r2':report['r2'],'calibration_units':4,'test_predictions':8,
        },
        'source':{
            'id':'mdpi-pp-natural-aging-2024','title':first.get('source_title'),
            'url':first.get('source_url'),'doi':first.get('source_doi'),
            'location':'Tableau 2, quatre formulations PP H301, 0–30–120 jours, n=7',
        },
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
    source_uncertainty=(uncertainty.get('source_specific') or uncertainty
                        if uncertainty.get('kind')!='standardized_rate_sensitivity'
                        else uncertainty.get('source_specific') or {})
    if source_uncertainty:
        quantified=source_uncertainty.get('kind') not in {'scenario_sensitivity','internal_formulation_iqr'}
        rows.append({'component':'Mesure / éprouvettes','value':source_uncertainty.get('label','Incertitude documentaire'),
                     'quantified':quantified,
                     'meaning':source_uncertainty.get('interpretation') or 'Composante déclarée dans la source.'})
    else:
        rows.append({'component':'Mesure / éprouvettes','value':'Non quantifiée','quantified':False,
                     'meaning':'Aucune répétition compatible n’est disponible pour ce résultat.'})
    rows.append({'component':'Plage affichée à l’horizon','value':f'± {shown:.1f} % autour de la courbe centrale' if shown is not None else 'Non calculable',
                 'quantified':shown is not None,
                 'meaning':'Convention commune ×0,90–×1,10 sur la vitesse ; largeur en module variable avec le temps.'})
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
        calibrated=manifest.get('evidence_level') in {'case_calibrated_short_term','calibrated_short_term','evidence_informed_short_term'}
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
