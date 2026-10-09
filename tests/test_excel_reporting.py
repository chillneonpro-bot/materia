from io import BytesIO
from zipfile import ZipFile

from materia import material_db
from materia.blind_prediction import compare_with_experiment, freeze_prediction
from materia.excel_reporting import (blind_validation_template_workbook,
                                     blind_validation_workbook,
                                     comparison_workbook, result_workbook,
                                     table_workbook)
from materia.modeling import (estimate_from_datasheet, observed_projection,
                              published_evidence_curve, standard_profile)
from materia.science import Scenario, simulate


def workbook_files(blob: bytes) -> tuple[ZipFile, set[str]]:
    archive = ZipFile(BytesIO(blob))
    return archive, set(archive.namelist())


def test_result_workbook_contains_curve_chart_and_source_details():
    rows = material_db.evidence_rows('PP', 'outdoor')
    result = published_evidence_curve(rows, 'MDPI-RPP1X', 120, 80, 'sd')
    blob = result_workbook(result, 'Mesures publiées · PP recyclé')
    archive, names = workbook_files(blob)
    assert blob.startswith(b'PK')
    assert 'xl/charts/chart1.xml' in names
    assert 'xl/worksheets/sheet4.xml' in names  # mesures source
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    chart = archive.read('xl/charts/chart1.xml').decode('utf-8')
    assert '10.3390/polym16131788' in shared
    assert 'Mesures source' in shared
    assert 'Validité scientifique du résultat' in shared
    assert "Budget d'incertitude" in shared
    assert 'Origine de la valeur' in shared
    assert 'Observé' in shared and 'Interpolé' in shared
    assert 'Module de Young en fonction du temps' in chart


def test_comparison_workbook_contains_native_chart_and_all_scenarios():
    values = [('Polymère A', simulate(Scenario())),
              ('Polymère B', simulate(Scenario(material='demo-b')))]
    blob = comparison_workbook(values, 'Comparaison pédagogique')
    archive, names = workbook_files(blob)
    assert 'xl/charts/chart1.xml' in names
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    chart = archive.read('xl/charts/chart1.xml').decode('utf-8')
    assert 'Polymère A' in shared
    assert 'Polymère B' in shared
    assert 'Origine de la valeur' in shared
    assert 'Synthétique' in shared
    assert 'Compatibilité de la comparaison' in shared
    assert 'Conditions comparables' in shared
    assert 'Module conservé en fonction du temps' in chart


def test_tabular_export_neutralizes_excel_formula_prefixes():
    blob = table_workbook([{'nom': '=1+1', 'valeur': 2}], 'Test', 'Données')
    archive, _ = workbook_files(blob)
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert "'=1+1" in shared


def test_datasheet_and_accepted_observation_exports_keep_their_origin():
    material = material_db.material('PP')
    profile = standard_profile(material)
    datasheet = estimate_from_datasheet(material, profile['suggested_modulus_mpa'], 23, 50, 2, 10, 80)
    datasheet['manifest']['inputs']['horizon_display'] = {'value': 120, 'unit': 'months', 'label': '120 mois'}
    archive, _ = workbook_files(result_workbook(datasheet, 'Projection fiche matériau'))
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert '120 mois' in shared
    assert 'ESTIMATION DOCUMENTAIRE DE PRÉSÉLECTION' in shared

    informed = estimate_from_datasheet(material, 1100, 23, 50, 2, 2, 80, 'outdoor',
                                       material_db.evidence_rows('PP', 'outdoor'))
    archive, _ = workbook_files(result_workbook(informed, 'Projection PP documentée'))
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert 'Plage standardisée ±10 % sur la vitesse' in shared
    assert 'Minimum observé du corpus (MPa)' not in shared
    assert 'Maximum observé du corpus (MPa)' not in shared

    rows = material_db.observation_rows('FLAX_EPOXY')
    observed = observed_projection(rows, 20, 90, 2.5, 30, 80)
    archive, names = workbook_files(result_workbook(observed, 'Observations acceptées'))
    shared = archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert '10.1016/j.compositesb.2012.12.010' in shared
    assert 'xl/worksheets/sheet4.xml' in names


def test_blind_validation_workbook_contains_chart_metrics_and_lock():
    material=material_db.material('PP'); profile=standard_profile(material)
    result=estimate_from_datasheet(material,profile['suggested_modulus_mpa'],23,50,2,120/365.25,80,
                                   'outdoor',material_db.evidence_rows('PP','outdoor'))
    result['manifest']['inputs']['horizon_display']={'value':120,'unit':'days','label':'120 jours'}
    snapshot=freeze_prediction(result,'PP avant essais','2026-09-30')
    observations=[]
    for day in (0,30,60,90,120):
        import numpy as np
        predicted=float(np.interp(day,np.asarray(snapshot['time_years'])*365.25,snapshot['central_mpa']))
        observations.append({'time_days':day,'modulus_mpa':predicted,'replicate_id':str(day)})
    report=compare_with_experiment(snapshot,observations)
    archive,names=workbook_files(blind_validation_workbook(snapshot,report))
    assert 'xl/charts/chart1.xml' in names
    shared=archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert 'Validation aveugle Materia' in shared
    assert snapshot['lock_sha256'] in shared
    assert 'Couverture P10–P90' in shared
    assert 'xl/worksheets/sheet4.xml' in names
    assert 'Vue par lot et par temps' in shared
    assert 'Vue par éprouvette' in shared
    assert 'Aucune valeur n’est exclue automatiquement' in shared


def test_blind_validation_template_has_required_columns():
    archive,names=workbook_files(blind_validation_template_workbook())
    assert 'xl/tables/table1.xml' in names
    shared=archive.read('xl/sharedStrings.xml').decode('utf-8')
    assert all(column in shared for column in ('time_days','modulus_mpa','replicate_id','lot_id','specimen_id'))
