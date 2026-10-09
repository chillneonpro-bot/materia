"""Hygrothermal ML baselines evaluated on held-out experiments."""
from __future__ import annotations

import os
import numpy as np
import unicodedata
from hashlib import sha256
import json
from scipy.stats import t as student_t
if not os.environ.get('LOKY_MAX_CPU_COUNT'):
    # Keep the worker count below the logical-core count so loky does not call
    # a platform-specific physical-core probe that is unreliable on some Macs.
    logical_cores=os.cpu_count() or 1
    os.environ['LOKY_MAX_CPU_COUNT']=str(max(1,min(4,logical_cores-1)))
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ['temperature_C', 'humidity_RH', 'time_hours', 'thickness_mm']
FEATURE_LABELS = {
    'temperature_C': 'Température (°C)', 'humidity_RH': 'Humidité relative (%)',
    'time_hours': "Temps d’exposition (h)", 'thickness_mm': 'Épaisseur (mm)',
}

TIME_UNIT_DAYS = {'days':1.0, 'months':365.25/12, 'years':365.25}

# One comparison convention is applied to every datasheet projection. It
# varies the ageing speed, not the module itself, so the time-to-threshold
# interval remains readable and comparable across material families.
STANDARD_RATE_SLOW_MULTIPLIER = .80
STANDARD_RATE_FAST_MULTIPLIER = 1.20

def duration_to_days(value: float, unit: str) -> float:
    """Convert a positive UI duration to days using a documented mean calendar year."""
    if unit not in TIME_UNIT_DAYS or not np.isfinite(value) or value < 0:
        raise ValueError('Durée ou unité de temps invalide.')
    return float(value*TIME_UNIT_DAYS[unit])

def duration_to_years(value: float, unit: str) -> float:
    return duration_to_days(value,unit)/365.25

def duration_label(value: float, unit: str) -> str:
    labels={'days':'jour','months':'mois','years':'an'}
    if unit not in labels: raise ValueError('Unité de temps invalide.')
    suffix='s' if unit in {'days','years'} and value!=1 else ''
    return f"{value:g} {labels[unit]}{suffix}"

def format_years_months(years: float) -> str:
    """Format a decimal duration as rounded calendar years and months."""
    if not np.isfinite(years) or years < 0:
        raise ValueError('Durée invalide.')
    days=years*365.25
    if days == 0:
        return 'immédiatement'
    if 0 < days < .75:
        hours=max(1,int(round(days*24)))
        return f"{hours} heure"+('s' if hours>1 else '')
    if 0 < days < 45:
        whole_days=max(1,int(round(days)))
        return f"{whole_days} jour"+('s' if whole_days>1 else '')
    total_months=int(round(years*12))
    whole_years,months=divmod(total_months,12)
    parts=[]
    if whole_years: parts.append(f"{whole_years} an"+('s' if whole_years>1 else ''))
    if months: parts.append(f"{months} mois")
    return ' et '.join(parts) if parts else 'moins d’un mois'

def standard_profile(material: dict) -> dict:
    """Return a traceable grade value when available, otherwise a family default."""
    if material.get('custom') and float(material.get('suggested_modulus_mpa') or 0)>0:
        return {'suggested_modulus_mpa':float(material['suggested_modulus_mpa']),
                'reference_half_life_years':8.,
                'basis':'Module saisi dans votre fiche personnalisée ; cinétique générique non validée.'}
    raw=' '.join(str(material.get(k,'')) for k in ('id','family','subcategory','subtype','mechanisms')).lower()
    text=''.join(c for c in unicodedata.normalize('NFKD',raw) if not unicodedata.combining(c))
    if 'composite' in text: e0,life=26000.,5.
    elif 'elastomere' in text or 'caoutchouc' in text or 'silicone' in text: e0,life=10.,6.
    elif 'fluoropolymere' in text: e0,life=900.,25.
    elif 'haute performance' in text or any(x in text for x in ('peek','polyimide','polysulf')): e0,life=3000.,20.
    elif 'thermodurcissable' in text: e0,life=3000.,10.
    elif 'biodegradable' in text or str(material.get('id','')).upper() in {'PLA','PBS','PHA','PCL'}: e0,life=2200.,2.
    elif 'polyamide' in text or 'polyester' in text: e0,life=2500.,6.
    elif 'polyurethane' in text: e0,life=50.,4.
    elif 'polyolefine' in text: e0,life=1100.,10.
    else: e0,life=2200.,8.
    # Import lazily to avoid coupling the numerical module to database setup at
    # import time. A datasheet value changes E0 only; it never validates the
    # generic ageing rate used for materials without time series.
    from materia import material_db
    reference=material_db.reference_property_profile(str(material.get('id','')))
    if reference:
        e0=reference['representative_mpa']
        low,high=reference['minimum_mpa'],reference['maximum_mpa']
        spread=(f"{low:,.0f} MPa" if low==high else f"{low:,.0f}–{high:,.0f} MPa").replace(',', '\u202f')
        return {
            'suggested_modulus_mpa':e0,'reference_half_life_years':life,
            'basis':(f"Module initial de fiche technique recoupé : {reference['grade']} ; "
                     f"plage officielle {spread}, {reference['test_standard']}, "
                     f"{reference['conditioning']}. La cinétique de vieillissement reste une estimation de famille."),
            'reference_property':reference,
        }
    return {'suggested_modulus_mpa':e0,'reference_half_life_years':life,
            'basis':'Valeur générique de famille à remplacer par la fiche technique du grade choisi.'}


def _evidence_profile(rows: list[dict]) -> dict | None:
    """Build a normalized profile from verified, property-compatible series."""
    rows=[r for r in rows
          if r.get('evidence_status') in {None,'source_verified_table'}
          and (not r.get('property_name') or 'module de young' in str(r['property_name']).lower())]
    groups=[]
    for experiment_id in sorted({r['experiment_id'] for r in rows}):
        group=sorted((r for r in rows if r['experiment_id']==experiment_id),key=lambda r:float(r['time_days']))
        if len(group)<3 or float(group[0]['time_days'])!=0 or any(float(r['modulus_mpa'])<=0 for r in group):
            continue
        groups.append(group)
    if len(groups)<3:
        return None
    common=sorted(set.intersection(*(set(float(r['time_days']) for r in group) for group in groups)))
    if len(common)<3 or common[0]!=0:
        return None
    profiles=[]
    for group in groups:
        by_time={float(r['time_days']):float(r['modulus_mpa']) for r in group}
        e0=by_time[0.]
        profiles.append([by_time[time]/e0 for time in common])
    profiles=np.asarray(profiles,dtype=float); times=np.asarray(common,dtype=float)
    late_rates=[]
    for profile in profiles:
        if profile[-2]>profile[-1]>0:
            late_rates.append(float(np.log(profile[-2]/profile[-1])/(times[-1]-times[-2])))
    if len(late_rates)<3:
        return None
    first=groups[0][0]
    source_ids=sorted({str(r.get('source_id') or 'source-non-renseignée') for group in groups for r in group})
    return {
        'times':times,'median':np.median(profiles,axis=0),
        'lower':np.quantile(profiles,.25,axis=0),'upper':np.quantile(profiles,.75,axis=0),
        'outer_lower':np.min(profiles,axis=0),'outer_upper':np.max(profiles,axis=0),
        'late_rate':float(np.median(late_rates)),
        'late_rate_low':float(np.quantile(late_rates,.25)),'late_rate_high':float(np.quantile(late_rates,.75)),
        'outer_rate_low':float(min(late_rates)),'outer_rate_high':float(max(late_rates)),
        'experiments':len(groups),'source_count':len(source_ids),'source_ids':source_ids,'source':{
            'id':first.get('source_id'),'title':first.get('source_title'),
            'url':first.get('source_url'),'doi':first.get('source_doi'),
            'location':f"Profils normalisés de {len(groups)} séries comparables",
        },
    }


