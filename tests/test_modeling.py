import math
import pytest
from materia import material_db
from materia.modeling import (evaluate_baselines, observed_projection, standard_profile,
    estimate_from_datasheet, format_years_months, evidence_assessment,
    sampled_curve_rows, published_evidence_curve, result_explanation,
    curve_value_origin, curve_value_origins, refresh_result_fingerprint,
    _literature_ensemble_profile)


def synthetic_rows():
    rows=[]
    for i,(temp,rh,thickness) in enumerate([(40,50,1.0),(50,65,1.2),(60,75,1.5),(70,85,2.0)]):
        for hours in [0,100,300,700]:
            rate=(.00008+temp/5_000_000+rh/10_000_000)/thickness
            rows.append({'experiment_id':f'E{i}','temperature_C':temp,'humidity_RH':rh,
                         'time_hours':hours,'thickness_mm':thickness,
                         'residual_property':math.exp(-rate*hours)})
    return rows


def test_groupwise_ml_report():
    report=evaluate_baselines(synthetic_rows())
    assert report['folds']==4
    assert {'Ridge','Random Forest'} < {m['model'] for m in report['metrics']}
    assert report['target']=='residual_property'
    assert abs(sum(i['importance'] for i in report['importance'])-1)<1e-9


def test_observed_projection_interpolates_and_refuses_extrapolation():
    rows=[]
    for days,value in [(0,2000),(10,1800),(20,1600)]:
        rows.append({'experiment_id':'E1','time_days':days,'modulus_MPa':value,
            'initial_modulus_MPa':2000,'temperature_C':40,'humidity_RH':90,
            'thickness_mm':2.5,'review_status':'accepted','extraction_uncertainty_pct':2})
    result=observed_projection(rows,40,90,2.5,15,80)
    assert result['modulus'][-1]==pytest.approx(1700)
    assert result['pending'] is False
    assert result['lower'][-1]==pytest.approx(1666)
    assert result['crossing'] is None
    assert observed_projection(rows,40,90,2.5,20,85)['crossing']==pytest.approx(15)
    with pytest.raises(ValueError,match='Extrapolation refusée'):
        observed_projection(rows,40,90,2.5,21,80)
    with pytest.raises(ValueError,match='correspond exactement'):
        observed_projection(rows,50,90,2.5,15,80)


def test_observed_projection_refuses_to_merge_independent_experiments():
    rows=[]
    for experiment in ('A','B'):
        for days,value in ((0,2000),(10,1800),(20,1600)):
            rows.append({'experiment_id':experiment,'time_days':days,'modulus_MPa':value,
                'initial_modulus_MPa':2000,'temperature_C':40,'humidity_RH':90,
                'thickness_mm':2.5,'review_status':'accepted','extraction_uncertainty_pct':2})
    with pytest.raises(ValueError,match='Plusieurs expériences'):
        observed_projection(rows,40,90,2.5,15,80)
    assert observed_projection(rows,40,90,2.5,15,80,'A')['modulus'][-1]==pytest.approx(1700)


def test_datasheet_estimator_uses_environment_and_reports_threshold():
    material={'id':'PP','name':'Polypropylène','family':'Polyoléfine',
              'subtype':'Thermoplastique','mechanisms':'Photo-oxydation; thermo-oxydation'}
    profile=standard_profile(material)
    assert profile['suggested_modulus_mpa'] == 1500
    assert profile['reference_property']['verification_status']=='cross_checked_official'
    indoor=estimate_from_datasheet(material,1500,23,50,2,10,80,'indoor')
    outdoor=estimate_from_datasheet(material,1500,23,50,2,10,80,'outdoor')
    assert indoor['modulus'][0] == 1500
    assert outdoor['modulus'][-1] < indoor['modulus'][-1]
    assert indoor['crossing_estimate_years'] > 0
    assert indoor['crossing_interval'][0] < indoor['crossing_estimate_years'] < indoor['crossing_interval'][1]
    assert indoor['crossing_interval'][1] / indoor['crossing_interval'][0] == pytest.approx(1.5/.65)
    assert indoor['manifest']['status'].startswith('ESTIMATION DOCUMENTAIRE DE PRÉSÉLECTION')
    assert indoor['manifest']['evidence_level']=='exploratory_family_assumptions'
    assert indoor['manifest']['uncertainty']['kind']=='scenario_sensitivity'
    assert indoor['manifest']['uncertainty']['display_band'] is True

    evidence=[]
    for experiment,values in {'a':[(0,600),(30,570),(120,550)],'b':[(0,520),(30,490),(120,460)],'c':[(0,540),(30,510),(120,485)]}.items():
        evidence.extend({'experiment_id':experiment,'time_days':day,'modulus_mpa':value} for day,value in values)
    calibrated=estimate_from_datasheet(material,1500,23,50,2,10,80,'outdoor',evidence)
    assert calibrated['manifest']['assumptions']['evidence_calibrated'] is True
    assert calibrated['crossing_interval'][1] / calibrated['crossing_interval'][0] < 3
    assert calibrated['manifest']['model']=='datasheet-screening-v5'
    assert calibrated['manifest']['uncertainty']['kind']=='internal_formulation_iqr'
    assert calibrated['manifest']['uncertainty']['predictive_interval_validated'] is False
    assert calibrated['manifest']['source']['doi'] is None or isinstance(calibrated['manifest']['source']['doi'],str)
    assert evidence_assessment(calibrated)['level']=='Niveau 1 sur 4'
    short_term=estimate_from_datasheet(material,1500,23,50,2,120/365.25,80,'outdoor',evidence)
    assert evidence_assessment(short_term)['level']=='Niveau 2 sur 4'
    assert len(sampled_curve_rows(calibrated))==9


