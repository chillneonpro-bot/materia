from io import BytesIO
from zipfile import ZipFile

import pytest

from materia import material_db
from materia.modeling import estimate_from_datasheet
from materia.planning import experiment_plan, experiment_plan_workbook


def pp_result(years=2):
    material=material_db.material('PP')
    return estimate_from_datasheet(material,1100,23,50,2,years,80,'outdoor',
                                   material_db.evidence_rows('PP','outdoor'))


def test_plan_covers_baseline_evidence_boundary_threshold_and_horizon():
    result=pp_result(2)
    plan=experiment_plan(result,5,5,3)
    days=[row['time_days'] for row in plan['rows']]
    assert plan['timepoints']==5
    assert plan['total_specimens']==75
    assert plan['reserved_validation_lots']==1
    assert days[0]==0
    assert 120 in days
    assert days[-1]==pytest.approx(730.5)
    assert any('franchissement' in row['role'] for row in plan['rows'])
    assert any(row['phase']=='Phase 3 · horizon cible' for row in plan['rows'])
    assert 'ne prédit pas un pourcentage' in plan['score_warning']


def test_plan_is_deterministic_and_validates_campaign_size():
    result=pp_result(1)
    assert experiment_plan(result,7,6,2)['rows']==experiment_plan(result,7,6,2)['rows']
    with pytest.raises(ValueError,match='entre 5 et 10'):
        experiment_plan(result,4,5,3)
    with pytest.raises(ValueError,match='éprouvettes'):
        experiment_plan(result,5,2,3)
    with pytest.raises(ValueError,match='lots'):
        experiment_plan(result,5,5,0)


def test_short_in_domain_plan_uses_balanced_measurement_times():
    plan=experiment_plan(pp_result(120/365.25),5,5,3)
    assert [row['time_days'] for row in plan['rows']]==[0.,30.,60.,90.,120.]


def test_plan_workbook_is_ready_for_lab_and_blind_validation_import():
    result=pp_result(2); plan=experiment_plan(result,5,5,3)
    blob=experiment_plan_workbook(plan,result,'Plan PP')
    archive=ZipFile(BytesIO(blob)); names=set(archive.namelist())
    assert blob.startswith(b'PK')
    assert 'xl/charts/chart1.xml' in names
    assert {'xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml','xl/worksheets/sheet3.xml','xl/worksheets/sheet4.xml'}<=names
    shared=archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert 'Import direct dans Validation aveugle' in shared
    assert 'Validation aveugle réservée' in shared
    assert result['fingerprint'] in shared
    assert all(column in shared for column in ('modulus_mpa','replicate_id','lot_id','specimen_id'))