def _temperature_surface_profile(rows: list[dict], temperature_c: float) -> dict | None:
    """Interpolate normalized curves only inside a published temperature/time surface."""
    eligible=[r for r in rows
              if r.get('evidence_status') in {None,'source_verified_table'}
              and r.get('ageing_temperature_c') is not None
              and (not r.get('property_name') or 'module de young' in str(r['property_name']).lower())]
    temperatures=sorted({float(r['ageing_temperature_c']) for r in eligible})
    if len(temperatures)<2 or not temperatures[0]<=temperature_c<=temperatures[-1]:
        return None
    groups=[]
    for temperature in temperatures:
        group=sorted((r for r in eligible if float(r['ageing_temperature_c'])==temperature),
                     key=lambda r:float(r['time_days']))
        if len(group)>=3 and float(group[0]['time_days'])==0:
            groups.append(group)
    if len(groups)<2:
        return None
    common=sorted(set.intersection(*(set(float(r['time_days']) for r in group) for group in groups)))
    if len(common)<3 or common[0]!=0:
        return None
    profiles=[]; deviations=[]
    for group in groups:
        by_time={float(r['time_days']):r for r in group}; e0=float(by_time[0.]['modulus_mpa'])
        profiles.append([float(by_time[t]['modulus_mpa'])/e0 for t in common])
        deviations.append([float(by_time[t].get('standard_deviation_mpa') or 0)/e0 for t in common])
    profiles=np.asarray(profiles); deviations=np.asarray(deviations); times=np.asarray(common)
    exact_temperature=any(np.isclose(temperature_c,value,rtol=0,atol=1e-9) for value in temperatures)
    center=np.asarray([np.interp(temperature_c,temperatures,profiles[:,i]) for i in range(len(times))])
    sd=np.asarray([np.interp(temperature_c,temperatures,deviations[:,i]) for i in range(len(times))])
    transfer_calibration=None
    if not exact_temperature and {str(r.get('source_id')) for r in eligible}=={'mdpi-iir-mwf-2019'}:
        # The entire 100 °C curve was hidden and reconstructed from 80/120 °C.
        # Its worst observed relative error is the only defensible band for an
        # unmeasured intermediate temperature in this small corpus.
        from materia.validation import iir_temperature_holdout
        transfer_calibration=iir_temperature_holdout(eligible)
        half=transfer_calibration['empirical_half_width_pct']/100
        lower=np.maximum(center*(1-half),0); upper=center*(1+half)
    else:
        lower=np.maximum(center-sd,0); upper=center+sd
    tail_rate=float(np.log(center[-2]/center[-1])/(times[-1]-times[-2])) if center[-2]>center[-1]>0 else 0.
    first=groups[0][0]; source_ids=sorted({str(r.get('source_id') or 'source-non-renseignée') for r in eligible})
    return {'times':times,'median':center,'lower':lower,'upper':upper,
            'outer_lower':lower,'outer_upper':upper,
            'late_rate':tail_rate,'late_rate_low':tail_rate,'late_rate_high':tail_rate,
            'outer_rate_low':tail_rate,'outer_rate_high':tail_rate,
            'experiments':len(groups),'source_count':len(source_ids),'source_ids':source_ids,
            'profile_kind':'temperature_surface','temperature_range':[temperatures[0],temperatures[-1]],
            'exact_temperature':exact_temperature,
            'calibration':({'method':transfer_calibration['method'],
                            'mape_pct':transfer_calibration['mape_pct'],
                            'empirical_half_width_pct':transfer_calibration['empirical_half_width_pct'],
                            'test_predictions':transfer_calibration['test_count']}
                           if transfer_calibration else None),
            'source':{'id':first.get('source_id'),'title':first.get('source_title'),
                      'url':first.get('source_url'),'doi':first.get('source_doi'),
                      'location':f'Tableau 1, {"courbe exacte" if exact_temperature else "interpolation"} à {temperature_c:g} °C'}}


def _literature_ensemble_profile(rows: list[dict]) -> dict | None:
    """Build an 80% log-symmetric band calibrated by leaving whole sources out."""
    eligible=[r for r in rows
              if r.get('evidence_status') in {None,'source_verified_table'}
              and (not r.get('property_name') or 'module de young' in str(r['property_name']).lower())]
    source_groups={}
    for row in eligible:
        source_groups.setdefault(str(row.get('source_id') or 'source-non-renseignée'),[]).append(row)
    prepared=[]
    for source_id,source_rows in source_groups.items():
        experiments=[]
        for experiment_id in sorted({str(r['experiment_id']) for r in source_rows}):
            group=sorted((r for r in source_rows if str(r['experiment_id'])==experiment_id),
                         key=lambda r:float(r['time_days']))
            if len(group)<3 or float(group[0]['time_days'])!=0 or any(float(r['modulus_mpa'])<=0 for r in group):
                continue
            times=np.asarray([float(r['time_days']) for r in group]); values=np.asarray([float(r['modulus_mpa']) for r in group])
            experiments.append({'times':times,'retention':values/values[0],'rows':group})
        if experiments:
            prepared.append({'id':source_id,'experiments':experiments,
                             'max_time':min(float(exp['times'][-1]) for exp in experiments),
                             'first':experiments[0]['rows'][0]})
    if len(prepared)<3:
        return None
    common_max=min(source['max_time'] for source in prepared)
    if common_max<=0:
        return None
    grid=sorted({0.,common_max}|{float(r['time_days']) for r in eligible if 0<float(r['time_days'])<common_max})
    if len(grid)<3:
        return None
    times=np.asarray(grid,dtype=float); study_curves=[]; source_details=[]; late_rates=[]
    for source in prepared:
        experiment_curves=[np.interp(times,exp['times'],exp['retention']) for exp in source['experiments']]
        study_curve=np.median(np.asarray(experiment_curves),axis=0)
        study_curves.append(study_curve)
        if study_curve[-2]>study_curve[-1]>0:
            late_rates.append(float(np.log(study_curve[-2]/study_curve[-1])/(times[-1]-times[-2])))
        first=source['first']
        source_details.append({'id':source['id'],'title':first.get('source_title'),
                               'url':first.get('source_url'),'doi':first.get('source_doi'),
                               'experiments':len(source['experiments']),'last_day':source['max_time'],
                               'extraction_methods':sorted({str(r.get('extraction_method') or 'non renseignée') for r in eligible if str(r.get('source_id') or 'source-non-renseignée')==source['id']})})
    curves=np.asarray(study_curves,dtype=float)
    center=np.median(curves,axis=0)
    source_scores=[]; signed_by_source=[]
    for index,observed in enumerate(curves):
        predicted=np.median(np.delete(curves,index,axis=0),axis=0)
        signed=np.log(np.clip(observed[1:],1e-9,None)/np.clip(predicted[1:],1e-9,None))
        signed_by_source.append(signed)
        source_scores.append(float(np.quantile(np.abs(signed),.8)))
    signed_matrix=np.asarray(signed_by_source)
    lower_q=np.minimum(0.,np.quantile(signed_matrix,.1,axis=0))
    upper_q=np.maximum(0.,np.quantile(signed_matrix,.9,axis=0))
    lower=np.r_[1.,center[1:]*np.exp(lower_q)]; upper=np.r_[1.,center[1:]*np.exp(upper_q)]
    center[0]=1.
    covered=np.logical_and(curves>=lower,curves<=upper)
    coverage=float(np.mean(covered[:,1:])*100)
    if late_rates:
        late_rate=float(np.median(late_rates)); late_low=float(np.min(late_rates)); late_high=float(np.max(late_rates))
    else:
        late_rate=late_low=late_high=0.
    return {'times':times,'median':center,'lower':lower,'upper':upper,
            'outer_lower':np.min(curves,axis=0),'outer_upper':np.max(curves,axis=0),
            'late_rate':late_rate,'late_rate_low':late_low,'late_rate_high':late_high,
            'outer_rate_low':late_low,'outer_rate_high':late_high,
            'experiments':sum(len(source['experiments']) for source in prepared),
            'source_count':len(prepared),'source_ids':[source['id'] for source in prepared],
            'profile_kind':'source_ensemble',
            'calibration':{'method':'leave-one-source-out asymmetric log-residual quantiles',
                           'target_coverage_pct':80.,'empirical_point_coverage_pct':coverage,
                           'log_residual_quantiles_at_last_day':[float(lower_q[-1]),float(upper_q[-1])],
                           'source_scores':source_scores,
                           'calibration_units':len(prepared)},
            'source':{'id':'pp-outdoor-multi-source','title':'Ensemble de publications indépendantes sur le PP en exposition naturelle',
                      'url':source_details[0].get('url'),'doi':None,
                      'location':f"{len(prepared)} sources indépendantes, fenêtre commune 0–{common_max:g} jours",
                      'sources':source_details}}