def test_ambient_humidity_does_not_change_immersion_scenario():
    material={'id':'IIR','name':'Caoutchouc butyle','family':'Élastomère',
              'subtype':'Élastomère','mechanisms':'Oxydation'}
    dry=estimate_from_datasheet(material,10,23,0,5,3,70,'immersion')
    humid=estimate_from_datasheet(material,10,23,100,5,3,70,'immersion')
    assert dry['crossing_estimate_years']==humid['crossing_estimate_years']
    assert dry['manifest']['assumptions']['humidity_factor']==1
    assert dry['manifest']['uncertainty']['display_band'] is True


def test_iir_uses_published_surface_only_inside_temperature_domain():
    material=material_db.material('IIR'); rows=material_db.evidence_rows('IIR','immersion')
    inside=estimate_from_datasheet(material,10,100,50,2,1/365.25,70,'immersion',rows,'milform64')
    outside=estimate_from_datasheet(material,10,23,50,2,1/365.25,70,'immersion',rows,'milform64')
    assert inside['manifest']['assumptions']['evidence_calibrated'] is True
    assert inside['manifest']['assumptions']['evidence_window_days']==pytest.approx(1)
    assert inside['manifest']['uncertainty']['kind']=='reported_standard_deviation'
    assert inside['retention'][-1]==pytest.approx(64.,abs=.1)
    assert outside['manifest']['assumptions']['evidence_calibrated'] is False
    wrong_liquid=estimate_from_datasheet(material,10,100,50,2,1/365.25,70,'immersion',rows,'water')
    assert wrong_liquid['manifest']['assumptions']['evidence_calibrated'] is False


def test_published_curve_interpolates_sd_and_refuses_extrapolation():
    rows=[]
    for day,value,sd in [(0,600,10),(30,570,20),(120,540,30)]:
        rows.append({'experiment_id':'FORMULATION-A','time_days':day,'modulus_mpa':value,
            'standard_deviation_mpa':sd,'sample_count':7,'source_id':'paper','source_location':'table 2',
            'exposure_mode':'outdoor','protocol':'tensile'})
    result=published_evidence_curve(rows,'FORMULATION-A',60,90)
    assert result['modulus'][-1]==pytest.approx(560)
    assert result['upper'][0]==pytest.approx(610)
    assert result['manifest']['evidence_level']=='published_observation'
    assert result['manifest']['uncertainty']['kind']=='reported_standard_deviation'
    origins=curve_value_origins(result)
    assert origins[0]=='Observé'
    assert curve_value_origin(result)=='Interpolé'
    assert {row['origine'] for row in sampled_curve_rows(result,time_unit='jours')} <= {'Observé','Interpolé'}
    ci=published_evidence_curve(rows,'FORMULATION-A',60,90,'ci95')
    assert ci['upper'][0] < result['upper'][0]
    assert ci['manifest']['uncertainty']['kind']=='confidence_interval_of_mean'
    with pytest.raises(ValueError,match='Extrapolation refusée'):
        published_evidence_curve(rows,'FORMULATION-A',121,90)


