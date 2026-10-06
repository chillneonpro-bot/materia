from io import BytesIO

import pytest
from openpyxl import Workbook

from materia.blind_prediction import (compare_with_experiment, freeze_prediction,
                                      parse_validation_file, verify_snapshot)
from materia.modeling import estimate_from_datasheet


def prediction():
    material={'id':'IIR','name':'Caoutchouc butyle','family':'Élastomère',
              'subtype':'Caoutchouc réticulé','mechanisms':'Thermo-oxydation'}
    return estimate_from_datasheet(material,10,23,50,5,3,70,'indoor')


def test_snapshot_is_verifiable_and_detects_mutation():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    assert verify_snapshot(snapshot)
    snapshot['central_mpa'][1]+=1
    assert not verify_snapshot(snapshot)


def test_later_experiment_scores_frozen_prediction():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    report=compare_with_experiment(snapshot,[{'time_days':0,'modulus_mpa':10},{'time_days':365,'modulus_mpa':9}])
    assert report['count']==2
    assert report['mape_pct']>=0
    assert 0<=report['interval_coverage_pct']<=100
    assert report['validation']['verdict']=='POINTS_INSUFFISANTS'
    with pytest.raises(ValueError,match='dépasse'):
        compare_with_experiment(snapshot,[{'time_days':2000,'modulus_mpa':8}])


def test_validation_separates_local_accuracy_from_general_reliability():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    observations=[]
    for day in [0,100,200,300,400]:
        expected=float(__import__('numpy').interp(day,
            __import__('numpy').asarray(snapshot['time_years'])*365.25,snapshot['central_mpa']))
        observations.append({'time_days':day,'modulus_mpa':expected})
    report=compare_with_experiment(snapshot,observations)
    assert report['validation']['central_curve_pass'] is True
    assert report['validation']['verdict']=='COURBE_CENTRALE_ACCEPTABLE_SUR_UNE_CAMPAGNE'
    assert report['validation']['predictive_interval_evaluable'] is False


def test_replicates_do_not_overweight_one_timepoint():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    observations=[]
    times=[0,100,200,300,400]
    for day in times:
        expected=float(__import__('numpy').interp(day,
            __import__('numpy').asarray(snapshot['time_years'])*365.25,snapshot['central_mpa']))
        observations.append({'time_days':day,'modulus_mpa':expected,'replicate_id':f'{day}-a'})
    observations.extend({'time_days':0,'modulus_mpa':20,'replicate_id':f'outlier-{index}'} for index in range(20))
    report=compare_with_experiment(snapshot,observations)
    assert report['count']==5
    assert report['observation_count']==25
    assert report['details'][0]['replicates']==21
    assert report['mape_pct']<report['details'][0]['relative_error_pct']


def test_snapshot_rejects_invalid_curve_even_with_recomputed_hash():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    snapshot['lower_mpa'][2]=snapshot['central_mpa'][2]+1
    from hashlib import sha256
    from materia.blind_prediction import _canonical
    snapshot['lock_sha256']=sha256(_canonical({k:v for k,v in snapshot.items() if k!='lock_sha256'})).hexdigest()
    assert verify_snapshot(snapshot) is False


def test_validation_file_parser_accepts_csv_and_xlsx():
    csv_rows=parse_validation_file(b'time_days,modulus_mpa,replicate_id\n0,1000,A\n30,950,B\n','mesures.csv')
    assert csv_rows[1]=={'time_days':30.,'modulus_mpa':950.,'replicate_id':'B',
                         'lot_id':'Lot non renseigné','specimen_id':'B'}
    workbook=Workbook(); sheet=workbook.active
    sheet.append(['time_days','modulus_mpa','replicate_id']); sheet.append([0,1000,'A']); sheet.append([30,950,'B'])
    output=BytesIO(); workbook.save(output)
    assert parse_validation_file(output.getvalue(),'mesures.xlsx')==csv_rows


def test_validation_parser_preserves_lot_and_specimen_or_derives_lot():
    explicit=parse_validation_file(
        b'time_days,modulus_mpa,replicate_id,lot_id,specimen_id\n30,950,R1,Lot-A,SPEC-01\n','mesures.csv')
    assert explicit[0]['lot_id']=='Lot-A'
    assert explicit[0]['specimen_id']=='SPEC-01'
    derived=parse_validation_file(
        b'time_days,modulus_mpa,replicate_id\n30,950,L2-J30-E1\n','mesures.csv')
    assert derived[0]['lot_id']=='L2'


def test_comparison_keeps_flagged_specimen_in_metrics():
    snapshot=freeze_prediction(prediction(),'IIR avant essais','2026-09-30')
    observations=[]
    for index,value in enumerate([9.9,10.,10.,10.1,14.],1):
        observations.append({'time_days':0,'modulus_mpa':value,'replicate_id':f'L1-T0-E{index}',
                             'lot_id':'L1','specimen_id':f'L1-T0-E{index}'})
    report=compare_with_experiment(snapshot,observations)
    assert report['specimen_analysis']['flagged_count']==1
    assert report['details'][0]['observed_mpa']==pytest.approx(sum([9.9,10.,10.,10.1,14.])/5)
    assert all(row['included_in_validation'] for row in report['raw_observations'])


def test_validation_file_parser_rejects_missing_columns():
    with pytest.raises(ValueError,match='Colonnes obligatoires'):
        parse_validation_file(b'time,module\n0,1000\n','mesures.csv')