def _evidence_match_score(profile: dict | None, rows: list[dict], temperature_c: float,
                          humidity_rh: float, thickness_mm: float) -> dict:
    """Score documentary similarity. This is a coverage indicator, never a probability."""
    if profile is None:
        return {'score':0,'label':'Aucune cinétique compatible','meaning':'Aucune série temporelle vérifiée ne correspond à la propriété et au milieu choisis.'}
    score=45.0  # same polymer family, target property and exposure mode
    reasons=['famille, propriété et milieu compatibles']
    temperatures=[float(r['ageing_temperature_c']) for r in rows if r.get('ageing_temperature_c') is not None]
    humidities=[float(r['humidity_rh']) for r in rows if r.get('humidity_rh') is not None]
    thicknesses=[float(r['thickness_mm']) for r in rows if r.get('thickness_mm') is not None]
    if temperatures:
        delta=abs(float(np.median(temperatures))-temperature_c)
        score+=15*max(0,1-delta/30); reasons.append(f'température documentée (Δ {delta:.0f} °C)')
    if humidities:
        delta=abs(float(np.median(humidities))-humidity_rh)
        score+=10*max(0,1-delta/50); reasons.append(f'humidité documentée (Δ {delta:.0f} points)')
    if thicknesses:
        ratio=max(float(np.median(thicknesses)),thickness_mm)/min(float(np.median(thicknesses)),thickness_mm)
        score+=10*max(0,1-(ratio-1)/3); reasons.append(f'épaisseur documentée (rapport {ratio:.1f})')
    score+=min(20.,5.*profile['source_count'])
    label=('Correspondance forte' if score>=80 else 'Correspondance moyenne' if score>=60 else 'Correspondance partielle')
    return {'score':int(round(min(score,100))), 'label':label,
            'meaning':'; '.join(reasons)+f" ; {profile['source_count']} source(s) indépendante(s)."}


def _profile_curve(days: np.ndarray, times: np.ndarray, values: np.ndarray, tail_rate: float) -> np.ndarray:
    clipped=np.minimum(days,times[-1]); curve=np.interp(clipped,times,values)
    after=days>times[-1]
    curve[after]=values[-1]*np.exp(-tail_rate*(days[after]-times[-1]))
    return curve


def _profile_crossing(target: float, times: np.ndarray, values: np.ndarray, tail_rate: float) -> float | None:
    if target>=1:
        return 0.
    for index in range(1,len(times)):
        before,after=float(values[index-1]),float(values[index])
        if before>=target>=after and before!=after:
            fraction=(before-target)/(before-after)
            return float(times[index-1]+fraction*(times[index]-times[index-1]))
    if float(values[-1])>target and tail_rate>0:
        return float(times[-1]+np.log(float(values[-1])/target)/tail_rate)
    return None

