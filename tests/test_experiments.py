from materia.experiments import measurement_template_xlsx, parse_measurement_file, quality_report


def test_excel_template_roundtrip_and_quality_report():
    blob=measurement_template_xlsx()
    assert blob.startswith(b'PK')
    rows=parse_measurement_file(blob,'campagne.xlsx')
    report=quality_report(rows)
    assert len(rows)==8
    assert report['experiments']==2
    assert report['ready_for_review'] is True
    assert all(detail['has_t0'] for detail in report['details'])


def test_quality_report_flags_incomplete_experiment():
    rows=parse_measurement_file(measurement_template_xlsx(),'campagne.xlsx')[:2]
    report=quality_report(rows)
    assert report['ready_for_review'] is False
    assert report['blocking_count']>=1


def test_quality_report_handles_legacy_rows_without_new_conditions():
    rows=[{
        'experiment_id':'LEGACY','time_days':day,'modulus_MPa':value,
        'temperature_C':40,'material':'PP','protocol':'tensile','source':'Archive',
    } for day,value in ((0,1000),(10,950),(20,900))]
    report=quality_report(rows)
    assert report['ready_for_review'] is False
    assert report['conditions']['humidity_RH']==[]
    assert any('humidité relative' in flag['message'] for flag in report['flags'])
