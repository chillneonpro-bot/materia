from materia import material_db
from materia.modeling import estimate_from_datasheet, standard_profile
from materia.readiness import comparison_assessment, preparation_assessment


def test_preparation_score_improves_when_grade_module_and_process_are_specific():
    material=material_db.material('PP'); profile=standard_profile(material)
    evidence=material_db.evidence_rows('PP','outdoor')
    generic=preparation_assessment(material,profile['suggested_modulus_mpa'],profile['suggested_modulus_mpa'],'','',120,'outdoor',evidence)
    documented=preparation_assessment(material,1450,profile['suggested_modulus_mpa'],'PP-H301','Injection, conditionné 23 °C',120,'outdoor',evidence)
    assert generic['score']==55
    assert documented['score']==100
    assert documented['label']=='Entrées bien documentées'


def test_preparation_flags_missing_immersion_medium_and_absent_series():
    material=material_db.material('PET'); profile=standard_profile(material)
    report=preparation_assessment(material,profile['suggested_modulus_mpa'],profile['suggested_modulus_mpa'],'','',365,'immersion',[],'unspecified')
    assert report['score']==0
    assert any(row['criterion']=='Milieu' and row['status']=='À compléter' for row in report['checks'])


def test_comparison_reports_common_and_different_conditions():
    material=material_db.material('PET')
    first=estimate_from_datasheet(material,2500,23,50,2,2,80,'indoor')
    second=estimate_from_datasheet(material,2500,23,50,2,2,80,'indoor')
    compatible=comparison_assessment([('A',first),('B',second)])
    assert compatible['can_compare'] is True and compatible['score']==100
    hotter=estimate_from_datasheet(material,2500,60,50,2,2,70,'outdoor')
    reserved=comparison_assessment([('A',first),('B',hotter)])
    assert reserved['can_compare'] is True
    assert reserved['score']<compatible['score']
    assert any(row['criterion']=='Température' and row['status']=='Différent' for row in reserved['checks'])


def test_comparison_blocks_different_mechanical_properties():
    material=material_db.material('PET')
    first=estimate_from_datasheet(material,2500,23,50,2,2,80,'indoor')
    second=estimate_from_datasheet(material,2500,23,50,2,2,80,'indoor')
    second['manifest']['target_property']='Résistance en traction'
    report=comparison_assessment([('Module',first),('Résistance',second)])
    assert report['can_compare'] is False
    assert report['score']==0