def estimate_from_datasheet(material: dict, modulus_mpa: float, temperature_c: float,
                            humidity_rh: float, thickness_mm: float, horizon_years: float,
                            threshold_percent: float, exposure: str='indoor',
                            evidence_rows: list[dict] | None = None,
                            immersion_medium: str | None = None) -> dict:
    """Engineering screening curve from a datasheet modulus and transparent family factors."""
    values=[modulus_mpa,temperature_c,humidity_rh,thickness_mm,horizon_years,threshold_percent]
    if not np.all(np.isfinite(values)) or modulus_mpa<=0 or thickness_mm<=0 or horizon_years<=0:
        raise ValueError('Les paramètres doivent être finis et strictement positifs.')
    if not -40<=temperature_c<=160 or not 0<=humidity_rh<=100 or not 1<=threshold_percent<=100:
        raise ValueError('Température, humidité ou seuil hors du domaine de l’estimateur.')
    if exposure not in {'indoor','outdoor','immersion'}:
        raise ValueError('Milieu d’exposition inconnu.')
    family_profile=standard_profile(material); mechanisms=str(material.get('mechanisms','')).lower()
    base_rate=np.log(2)/(family_profile['reference_half_life_years']*365.25)
    temp_factor=2**((temperature_c-23)/10)
    moisture_sensitive=any(x in mechanisms for x in ('hydro','humid','eau','plastification'))
    humidity_factor=1+(2.2 if moisture_sensitive else .45)*(humidity_rh/100)**2
    if exposure=='immersion':
        # Ambient relative humidity has no physical meaning for a permanently immersed specimen.
        # The bath chemistry is not yet represented, so immersion remains a coarse scenario factor.
        humidity_factor=1.
    environment_factor=1.
    if exposure=='outdoor': environment_factor=2.2 if 'photo' in mechanisms else 1.35
    if exposure=='immersion': environment_factor=2.8 if moisture_sensitive else 1.5
    thickness_factor=np.clip((2/max(thickness_mm,.1))**.35,.55,2.5) if moisture_sensitive else 1.
    rate=float(base_rate*temp_factor*humidity_factor*environment_factor*thickness_factor)
    days=np.linspace(0,horizon_years*365.25,241)
    target=threshold_percent/100
    compatible_rows=evidence_rows or []
    if exposure=='immersion':
        wanted={'milform64':'milform 64 sst','Milform 64 SST':'milform 64 sst'}.get(immersion_medium)
        compatible_rows=[r for r in compatible_rows if wanted and wanted in str(r.get('medium','')).lower()]
    if exposure=='outdoor':
        # PP has one homogeneous, directly tabulated case with four related
        # formulations. Prefer its held-out formulation benchmark to a broad
        # mixture of unrelated climates and grades.
        if str(material.get('id','')).upper()=='PP':
            from materia.validation import pp_h301_reference_profile
            observed_profile=(pp_h301_reference_profile(compatible_rows)
                              or _literature_ensemble_profile(compatible_rows)
                              or _evidence_profile(compatible_rows))
        else:
            observed_profile=_literature_ensemble_profile(compatible_rows) or _evidence_profile(compatible_rows)
    elif exposure=='immersion':
        observed_profile=_temperature_surface_profile(compatible_rows,temperature_c)
    else:
        observed_profile=None
    evidence_calibrated=observed_profile is not None
    match=_evidence_match_score(observed_profile,compatible_rows,temperature_c,humidity_rh,thickness_mm)
    if evidence_calibrated:
        # Natural weathering is represented by a normalized observed profile. Temperature is only a
        # scenario time-warp; its Q10 value is not fitted by the publication and remains explicit.
        transfer_factor=(1. if observed_profile.get('profile_kind') in {'temperature_surface','source_ensemble','same_study_formulation_holdout'}
                         else float(temp_factor))
        effective_days=days*transfer_factor
        center_ret=_profile_curve(effective_days,observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
        lower_ret=_profile_curve(effective_days,observed_profile['times'],observed_profile['lower'],observed_profile['late_rate_high'])
        upper_ret=_profile_curve(effective_days,observed_profile['times'],observed_profile['upper'],observed_profile['late_rate_low'])
        center=modulus_mpa*center_ret; lower=modulus_mpa*lower_ret; upper=modulus_mpa*upper_ret
        outer_lower_ret=_profile_curve(effective_days,observed_profile['times'],observed_profile['outer_lower'],observed_profile['outer_rate_high'])
        outer_upper_ret=_profile_curve(effective_days,observed_profile['times'],observed_profile['outer_upper'],observed_profile['outer_rate_low'])
        outer_lower=modulus_mpa*outer_lower_ret; outer_upper=modulus_mpa*outer_upper_ret
        effective_cross=_profile_crossing(target,observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
        effective_low=_profile_crossing(target,observed_profile['times'],observed_profile['lower'],observed_profile['late_rate_high'])
        effective_high=_profile_crossing(target,observed_profile['times'],observed_profile['upper'],observed_profile['late_rate_low'])
        effective_outer_low=_profile_crossing(target,observed_profile['times'],observed_profile['outer_lower'],observed_profile['outer_rate_high'])
        effective_outer_high=_profile_crossing(target,observed_profile['times'],observed_profile['outer_upper'],observed_profile['outer_rate_low'])
        crossing=effective_cross/transfer_factor/365.25 if effective_cross is not None else None
        low_cross=effective_low/transfer_factor/365.25 if effective_low is not None else None
        high_cross=effective_high/transfer_factor/365.25 if effective_high is not None else None
        outer_low_cross=effective_outer_low/transfer_factor/365.25 if effective_outer_low is not None else None
        outer_high_cross=effective_outer_high/transfer_factor/365.25 if effective_outer_high is not None else None
        rate=observed_profile['late_rate']*transfer_factor; low_rate=observed_profile['late_rate_low']*transfer_factor; high_rate=observed_profile['late_rate_high']*transfer_factor
        evidence_window_days=float(observed_profile['times'][-1])/transfer_factor
        source=observed_profile['source']
        predictive_interval_validated=observed_profile['source_count']>=3
        surface=observed_profile.get('profile_kind')=='temperature_surface'
        temperature_transfer=surface and not observed_profile.get('exact_temperature',False)
        ensemble=observed_profile.get('profile_kind')=='source_ensemble'
        case_profile=observed_profile.get('profile_kind')=='same_study_formulation_holdout'
        uncertainty={'kind':'temperature_transfer_holdout' if temperature_transfer else 'reported_standard_deviation' if surface else 'source_level_predictive_interval' if ensemble else 'internal_holdout_interval' if case_profile else 'internal_formulation_iqr',
                     'label':f"Bande de transfert en température ±{observed_profile['calibration']['empirical_half_width_pct']:.1f} %" if temperature_transfer else 'Dispersion publiée ±1 écart-type' if surface else 'Intervalle prédictif pilote P10–P90' if ensemble else 'Bande empirique 80 % du cas PP H301' if case_profile else f"Dispersion centrale des {observed_profile['experiments']} formulations",
                     'coverage':f"pire erreur sur {observed_profile['calibration']['test_predictions']} valeurs de la courbe 100 °C masquée" if temperature_transfer else 'dispersion des mesures publiées' if surface else f"{observed_profile['calibration']['empirical_point_coverage_pct']:.1f} % observés en validation hors source" if ensemble else f"{observed_profile['calibration']['empirical_point_coverage_pct']:.1f} % sur 8 prédictions hors formulation" if case_profile else '50 % central du corpus aux temps observés',
                     'interpretation':'La température demandée n’a pas de courbe publiée exacte. La bande reprend la pire erreur lorsque la courbe 100 °C est reconstruite depuis 80 et 120 °C.' if temperature_transfer else 'Écart-type rapporté dans le tableau source ; il ne couvre pas le transfert vers un autre liquide ou une autre formulation.' if surface else 'Quantiles asymétriques des erreurs logarithmiques obtenues en laissant chaque publication entière de côté. Le corpus minimal de trois sources rend encore la couverture incertaine.' if ensemble else 'Largeur issue de l’erreur relative maximale observée lorsque chaque formulation PP H301 est masquée à tour de rôle. Elle est calibrée en interne à 0–120 jours.' if case_profile else 'Zone centrale entre les quartiles 25 % et 75 %. L’enveloppe min-max complète reste indiquée dans les hypothèses.',
                     'predictive_interval_validated':predictive_interval_validated and not case_profile,
                     'internally_calibrated':case_profile,
                     'display_band':True,
                     'outer_band_available':not surface,
                     'outer_band_label':'Enveloppe complète min–max observée' if not surface else None,
                     'calibration':observed_profile.get('calibration'),
                     'excludes':['transfert vers un autre grade','autre climat','variabilité entre lots']}
        # If the central threshold lies after the evidence window, the
        # in-domain P10–P90 must not be extrapolated to produce a threshold
        # interval. Use the same explicit projection sensitivity as the
        # long-horizon view.
        if ensemble and crossing is not None and crossing*365.25>evidence_window_days:
            effective_low=_profile_crossing(target**(1/1.5),observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
            effective_high=_profile_crossing(target**(1/.65),observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
            low_cross=effective_low/transfer_factor/365.25 if effective_low is not None else None
            high_cross=effective_high/transfer_factor/365.25 if effective_high is not None else None
            outer_low_cross=low_cross; outer_high_cross=high_cross
        # Coverage of the source-level interval was assessed only over the
        # common publication window. For a longer horizon, keep the median
        # documentary curve and show a transparent sensitivity around it.
        if ensemble and horizon_years*365.25>evidence_window_days:
            damage=-np.log(np.clip(center_ret,1e-12,1.))
            lower=modulus_mpa*np.exp(-1.5*damage)
            upper=modulus_mpa*np.exp(-.65*damage)
            effective_low=_profile_crossing(target**(1/1.5),observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
            effective_high=_profile_crossing(target**(1/.65),observed_profile['times'],observed_profile['median'],observed_profile['late_rate'])
            low_cross=effective_low/transfer_factor/365.25 if effective_low is not None else None
            high_cross=effective_high/transfer_factor/365.25 if effective_high is not None else None
            outer_low_cross=low_cross; outer_high_cross=high_cross
            uncertainty={
                'kind':'extrapolation_sensitivity',
                'label':'Sensibilité de la projection centrale',
                'coverage':'non statistique au-delà de la fenêtre publiée',
                'interpretation':f"Le P10–P90 pilote reste valable uniquement entre 0 et {evidence_window_days:g} jours. Pour l’horizon prolongé, la zone affichée applique ×0,65 à ×1,50 à la dégradation cumulée de la courbe P50.",
                'predictive_interval_validated':False,
                'display_band':True,
                'calibration':observed_profile.get('calibration'),
                'in_domain_uncertainty':'Intervalle prédictif pilote P10–P90',
                'sensitivity_multipliers':[.65,1.5],
                'excludes':['couverture statistique après la fenêtre publiée','transfert vers un autre grade','autre climat','variabilité entre lots'],
            }
        elif case_profile and horizon_years*365.25>evidence_window_days:
            uncertainty={
                'kind':'observed_rate_envelope_extrapolation',
                'label':'Bande PP H301, élargie par les vitesses observées',
                'coverage':'80 % interne jusqu’à 120 jours ; sensibilité au-delà',
                'interpretation':('Jusqu’à 120 jours, la largeur vient des huit erreurs hors formulation. '
                                  'Après 120 jours, les bornes prolongent les vitesses tardives minimale et maximale '
                                  'mesurées sur les quatre formulations, sans prétendre à une couverture statistique.'),
                'predictive_interval_validated':False,
                'internally_calibrated':True,'display_band':True,
                'calibration':observed_profile.get('calibration'),
                'sensitivity_rate_bounds_per_day':[observed_profile['late_rate_low'],observed_profile['late_rate_high']],
                'excludes':['validation après 120 jours','transfert vers un autre grade','autre climat','variabilité entre lots'],
            }
    else:
        # A literature-family transfer remains uncertain, but the former ÷3/×3
        # sensitivity made the estimate unreadable. These multipliers keep a
        # deliberately asymmetric engineering range around the best estimate.
        low_rate=rate*.65; high_rate=rate*1.5
        center=modulus_mpa*np.exp(-rate*days)
        upper=modulus_mpa*np.exp(-low_rate*days); lower=modulus_mpa*np.exp(-high_rate*days)
        crossing=float(-np.log(target)/rate/365.25) if target<1 else 0.
        low_cross=float(-np.log(target)/high_rate/365.25) if target<1 else 0.
        high_cross=float(-np.log(target)/low_rate/365.25) if target<1 else 0.
        evidence_window_days=0.
        outer_low_cross=low_cross; outer_high_cross=high_cross
        source={'title':material.get('source_title'),'url':material.get('source_url'),'doi':material.get('source_doi')}
        uncertainty={'kind':'scenario_sensitivity','label':'Plage indicative de transfert',
                     'coverage':'non statistique','interpretation':'La vitesse centrale est modulée de ×0,65 à ×1,50 pour représenter un transfert raisonnable entre la famille documentaire et le grade saisi. Cette zone reste une plage d’estimation, pas un intervalle de confiance.',
                     'predictive_interval_validated':False,'display_band':True,
                     'excludes':['dispersion expérimentale','transfert de formulation','incertitude prédictive']}

    # Uniform comparison layer: every material uses the same ±20 % change in
    # ageing speed. Source-specific uncertainty is retained for scientific
    # traceability but no longer changes the main simulator band.
    source_uncertainty=uncertainty
    damage=-np.log(np.clip(center/modulus_mpa,1e-12,None))
    slow_curve=modulus_mpa*np.exp(-STANDARD_RATE_SLOW_MULTIPLIER*damage)
    fast_curve=modulus_mpa*np.exp(-STANDARD_RATE_FAST_MULTIPLIER*damage)
    lower=np.minimum(slow_curve,fast_curve)
    upper=np.maximum(slow_curve,fast_curve)
    low_cross=(crossing/STANDARD_RATE_FAST_MULTIPLIER if crossing is not None else None)
    high_cross=(crossing/STANDARD_RATE_SLOW_MULTIPLIER if crossing is not None else None)
    outer_low_cross=low_cross; outer_high_cross=high_cross
    low_rate=rate*STANDARD_RATE_SLOW_MULTIPLIER
    high_rate=rate*STANDARD_RATE_FAST_MULTIPLIER
    uncertainty={
        'kind':'standardized_rate_sensitivity',
        'label':'Plage standardisée ±20 % sur la vitesse',
        'coverage':'même convention de comparaison pour tous les matériaux',
        'interpretation':('La borne rapide applique ×1,20 à la vitesse de vieillissement et la borne lente '
                          '×0,80. Cette plage uniforme facilite la comparaison ; elle ne constitue pas un '
                          'intervalle de confiance universel.'),
        'predictive_interval_validated':False,'display_band':True,
        'rate_multipliers':[STANDARD_RATE_SLOW_MULTIPLIER,STANDARD_RATE_FAST_MULTIPLIER],
        'calibration':source_uncertainty.get('calibration'),
        'source_specific':source_uncertainty,
        'excludes':['garantie statistique universelle','transfert vers un autre grade','variabilité entre lots'],
    }
    extrapolation_multiple=(horizon_years*365.25/evidence_window_days if evidence_calibrated and evidence_window_days else None)
    evidence_level=('case_calibrated_short_term' if evidence_calibrated and observed_profile.get('profile_kind')=='same_study_formulation_holdout'
                    else 'calibrated_short_term' if evidence_calibrated and observed_profile.get('profile_kind')=='source_ensemble'
                    else 'evidence_informed_short_term' if evidence_calibrated else 'exploratory_family_assumptions')
    if evidence_calibrated and extrapolation_multiple<=1:
        model_status=('CAS PP H301 CALIBRÉ HORS FORMULATION - FENÊTRE 0 À 120 JOURS'
                      if observed_profile.get('profile_kind')=='same_study_formulation_holdout' else
                      'INTERVALLE PILOTE CALIBRÉ HORS ÉTUDE - CORPUS MINIMAL'
                      if observed_profile.get('profile_kind')=='source_ensemble' else
                      'PROFIL DOCUMENTAIRE DANS LA FENÊTRE PUBLIÉE - TRANSFERT DE GRADE NON VALIDÉ')
    elif evidence_calibrated and extrapolation_multiple<=3:
        model_status='EXTRAPOLATION DOCUMENTAIRE LIMITÉE - VALIDATION INDÉPENDANTE REQUISE'
    elif evidence_calibrated:
        model_status='HORS DOMAINE DE PREUVE - SCÉNARIO PÉDAGOGIQUE UNIQUEMENT'
    else:
        model_status='ESTIMATION DOCUMENTAIRE DE PRÉSÉLECTION - CONFIANCE LIMITÉE'
    if not evidence_calibrated:
        profile_warning=('Les facteurs température, humidité et épaisseur sont des hypothèses exploratoires ; '
                         'la plage principale applique la convention commune ×0,80–×1,20 sur la vitesse.')
    elif observed_profile.get('profile_kind')=='temperature_surface':
        profile_warning=('La température saisie n’a pas de courbe exacte : la bande est élargie à la pire erreur '
                         'du test masqué 100 °C (±26,24 %).') if temperature_transfer else (
                         'La courbe correspond à une température publiée exacte ; aucun transfert sous 80 °C '
                         'ou au-dessus de 120 °C.')
    elif observed_profile.get('profile_kind')=='source_ensemble':
        profile_warning=('Les climats naturels des publications sont conservés tels quels ; la température, '
                         'l’humidité et l’épaisseur saisies ne corrigent pas encore cet ensemble.')
    elif observed_profile.get('profile_kind')=='same_study_formulation_holdout':
        profile_warning=('Le cas PP H301 est calibré sur quatre formulations d’une même publication ; au-delà de '
                         '120 jours, la bande prolonge les vitesses tardives extrêmes observées.')
    else:
        profile_warning=('Le facteur de température Q10 est une analyse de sensibilité non ajustée sur cette '
                         'publication ; humidité et épaisseur ne sont pas calibrées.')
    manifest={'model':'datasheet-screening-v5','dataset':'verified-literature-plus-material-card',
        'material_id':material['id'],'material_name':material['name'],
        'target_property':material.get('target_property') or 'Module de Young',
        'inputs':{'e0':modulus_mpa,'temperature':temperature_c,'humidity_RH':humidity_rh,
                  'thickness_mm':thickness_mm,'horizon_years':horizon_years,
                  'threshold':threshold_percent,'exposure':exposure,
                  'immersion_medium':immersion_medium if exposure=='immersion' else None},
        'assumptions':{'reference_half_life_years':family_profile['reference_half_life_years'],
                       'temperature_factor':temp_factor,'humidity_factor':humidity_factor,
                       'environment_factor':environment_factor,'thickness_factor':float(thickness_factor),
                       'evidence_calibrated':evidence_calibrated,'evidence_experiments':observed_profile['experiments'] if evidence_calibrated else 0,
                       'independent_sources':observed_profile['source_count'] if evidence_calibrated else 0,
                       'documentary_match':match,
                       'profile_method':(('surface température-temps publiée, interpolation dans le domaine' if observed_profile.get('profile_kind')=='temperature_surface' else 'médiane inter-études normalisée et calibration leave-one-source-out' if observed_profile.get('profile_kind')=='source_ensemble' else 'rétention médiane PP H301 et validation leave-one-formulation-out' if observed_profile.get('profile_kind')=='same_study_formulation_holdout' else 'médiane normalisée 0-30-120 jours puis vitesse tardive') if evidence_calibrated else None),
                       'evidence_window_days':evidence_window_days,
                       'extrapolation_multiple':extrapolation_multiple,
                       'rate_bounds_per_day':[low_rate,high_rate],
                       'outer_crossing_interval_years':[outer_low_cross,outer_high_cross]},
        'evidence_level':evidence_level,
        'intended_use':'Présélection pédagogique et comparaison de scénarios',
        'prohibited_use':'Dimensionnement, sécurité, garantie ou qualification sans essais représentatifs',
        'validity':{
            'temperature_c':[-40,160], 'humidity_rh':[0,100],
            'exposure':exposure,
            'material_scope':(f"Profil publié pour {material['name']} ; transfert vers le grade saisi non validé"
                              if evidence_calibrated else 'Famille générique, sans grade ni formulation propres'),
        },
        'uncertainty':uncertainty,
        'warnings':[
            'Le module initial ne détermine pas à lui seul la cinétique de vieillissement.',
            'La formulation, les additifs, le procédé et les contraintes mécaniques ne sont pas décrits.',
            (f"Le profil publié couvre {evidence_window_days:g} jours dans les conditions du scénario ; l’horizon demandé représente environ {extrapolation_multiple:.1f} fois cette durée." if evidence_calibrated
             else 'La vitesse centrale provient de la famille documentaire ; la plage visible applique la convention commune ×0,80 à ×1,20.'),
            profile_warning,
            ('En immersion, l’humidité relative de l’air est ignorée ; la nature du liquide, le pH, l’oxygène dissous et le renouvellement du bain ne sont pas modélisés.'
             if exposure=='immersion' else 'Le milieu est représenté par un facteur simplifié.'),
        ],
        'source':source,
        'status':model_status}
    fingerprint=sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    result={'time':(days/365.25).tolist(),'modulus':center.tolist(),'lower':lower.tolist(),'upper':upper.tolist(),
            'retention':(center/modulus_mpa*100).tolist(),
            'crossing':crossing if crossing is not None and crossing<=horizon_years else None,
            'crossing_estimate_years':crossing,'crossing_interval':[low_cross,high_cross],
            'fraction_crossing':float(crossing is not None and crossing<=horizon_years),'rate':rate,'manifest':manifest,
            'fingerprint':fingerprint,'pending':False}
    return result

def evidence_assessment(result: dict) -> dict:
    """Return a student-readable assessment without inventing a precision score."""
    manifest=result.get('manifest',{})
    level=manifest.get('evidence_level')
    if level in {'case_calibrated_short_term','calibrated_short_term','evidence_informed_short_term'}:
        multiple=(manifest.get('assumptions') or {}).get('extrapolation_multiple')
        if multiple is not None and multiple>3:
            return {
                'level':'Niveau 1 sur 4',
                'label':'Hors de la fenêtre de preuve',
                'tone':'amber',
                'meaning':f'L’horizon représente environ {multiple:.1f} fois la fenêtre comparable ; la courbe est un scénario, pas une prédiction qualifiée.',
                'allowed':'Visualiser la conséquence des hypothèses et préparer une campagne plus longue.',
                'next_step':'Allonger les observations ou réduire l’horizon avant toute interprétation de durée.',
            }
        if level=='case_calibrated_short_term':
            calibration=(manifest.get('uncertainty') or {}).get('calibration') or {}
            return {
                'level':'Niveau 2 sur 4',
                'label':'Cas PP H301 calibré hors formulation',
                'tone':'teal',
                'meaning':(f"La courbe a été contrôlée sur {calibration.get('test_predictions',8)} prédictions masquées ; "
                           f"erreur relative moyenne {calibration.get('mape_pct',0):.2f} % dans la fenêtre publiée."),
                'allowed':'Utiliser la courbe centrale et sa bande pour le cas PP H301 entre 0 et 120 jours.',
                'next_step':'Valider le transfert si le grade, la formulation, le climat ou l’horizon diffèrent.',
            }
        if level=='calibrated_short_term':
            calibration=(manifest.get('uncertainty') or {}).get('calibration') or {}
            return {
                'level':'Niveau 2 sur 4',
                'label':'Prédiction documentaire pilote calibrée hors étude',
                'tone':'teal',
                'meaning':f"La courbe centrale et le P10–P90 utilisent {calibration.get('calibration_units','plusieurs')} publications indépendantes. La couverture observée reste à confirmer prospectivement.",
                'allowed':'Figer la P50 avant essais et utiliser P10 comme scénario prudent de recherche.',
                'next_step':'Comparer la prédiction figée à plusieurs campagnes futures compatibles.',
            }
        return {
            'level':'Niveau 2 sur 4',
            'label':'Profil informé par des mesures publiées à court terme',
            'tone':'teal',
                'meaning':'Le profil central et son enveloppe viennent de plusieurs séries publiées ; au-delà de la dernière observation, la vitesse tardive reste une extrapolation.',
            'allowed':'Comparer des scénarios et formuler une hypothèse à vérifier.',
            'next_step':'Réaliser ou intégrer une campagne indépendante proche du grade et du milieu étudiés.',
        }
    return {
        'level':'Niveau 1 sur 4',
        'label':'Estimation documentaire de présélection',
        'tone':'amber',
        'meaning':'La ligne centrale est la meilleure estimation disponible à partir de la famille du matériau, du module initial et des conditions saisies. La plage standardisée applique la même variation de vitesse ×0,80 à ×1,20 à tous les matériaux.',
        'allowed':'Utiliser la courbe centrale pour une première estimation et comparer des scénarios, en conservant le niveau de confiance limité.',
        'next_step':'Ajouter des séries temporelles traçables pour ce matériau et ces conditions.',
    }

def sampled_curve_rows(result: dict, count: int = 9, time_unit: str | None = None) -> list[dict]:
    """Create an accessible, compact data table from a plotted curve."""
    times=np.asarray(result['time'],dtype=float)
    model=str(result.get('manifest',{}).get('model',''))
    if time_unit is None and model.startswith('datasheet-screening-'):
        unit=result.get('manifest',{}).get('inputs',{}).get('horizon_display',{}).get('unit','years')
        factor={'days':365.25,'months':12.,'years':1.}.get(unit,1.)
        times=times*factor; time_unit={'days':'jours','months':'mois','years':'années'}.get(unit,'années')
    elif time_unit is None:
        time_unit='jours'
    if len(times)==0:
        return []
    indices=np.unique(np.linspace(0,len(times)-1,min(count,len(times)),dtype=int))
    origins=curve_value_origins(result)
    rows=[]
    for index in indices:
        rows.append({
            'temps':round(float(times[index]),3), 'unite':time_unit,
            'module_mpa':round(float(result['modulus'][index]),2),
            'module_min_mpa':round(float(result['lower'][index]),2),
            'module_max_mpa':round(float(result['upper'][index]),2),
            'retention_pct':round(float(result['retention'][index]),2),
            'origine':origins[index],
        })
    return rows


def curve_value_origins(result: dict) -> list[str]:
    """Classify every curve value by how it was produced."""
    times=np.asarray(result.get('time') or [],dtype=float)
    manifest=result.get('manifest') or {}
    model=str(manifest.get('model',''))
    assumptions=manifest.get('assumptions') or {}
    if model.startswith('datasheet-screening-'):
        if assumptions.get('evidence_calibrated'):
            limit_days=float(assumptions.get('evidence_window_days') or 0)
            return ['Extrapolé' if limit_days and value*365.25>limit_days+1e-9 else 'Interpolé'
                    for value in times]
        return ['Estimé']*len(times)
    points=result.get('observed_points') or []
    if points:
        observed_times=[]
        for point in points:
            if point.get('time_days') is not None:
                observed_times.append(float(point['time_days']))
            elif point.get('time_hours') is not None:
                observed_times.append(float(point['time_hours'])/24)
        tolerance=max(1e-8,float(np.max(times))*1e-8 if len(times) else 1e-8)
        return ['Observé' if any(abs(value-observed)<=tolerance for observed in observed_times) else 'Interpolé'
                for value in times]
    if model.startswith('synthetic-'):
        return ['Synthétique']*len(times)
    return ['Calculé']*len(times)


def curve_value_origin(result: dict, index: int = -1) -> str:
    """Return the provenance label for one point of a result curve."""
    origins=curve_value_origins(result)
    return origins[index] if origins else 'Non disponible'


def refresh_result_fingerprint(result: dict) -> str:
    """Refresh the reproducibility fingerprint after adding UI provenance."""
    fingerprint=sha256(json.dumps(result.get('manifest') or {},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    result['fingerprint']=fingerprint
    return fingerprint

def result_explanation(result: dict) -> str:
    """Explain the result in plain French for the result card and exports."""
    manifest=result['manifest']; inputs=manifest['inputs']
    crossing=result.get('crossing_estimate_years')
    end=float(result['retention'][-1])
    if manifest.get('evidence_level')=='exploratory_family_assumptions':
        threshold_detail=(f" et atteint le seuil après {format_years_months(float(crossing))}. "
                          if crossing is not None else ". ")
        return ("La meilleure estimation documentaire disponible "
                f"conserve {end:.1f} % du module initial à l’horizon choisi"
                +threshold_detail+
                "La ligne centrale est la valeur de travail ; la plage autour d’elle mesure la sensibilité du transfert de famille au grade.")
    evidence_window=float((manifest.get('assumptions') or {}).get('evidence_window_days') or 0)
    if crossing is not None and evidence_window and float(crossing)*365.25>evidence_window:
        threshold_sentence=(f"Le seuil de {inputs['threshold']:g} % est franchi après environ "
                            f"{format_years_months(float(crossing))} selon le prolongement central, soit après "
                            f"la fenêtre publiée de {evidence_window:g} jours. Cette durée est l’estimation de travail "
                            "à comparer aux essais futurs ; sa confiance est plus faible que dans la fenêtre observée.")
    elif crossing is None:
        threshold_sentence='Le seuil choisi n’est pas franchi dans l’horizon affiché.'
    else:
        threshold_sentence=f"Le calcul central atteint {inputs['threshold']:g} % après environ {format_years_months(float(crossing))}."
    horizon_text=(inputs.get('horizon_display') or {}).get('label') or format_years_months(float(inputs['horizon_years']))
    return (f"À la fin de l’horizon de {horizon_text}, la courbe centrale conserve "
            f"{end:.1f} % du module initial. {threshold_sentence} Ce résultat décrit le modèle et ses "
            "hypothèses ; il ne remplace pas un essai sur le matériau réel.")


def _linear_crossing(times: np.ndarray, values: np.ndarray, target: float) -> float | None:
    """Return an exact crossing on a piecewise-linear curve, without grid discretization."""
    if len(times)!=len(values) or not len(times):
        return None
    if float(values[0])<=target:
        return float(times[0])
    for index in range(1,len(times)):
        before,after=float(values[index-1]),float(values[index])
        if before>target>=after:
            if before==after:
                return float(times[index])
            fraction=(before-target)/(before-after)
            return float(times[index-1]+fraction*(times[index]-times[index-1]))
    return None

def observed_projection(rows: list[dict], temperature_c: float, humidity_rh: float,
                        thickness_mm: float, horizon_days: float, threshold_percent: float,
                        experiment_id: str | None = None) -> dict:
    """Interpolate one measured condition without extrapolation."""
    matching=[r for r in rows if abs(r['temperature_C']-temperature_c)<1e-9
              and abs(r['humidity_RH']-humidity_rh)<1e-9
              and abs(r['thickness_mm']-thickness_mm)<1e-9
              and (experiment_id is None or r.get('experiment_id')==experiment_id)]
    if len(matching)<3:
        raise ValueError('Aucune série comportant au moins trois temps ne correspond exactement à ces conditions.')
    experiments={r.get('experiment_id') for r in matching}
    if len(experiments)>1:
        raise ValueError('Plusieurs expériences correspondent à ces conditions : choisissez explicitement un lot avant le calcul.')
    matching=sorted(matching,key=lambda r:r['time_days'])
    observed_times=[float(r['time_days']) for r in matching]
    if observed_times[0]!=0 or len(set(observed_times))!=len(observed_times):
        raise ValueError('La série doit commencer à t=0 et ne contenir aucun temps dupliqué.')
    max_day=max(r['time_days'] for r in matching)
    if horizon_days>max_day:
        raise ValueError(f'Extrapolation refusée : cette série est observée jusqu’à {max_day:g} jours.')
    t=np.linspace(0,horizon_days,241)
    observed_t=np.asarray([r['time_days'] for r in matching]); observed_e=np.asarray([r['modulus_MPa'] for r in matching])
    modulus=np.interp(t,observed_t,observed_e); e0=float(matching[0]['initial_modulus_MPa'])
    retention=modulus/e0*100
    uncertainty=max(float(r.get('extraction_uncertainty_pct') or 0) for r in matching)/100
    lower=modulus*(1-uncertainty); upper=modulus*(1+uncertainty)
    target=e0*threshold_percent/100
    crossing=_linear_crossing(observed_t,observed_e,target)
    if crossing is not None and crossing>horizon_days: crossing=None
    lower_cross=_linear_crossing(t,lower,target); upper_cross=_linear_crossing(t,upper,target)
    pending=any(r['review_status']=='pending' for r in matching)
    source=matching[0]
    manifest={'model':'piecewise-linear-observed-v1','dataset':'material_observations',
              'material_status':'PENDING_REVIEW' if pending else 'ACCEPTED',
              'experiment_id':source.get('experiment_id'),
              'inputs':{'temperature':temperature_c,'humidity_RH':humidity_rh,'thickness_mm':thickness_mm,
                        'horizon':horizon_days,'threshold':threshold_percent,'e0':e0},
              'source':{'id':source.get('source_id'),'title':source.get('source_title'),
                        'url':source.get('source_url'),'doi':source.get('source_doi'),
                        'location':source.get('source_location')},
              'validity':{'time_days':[0,max_day],'protocol':source.get('protocol'),
                          'measurement_temperature_C':source.get('measurement_temperature_C')},
              'uncertainty':{
                  'kind':'estimated_digitization_error','relative_half_width':uncertainty,
                  'label':'Incertitude de numérisation estimée',
                  'coverage':'non_statistical',
                  'excludes':['dispersion entre éprouvettes','variabilité entre lots','incertitude prédictive'],
              },
              'warnings':['La bande montre uniquement une erreur de lecture estimée des points de la figure.',
                          'Elle ne constitue pas un intervalle de prédiction ni la dispersion expérimentale totale.'],
              'status':'APERÇU DE DONNÉES EN ATTENTE — NON VALIDÉ' if pending else 'INTERPOLATION DU CORPUS ACCEPTÉ — NON EXTRAPOLÉ'}
    fingerprint=sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return {'time':t.tolist(),'modulus':modulus.tolist(),'lower':lower.tolist(),'upper':upper.tolist(),
            'retention':retention.tolist(),'crossing':crossing,'crossing_interval':[lower_cross,upper_cross],
            'fraction_crossing':float(crossing is not None),'rate':None,'manifest':manifest,
            'fingerprint':fingerprint,'observed_points':matching,'pending':pending}

def published_evidence_curve(rows: list[dict], experiment_id: str, horizon_days: float,
                             threshold_percent: float, uncertainty_mode: str = 'sd') -> dict:
    """Interpolate one peer-reviewed series with either reported SD or the mean's 95% CI."""
    group=sorted((r for r in rows if r['experiment_id']==experiment_id),key=lambda r:r['time_days'])
    if len(group)<3:
        raise ValueError('Cette formulation ne comporte pas assez de temps publiés.')
    if not np.isfinite(horizon_days) or horizon_days<0:
        raise ValueError('Horizon invalide.')
    max_day=float(group[-1]['time_days'])
    if horizon_days>max_day:
        raise ValueError(f'Extrapolation refusée : la publication observe cette série jusqu’à {max_day:g} jours.')
    if not 1<=threshold_percent<=100:
        raise ValueError('Le seuil doit être compris entre 1 et 100 %.')
    if uncertainty_mode not in {'sd','ci95'}:
        raise ValueError('Mode d’incertitude inconnu.')
    observed_t=np.asarray([r['time_days'] for r in group],dtype=float)
    observed_e=np.asarray([r['modulus_mpa'] for r in group],dtype=float)
    observed_sd=np.asarray([r.get('standard_deviation_mpa') or 0 for r in group],dtype=float)
    sample_counts=np.asarray([r.get('sample_count') or 0 for r in group],dtype=float)
    times=np.linspace(0,horizon_days,241)
    modulus=np.interp(times,observed_t,observed_e)
    if uncertainty_mode=='ci95':
        if np.any(sample_counts<2):
            raise ValueError('Le nombre d’éprouvettes est requis pour calculer l’IC95 % de la moyenne.')
        observed_half_width=np.asarray([
            student_t.ppf(.975,count-1)*sd/np.sqrt(count)
            for sd,count in zip(observed_sd,sample_counts)
        ])
        uncertainty_label='IC95 % de la moyenne publiée'
        uncertainty_kind='confidence_interval_of_mean'
    else:
        observed_half_width=observed_sd
        uncertainty_label='Dispersion publiée ±1 écart-type'
        uncertainty_kind='reported_standard_deviation'
    half_width=np.interp(times,observed_t,observed_half_width)
    lower=np.maximum(modulus-half_width,0); upper=modulus+half_width
    e0=float(observed_e[0]); retention=modulus/e0*100
    target=e0*threshold_percent/100
    crossing=_linear_crossing(observed_t,observed_e,target)
    if crossing is not None and crossing>horizon_days: crossing=None
    lower_cross=_linear_crossing(times,lower,target); upper_cross=_linear_crossing(times,upper,target)
    source=group[0]
    manifest={
        'model':'piecewise-linear-published-v1','dataset':'aging_evidence',
        'evidence_level':'published_observation','experiment_id':experiment_id,
        'inputs':{'horizon_days':horizon_days,'threshold':threshold_percent,'e0':e0},
        'source':{'id':source.get('source_id'),'title':source.get('source_title'),
                  'url':source.get('source_url'),'doi':source.get('source_doi'),
                  'location':source.get('source_location')},
        'validity':{'time_days':[0,max_day],'exposure_mode':source.get('exposure_mode'),
                    'protocol':source.get('protocol')},
        'uncertainty':{'kind':uncertainty_kind,'mode':uncertainty_mode,
                       'label':uncertainty_label,
                       'sample_count':int(sample_counts[0]) if np.all(sample_counts==sample_counts[0]) else sample_counts.tolist(),
                       'interpretation':('Variabilité observée entre les sept éprouvettes de chaque point.'
                                         if uncertainty_mode=='sd' else
                                         'Incertitude statistique sur la moyenne ; elle est plus étroite que la dispersion des éprouvettes.')},
        'status':'MESURES PUBLIÉES — INTERPOLATION SANS EXTRAPOLATION',
        'warnings':['Cette courbe décrit la formulation publiée, pas tous les polypropylènes.',
                    'Les conditions météorologiques détaillées ne sont pas transférées à un autre site.',
                    'Cette bande n’est pas un intervalle de prédiction de durée de vie.'],
    }
    fingerprint=sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return {'time':times.tolist(),'modulus':modulus.tolist(),'lower':lower.tolist(),'upper':upper.tolist(),
            'retention':retention.tolist(),'crossing':crossing,'crossing_interval':[lower_cross,upper_cross],
            'fraction_crossing':float(crossing is not None),'rate':None,'manifest':manifest,
            'fingerprint':fingerprint,'observed_points':group,'pending':False}

def _matrix(rows):
    missing=sorted({k for r in rows for k in FEATURES+['residual_property'] if k not in r})
    if missing:
        raise ValueError('Ancien format incompatible : réimportez le CSV avec les colonnes hygrothermiques ('+', '.join(missing)+').')
    x=np.asarray([[r[k] for k in FEATURES] for r in rows],dtype=float)
    y=np.asarray([r['residual_property'] for r in rows],dtype=float)
    groups=np.asarray([r['experiment_id'] for r in rows])
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError('Le dataset contient des valeurs non finies.')
    return x,y,groups

def evaluate_baselines(rows: list[dict]) -> dict:
    """Compare models with group-wise CV; returns metrics and SHAP for XGBoost."""
    if len(rows) < 12:
        raise ValueError('Il faut au moins 12 mesures pour comparer les modèles.')
    x,y,groups=_matrix(rows)
    unique=np.unique(groups)
    if len(unique) < 3:
        raise ValueError('Il faut au moins trois expériences indépendantes pour la validation croisée.')
    folds=min(5,len(unique)); cv=GroupKFold(n_splits=folds)
    xgb_available=True
    try:
        from xgboost import XGBRegressor
        booster=XGBRegressor(n_estimators=250,max_depth=3,learning_rate=.04,subsample=.85,
                             colsample_bytree=.9,reg_lambda=2,objective='reg:squarederror',random_state=42,n_jobs=1)
        booster_name='XGBoost'
    except Exception:
        xgb_available=False
        booster=HistGradientBoostingRegressor(max_iter=250,max_depth=3,learning_rate=.04,
                                              l2_regularization=2,random_state=42)
        booster_name='Gradient Boosting (secours)'
    models={
        'Ridge':make_pipeline(StandardScaler(),Ridge(alpha=1.0)),
        'Random Forest':RandomForestRegressor(n_estimators=250,min_samples_leaf=2,random_state=42,n_jobs=1),
        booster_name:booster,
    }
    metrics=[]
    for name,model in models.items():
        scores=cross_validate(model,x,y,groups=groups,cv=cv,
            scoring={'r2':'r2','rmse':'neg_root_mean_squared_error','mae':'neg_mean_absolute_error'},
            return_train_score=True,n_jobs=1)
        metrics.append({
            'model':name,
            'r2_mean':float(np.mean(scores['test_r2'])),
            'rmse_mean':float(-np.mean(scores['test_rmse'])),
            'mae_mean':float(-np.mean(scores['test_mae'])),
            'train_r2_mean':float(np.mean(scores['train_r2'])),
            'overfit_gap':float(np.mean(scores['train_r2'])-np.mean(scores['test_r2'])),
        })
    metrics.sort(key=lambda m:m['rmse_mean'])
    best_name=metrics[0]['model']; best=models[best_name].fit(x,y)
    predictions=np.asarray(best.predict(x),dtype=float)
    importance=[]
    xgb=models[booster_name].fit(x,y)
    try:
        if not xgb_available: raise RuntimeError('XGBoost natif indisponible')
        import shap
        values=shap.TreeExplainer(xgb).shap_values(x); weights=np.mean(np.abs(values),axis=0)
        method='SHAP moyen absolu sur le corpus complet (interprétation, pas validation)'
    except Exception:
        from sklearn.inspection import permutation_importance
        weights=permutation_importance(xgb,x,y,n_repeats=10,random_state=42,scoring='neg_mean_squared_error').importances_mean
        weights=np.maximum(weights,0)
        method='Importance par permutation sur le corpus complet (interprétation, pas validation)'
    if float(np.sum(weights)) <= 0:
        weights=np.ones(len(FEATURES),dtype=float)
    total=float(np.sum(weights))
    for feature,weight in sorted(zip(FEATURES,weights),key=lambda p:float(p[1]),reverse=True):
        importance.append({'feature':feature,'label':FEATURE_LABELS[feature],'importance':float(weight/total)})
    return {
        'features':FEATURES,'target':'residual_property','folds':folds,
        'split':'GroupKFold par experiment_id','metrics':metrics,'best_model':best_name,
        'fit_on_all':{'r2':float(r2_score(y,predictions)),'rmse':float(mean_squared_error(y,predictions)**.5),
                      'mae':float(mean_absolute_error(y,predictions))},
        'importance':importance,'importance_method':method,
        'xgboost_available':xgb_available,
        'limits':('Résultats exploratoires. Une validation externe par publication ou campagne distincte reste nécessaire. '
                  +('XGBoost natif actif.' if xgb_available else 'XGBoost installé mais OpenMP indisponible : Gradient Boosting de secours utilisé.')),
    }
