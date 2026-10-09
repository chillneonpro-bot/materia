import csv
from pathlib import Path
import pytest
from materia import material_db, store


def test_seeded_catalog_and_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    items = material_db.catalog()
    assert {'PE','LDPE','PET','EPOXY','PP','PA66','PLA','FLAX_EPOXY','PEEK','PVC','NBR',
            'PPA','PEKK','PFA','FEP','ECTFE','PEBA','TPV','FKM','PBAT'} <= {m['id'] for m in items}
    assert len(items) == 75
    assert all(m['category'] and m['subcategory'] for m in items)
    assert all(m['evidence_status'] in {'taxonomy_verified','experimental_pending','published_table_verified','datasheet_cross_checked'} for m in items)
    assert all(m['source_url'].startswith('https://') for m in items)
    assert all(m['accepted_observations'] == 0 for m in items)
    assert material_db.material('PET')['priority'] == 1


def test_no_material_is_prematurely_predictable(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    for item in material_db.catalog():
        decision = material_db.domain_decision(item['id'])
        assert decision['can_predict'] is False
        assert decision['status'] in {'insufficient','published'}
    assert material_db.domain_decision('UNKNOWN')['can_predict'] is False


def test_seed_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    material_db.migrate()
    material_db.migrate()
    with store.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM materials').fetchone()[0] == 75
        assert conn.execute('SELECT COUNT(*) FROM material_sources').fetchone()[0] == 53
        assert conn.execute('SELECT COUNT(*) FROM material_reference_properties').fetchone()[0] == 21
        assert conn.execute("SELECT COUNT(*) FROM material_observations WHERE source_id='scida-2013-flax-epoxy'").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM aging_evidence WHERE source_id='mdpi-pp-natural-aging-2024'").fetchone()[0] == 12
        assert conn.execute("SELECT COUNT(*) FROM aging_evidence WHERE source_id='mdpi-iir-mwf-2019'").fetchone()[0] == 21
    rows=material_db.evidence_rows('PP','outdoor')
    assert len(rows)==22
    assert all(r['evidence_status']=='source_verified_table' for r in rows)
    direct=[r for r in rows if r['source_id']=='mdpi-pp-natural-aging-2024']
    digitized=[r for r in rows if r['source_id']!='mdpi-pp-natural-aging-2024']
    assert len(direct)==12 and all(r['sample_count']==7 for r in direct)
    assert all(r['extraction_method']=='direct_table_transcription' for r in direct)
    assert all(r['source_doi']=='10.3390/polym16131788' and 'PP H301' in r['protocol'] for r in direct)
    assert len(digitized)==10 and all(r['extraction_method']=='controlled_figure_digitization' for r in digitized)
    assert {r['source_id'] for r in rows}=={'mdpi-pp-natural-aging-2024','mdpi-pp-zno-sunlight-2020','ccse-pp-riyadh-weathering-2011'}
    assert material_db.material('PP')['verified_evidence_observations']==22
    assert material_db.material('PP')['readiness']=='published_evidence'


def test_reference_properties_are_cross_checked_and_keep_conditions(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    expected={'PP','PC','ABS','PBT','PA66','POM','COC','COP','PPSU','PA11',
              'PEEK','PEI','PSU','PESU','PET','PVDF','PPA','PFA','FEP'}
    for material_id in expected:
        rows=material_db.reference_properties(material_id)
        assert rows
        assert all(row['verification_status']=='cross_checked_official' for row in rows)
        assert all(row['primary_source_id'] != row['cross_source_id'] for row in rows)
        assert all(row['primary_source_url'].startswith('https://') and row['cross_source_url'].startswith('https://') for row in rows)
        assert all(0 < row['minimum_mpa'] <= row['representative_mpa'] <= row['maximum_mpa'] for row in rows)
        assert all(row['test_standard'] and row['conditioning'] and row['process'] for row in rows)
        profile=material_db.reference_property_profile(material_id)
        assert profile and profile['verification_status']=='cross_checked_official'
    assert material_db.reference_property_profile('LDPE') is None
    assert material_db.reference_property_profile('PA66')['representative_mpa']==3050
    assert material_db.reference_property_profile('PA11')['representative_mpa']==1300
    assert material_db.reference_property_profile('PET')['representative_mpa']==3100
    assert material_db.reference_property_profile('PEEK')['representative_mpa']==4000
    assert material_db.reference_property_profile('PEI')['representative_mpa']==3200
    assert material_db.reference_property_profile('PSU')['representative_mpa']==2625
    assert material_db.reference_property_profile('PESU')['representative_mpa']==2650
    assert material_db.reference_property_profile('PVDF')['representative_mpa']==2250
    assert material_db.reference_property_profile('PPA')['representative_mpa']==10500
    assert material_db.reference_property_profile('PFA')['representative_mpa']==369
    assert material_db.reference_property_profile('FEP')['representative_mpa']==480
    assert {row['representative_mpa'] for row in material_db.reference_properties('PA66')}=={1100,3050}


def test_digitization_manifest_matches_seed_constants():
    path=Path(__file__).parents[1]/'data'/'evidence'/'pp_outdoor_digitized.csv'
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    expected={(item['source_id'],item['experiment_id'],float(day),float(value),float(item['uncertainty']))
              for item in material_db.PP_OUTDOOR_DIGITIZED_OBSERVATIONS for day,value in item['values']}
    actual={(row['source_id'],row['experiment_id'],float(row['time_days']),float(row['modulus_mpa']),float(row['extraction_uncertainty_pct'])) for row in rows}
    assert actual==expected


def test_unverified_evidence_never_reaches_model_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    material_db.migrate()
    with store.connect() as conn:
        conn.execute("""INSERT INTO aging_evidence
            (material_id,experiment_id,time_days,modulus_mpa,exposure_mode,protocol,
             source_id,source_location,evidence_status,property_name)
            VALUES ('PP','UNVERIFIED',10,999,'outdoor','test','mdpi-pp-natural-aging-2024',
                    'test','context_only','Module de Young en traction')""")
        conn.commit()
    assert all(row['experiment_id']!='UNVERIFIED' for row in material_db.evidence_rows('PP','outdoor'))
    candidates=material_db.research_candidates('PP')
    assert len(candidates)==3
    assert {c['status'] for c in candidates}=={
        'figure_digitization_required','target_property_mismatch','domain_mismatch_excluded'
    }
    iir=material_db.research_candidates('IIR')
    assert len(iir)==1
    assert iir[0]['source_doi']=='10.3390/jcs3020048'
    assert iir[0]['status']=='source_verified_domain_limited'
    iir_rows=material_db.evidence_rows('IIR','immersion')
    assert len(iir_rows)==21
    assert {r['ageing_temperature_c'] for r in iir_rows}=={80.,100.,120.}
    assert all(r['source_location'].startswith('Tableau 1') for r in iir_rows)
    assert not any(abs(r['time_days']-3/24)<1e-12 for r in iir_rows)
    value_120c_2h=next(r for r in iir_rows
                       if r['ageing_temperature_c']==120 and abs(r['time_days']-2/24)<1e-12)
    assert value_120c_2h['modulus_mpa']==pytest.approx(7.43)


def test_corpus_audit_explains_scientific_gates(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'audit.sqlite3')
    flax=material_db.corpus_audit('FLAX_EPOXY')
    assert flax['trainable'] is False
    assert flax['missing']=={'points':12,'experiments':3}
    assert flax['uncertainty']['predictive_interval_validated'] is False
    assert any('30 °C' in item for item in flax['recommendations'])
    pp=material_db.corpus_audit('PP')
    assert pp['verified_published_values']==22
    assert pp['verified_published_series']==6
    assert len(pp['candidate_sources'])==3
    excluded=next(item for item in pp['candidate_sources'] if item['id']=='PP-FILM-NATURAL-2022')
    assert excluded['status']=='domain_mismatch_excluded'


def test_curated_real_candidate_stays_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'candidate.sqlite3')
    item=material_db.material('FLAX_EPOXY')
    assert item['pending_observations']==10
    assert item['accepted_observations']==0
    batches=[b for b in material_db.review_batches() if b['material_id']=='FLAX_EPOXY']
    assert len(batches)==2
    assert all(b['extraction_method']=='figure_digitization' for b in batches)
    with store.connect() as conn:
        row=conn.execute("SELECT measurement_temperature_c,protocol FROM material_observations WHERE source_id='scida-2013-flax-epoxy' LIMIT 1").fetchone()
    assert row['measurement_temperature_c'] is None
    assert 'room temperature' in row['protocol'] and 'n=5' in row['protocol']
    assert material_db.domain_decision('FLAX_EPOXY')['can_predict'] is False


def test_imported_observations_stay_pending_and_are_deduplicated(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'materials.sqlite3')
    rows = [{
        'experiment_id': 'EXP-1', 'time_days': 0.0, 'modulus_MPa': 2000.0,
        'temperature_C': 60.0, 'measurement_temperature_C': 23.0,
        'protocol': 'tensile', 'source': 'Article exemple', 'location': 'table 2',
    }]
    first = material_db.propose_observations('LDPE', rows, 'https://doi.org/10.0000/example')
    second = material_db.propose_observations('LDPE', rows, 'https://doi.org/10.0000/example')
    assert first['inserted'] == 1
    assert second['duplicates'] == 1
    item = material_db.material('LDPE')
    assert item['pending_observations'] == 1
    assert item['readiness'] == 'data_pending_review'
    assert material_db.domain_decision('LDPE')['can_predict'] is False


def test_scientific_review_gates_and_model_readiness(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'review.sqlite3')
    rows=[]
    for experiment in ['A','B','C']:
        for hours in [0,100,200,400]:
            rows.append({'experiment_id':experiment,'time_days':hours/24,'time_hours':hours,
                'modulus_MPa':2000-hours/2,'initial_modulus_MPa':2000,
                'residual_property':(2000-hours/2)/2000,'temperature_C':60,
                'humidity_RH':75,'thickness_mm':1.5,'measurement_temperature_C':23,
                'protocol':'tensile','source':'Article test','location':f'table 1, {hours} h'})
    material_db.propose_observations('LDPE',rows,'https://doi.org/10.0000/review')
    batch=material_db.review_batches()[0]
    with pytest.raises(PermissionError):
        material_db.review_batch(batch['source_id'],'A','accepted','Dr Test','Contrôle complet.',{},authorized=False)
    with pytest.raises(ValueError):
        material_db.review_batch(batch['source_id'],'A','accepted','Dr Test','Contrôle incomplet',{},authorized=True)
    checks={k:True for k in ['source_verified','conditions_verified','units_verified','extraction_verified']}
    for experiment in ['A','B','C']:
        assert material_db.review_batch(batch['source_id'],experiment,'accepted','Dr Test','Source et extraction vérifiées.',checks,authorized=True)==4
    item=material_db.material('LDPE')
    assert item['accepted_observations']==12
    assert item['accepted_experiments']==3
    assert item['readiness']=='model_ready'
    assert len(material_db.accepted_rows('LDPE'))==12
    assert material_db.domain_decision('LDPE')['can_predict'] is False
