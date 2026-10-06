import csv
import io
import json
import math
import numpy as np
import pytest
from materia.science import Scenario,simulate,parse_measurements,fit_measurements,result_csv,comparison_csv,REQUIRED
from materia.modeling import duration_to_days,duration_to_years

def test_analytic_threshold_and_initial_condition():
    result=simulate(Scenario(spread=0))
    assert result['modulus'][0]==2400
    assert result['crossing']==pytest.approx(-math.log(.8)/.0007)
    assert result['lower']==result['upper']
    assert result['modulus'][-1]==pytest.approx(2400*math.exp(-.0007*1200))

def test_censored_and_stiffening():
    assert simulate(Scenario(horizon=10))['crossing'] is None
    r=simulate(Scenario(material='demo-c'))
    assert r['modulus'][-1]>r['modulus'][0]
    assert r['crossing'] is None
    assert r['crossing_interval']==[None,None]
    assert r['fraction_crossing']==0

@pytest.mark.parametrize('material',['demo-a','demo-c'])
def test_initial_threshold(material):
    assert simulate(Scenario(material=material,threshold=100))['crossing']==0

@pytest.mark.parametrize('kwargs',[{'e0':0},{'e0':float('nan')},{'temperature':float('inf')},{'threshold':0},{'spread':-1}])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValueError): Scenario(**kwargs)

@pytest.mark.parametrize('kwargs',[{'material':'unknown'},{'temperature':110},{'horizon':6000}])
def test_domain_refusal(kwargs):
    with pytest.raises(ValueError): simulate(Scenario(**kwargs))

def test_reproducibility_and_provenance():
    a=simulate(Scenario()); b=simulate(Scenario())
    assert a==b
    assert a['fingerprint']!=simulate(Scenario(temperature=70))['fingerprint']
    assert 'SYNTHETIC_NOT_VALIDATED' in result_csv(a).decode('utf-8-sig')
    json.dumps(a,allow_nan=False)

def test_duration_units_and_comparison_csv():
    assert duration_to_days(1,'years')==pytest.approx(365.25)
    assert duration_to_days(1,'months')==pytest.approx(30.4375)
    assert duration_to_years(365.25,'days')==pytest.approx(1)
    with pytest.raises(ValueError): duration_to_days(1,'weeks')
    exported=comparison_csv([('A',simulate(Scenario())),('B',simulate(Scenario(material='demo-b')))]).decode('utf-8-sig')
    assert 'scenario,time,time_unit' in exported
    assert '\nA,' in exported and '\nB,' in exported

def raw(rows):
    out=io.StringIO(); w=csv.DictWriter(out,fieldnames=REQUIRED); w.writeheader(); w.writerows(rows); return out.getvalue().encode()
def measurement(**kw):
    return dict(experiment_id='a',time=24,time_unit='hours',modulus=2,modulus_unit='GPa',
                initial_modulus=2.1,initial_modulus_unit='GPa',temperature_C=60,
                humidity_RH=75,thickness_mm=1.5,measurement_temperature_C=23,
                material='test',protocol='tensile',source='synthetic-test',location='row 1')|kw

def test_normalization():
    row=parse_measurements(raw([measurement()]))[0]
    assert row['time_days']==1
    assert row['time_hours']==24
    assert row['modulus_MPa']==2000
    assert row['residual_property']==pytest.approx(2000/2100)
    assert row['status']=='pending'

@pytest.mark.parametrize('kw',[{'modulus':'NaN'},{'time':-1},{'source':''},{'protocol':'bending'},
    {'modulus_unit':'psi'},{'measurement_temperature_C':-300},{'humidity_RH':101},{'thickness_mm':0}])
def test_reject_bad_measurements(kw):
    with pytest.raises(ValueError): parse_measurements(raw([measurement(**kw)]))

def test_duplicates_and_missing_columns():
    with pytest.raises(ValueError): parse_measurements(raw([measurement(),measurement()]))
    with pytest.raises(ValueError): parse_measurements(b'time,modulus\n1,2')

def test_calibration_group_holdout():
    rows=parse_measurements(raw([measurement(experiment_id=g,time=t,time_unit='days',modulus=2000*math.exp(-.002*t),modulus_unit='MPa') for g in ['a','b'] for t in [0,100,200,300]]))
    fit=fit_measurements(rows)
    assert fit['e0']==pytest.approx(2000,rel=1e-5)
    assert fit['rate']==pytest.approx(.002,rel=1e-5)
    assert fit['holdout']=='b'
    assert fit['holdout_mae_MPa']<.001
    rows[0]['temperature_C']=70
    with pytest.raises(ValueError): fit_measurements(rows)
