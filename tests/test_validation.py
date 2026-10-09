import math
import pytest

from materia import material_db
from materia.modeling import estimate_from_datasheet, published_evidence_curve, standard_profile
from materia.validation import (pp_model_benchmark, pp_short_term_prediction,
                                pp_literature_only_benchmark, pp_temporal_holdout, uncertainty_budget,
                                validity_diagnostic, iir_temporal_holdout, iir_temperature_holdout,
                                flax_temperature_transfer_benchmark)


def test_pp_temporal_holdout_is_explicitly_internal():
    report=pp_temporal_holdout(material_db.evidence_rows('PP','outdoor'))
    assert report['test_count']==4
    assert math.isfinite(report['mae_mpa']) and report['mae_mpa']>0
    assert report['status']=='MODÈLE INTERNE AMÉLIORÉ - VALIDATION EXTERNE REQUISE'
    assert report['mape_pct']<1
    assert report['within_reported_sd_count']==4
    assert report['benchmark']['methods']['exponential']['mape_pct']>20
    assert report['external_reference']['decision']=='EXCLUE DE LA VALIDATION NUMÉRIQUE'


def test_pp_benchmark_and_short_term_interval_are_honest_and_tight():
    rows=material_db.evidence_rows('PP','outdoor')
    benchmark=pp_model_benchmark(rows)
    assert benchmark['recommended_method']=='hierarchical_two_phase'
    prediction=pp_short_term_prediction(600,560,rows)
    assert prediction['lower_120_mpa']<prediction['predicted_120_mpa']<prediction['upper_120_mpa']
    assert prediction['empirical_half_width_pct']<2.1
    assert 'VALIDATION EXTERNE' in prediction['status']


def test_pp_literature_only_case_is_checked_without_target_ageing_measurements():
    report=pp_literature_only_benchmark(material_db.evidence_rows('PP','outdoor'))
    assert report['test_count']==8
    assert report['mape_pct']==pytest.approx(2.7498356554)
    assert report['mae_mpa']==pytest.approx(13.7214843983)
    assert report['empirical_half_width_pct']==pytest.approx(3.4109767496)
    assert report['empirical_coverage_pct']==100
    assert report['by_day']['30']['mape_pct']==pytest.approx(2.7184879264)
    assert report['by_day']['120']['mape_pct']==pytest.approx(2.7811833843)
    assert all(row['relative_error_pct']<=report['empirical_half_width_pct']+1e-12 for row in report['details'])


def test_pp_benchmark_uses_named_time_anchors_when_extra_rows_exist():
    rows=material_db.evidence_rows('PP','outdoor')
    baseline=pp_model_benchmark(rows)['methods']['hierarchical_two_phase']['mape_pct']
    augmented=list(reversed(rows))+[{**rows[0],'time_days':15,'modulus_mpa':590.0}]
    assert pp_model_benchmark(augmented)['methods']['hierarchical_two_phase']['mape_pct']==baseline


def test_iir_masked_interpolation_and_temperature_transfer_are_separated():
    rows=material_db.evidence_rows('IIR','immersion')
    temporal=iir_temporal_holdout(rows)
    temperature=iir_temperature_holdout(rows)
    assert temporal['test_count']==15
    assert temporal['mape_pct']==pytest.approx(6.4004515278)
    assert temporal['empirical_half_width_pct']==pytest.approx(10.8996539792)
    assert temporal['max_relative_error_pct']==pytest.approx(20.8165096456)
    assert temperature['test_count']==6
    assert temperature['mape_pct']==pytest.approx(10.6011432284)
    assert temperature['max_relative_error_pct']==pytest.approx(26.2381252684)
    assert temperature['r2']<0
    assert 'NON VALIDÉ' in temperature['status']


def test_flax_curve_transfer_is_checked_with_the_other_temperature_hidden():
    rows=material_db.observation_rows('FLAX_EPOXY',include_pending=True)
    report=flax_temperature_transfer_benchmark(rows)
    assert report['test_count']==8
    assert report['mae_mpa']==pytest.approx(725.)
    assert report['mape_pct']==pytest.approx(5.4126631961)
    assert report['r2']==pytest.approx(.9747376951)
    assert report['empirical_half_width_pct']==pytest.approx(11.4035087719)
    assert report['empirical_coverage_pct']==100


def test_validity_distinguishes_published_and_exploratory_results():
    rows=material_db.evidence_rows('PP','outdoor')
    published=published_evidence_curve(rows,'MDPI-RPP1X',120,80)
    diagnostic=validity_diagnostic(published)
    assert diagnostic['level']=='Interpolation publiée'
    assert any(row['component']=='Mesure / éprouvettes' and row['quantified'] for row in uncertainty_budget(published))
    material=material_db.material('PEEK'); profile=standard_profile(material)
    exploratory=estimate_from_datasheet(material,profile['suggested_modulus_mpa'],23,50,2,5,80)
    diagnostic=validity_diagnostic(exploratory)
    assert diagnostic['level']=='Estimation de présélection'
    assert all(check['status']!='bloquant' for check in diagnostic['checks'])
    assert 'estimation centrale utilisable' in diagnostic['conclusion']