def test_pp_evidence_profile_is_tight_in_domain_and_expands_after_observations():
    rows=material_db.evidence_rows('PP','outdoor')
    material=material_db.material('PP')
    short=estimate_from_datasheet(material,1000,23,50,2,120/365.25,80,'outdoor',rows)
    long=estimate_from_datasheet(material,1000,23,50,2,5,80,'outdoor',rows)
    assert short['retention'][-1]==pytest.approx(90.01,abs=.05)
    short_width=(short['upper'][-1]-short['lower'][-1])/short['modulus'][-1]
    long_width=(long['upper'][-1]-long['lower'][-1])/long['modulus'][-1]
    assert .06 < short_width < .07
    assert short['manifest']['uncertainty']['kind']=='internal_holdout_interval'
    assert short['manifest']['uncertainty']['predictive_interval_validated'] is False
    assert short['manifest']['uncertainty']['internally_calibrated'] is True
    assert short['manifest']['assumptions']['independent_sources']==1
    assert short['manifest']['uncertainty']['calibration']['calibration_units']==4
    assert short['manifest']['uncertainty']['calibration']['test_predictions']==8
    assert short_width < long_width < .60
    assert all(lo<=mid<=hi for lo,mid,hi in zip(long['lower'],long['modulus'],long['upper']))
    assert long['manifest']['source']['id']=='mdpi-pp-natural-aging-2024'
    assert all(value is not None for value in short['outer_lower'])
    assert short['outer_lower'][-1] <= short['modulus'][-1] <= short['outer_upper'][-1]
    observed_outer=[value for value in long['outer_lower'] if value is not None]
    assert observed_outer
    assert long['outer_lower'][-1] is None and long['outer_upper'][-1] is None
    assert long['outer_band_window_days']==pytest.approx(120)


def test_source_ensemble_groups_by_publication_and_rejects_property_mixing():
    rows=[]
    source_profiles={'A':[1,.9,.8],'B':[1,.8,.6],'C':[1,.7,.4]}
    for source,profile in source_profiles.items():
        repeat=8 if source=='A' else 1
        for formulation in range(repeat):
            for day,retention in zip([0,10,20],profile):
                rows.append({'source_id':source,'experiment_id':f'{source}-{formulation}',
                             'time_days':day,'modulus_mpa':1000*retention,
                             'property_name':'Module de Young en traction',
                             'evidence_status':'source_verified_table'})
    rows += [{'source_id':'D','experiment_id':'WRONG','time_days':day,'modulus_mpa':value,
              'property_name':'Résistance en traction','evidence_status':'source_verified_table'}
             for day,value in [(0,1000),(10,100),(20,10)]]
    profile=_literature_ensemble_profile(rows)
    assert profile['source_count']==3
    assert profile['experiments']==10
    assert profile['median'][-1]==pytest.approx(.6)
    assert profile['calibration']['calibration_units']==3


def test_explanation_labels_extrapolated_threshold_as_working_estimate():
    material=material_db.material('PP')
    result=estimate_from_datasheet(material,1100,23,50,2,120/365.25,80,'outdoor',
                                   material_db.evidence_rows('PP','outdoor'))
    result['manifest']['inputs']['horizon_display']={'value':120,'unit':'days','label':'120 jours'}
    explanation=result_explanation(result)
    assert 'franchi après environ 1 an et 8 mois selon le prolongement central' in explanation
    assert 'estimation de travail à comparer aux essais futurs' in explanation


def test_pp_long_horizon_replaces_calibrated_band_with_projection_sensitivity():
    material=material_db.material('PP')
    result=estimate_from_datasheet(material,1100,23,50,2,2,80,'outdoor',
                                   material_db.evidence_rows('PP','outdoor'))
    assert result['manifest']['uncertainty']['kind']=='observed_rate_envelope_extrapolation'
    assert result['manifest']['uncertainty']['predictive_interval_validated'] is False
    assert result['lower'][-1] < result['modulus'][-1] < result['upper'][-1]
    assert result['upper'][-1] / result['lower'][-1] < 1.25
    assert format_years_months(result['crossing_estimate_years'])=='1 an et 8 mois'
    assert [format_years_months(value) for value in result['crossing_interval']]==['1 an','3 ans et 10 mois']
    assert curve_value_origins(result)[0]=='Interpolé'
    assert curve_value_origin(result)=='Extrapolé'


def test_generic_and_synthetic_curves_are_never_presented_as_observed():
    generic=estimate_from_datasheet(material_db.material('PET'),2000,23,50,2,2,80,'indoor')
    assert set(curve_value_origins(generic))=={'Estimé'}


def test_fingerprint_is_refreshed_after_provenance_is_added():
    result=estimate_from_datasheet(material_db.material('PET'),2500,23,50,2,2,80,'indoor')
    original=result['fingerprint']
    result['manifest']['inputs']['grade_reference']='PET-G-01'
    assert refresh_result_fingerprint(result)!=original


@pytest.mark.parametrize(('years','label'),[(0,'immédiatement'),(1/365.25,'1 jour'),(8/24/365.25,'8 heures'),(.82,'10 mois'),(1.09,'1 an et 1 mois'),(2.34,'2 ans et 4 mois')])
def test_format_years_months(years,label):
    assert format_years_months(years)==label
