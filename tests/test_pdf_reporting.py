from io import BytesIO

from pypdf import PdfReader

from materia import material_db
from materia.modeling import published_evidence_curve
from materia.pdf_reporting import evidence_card_pdf, result_pdf


def test_pdf_report_contains_results_validity_and_source():
    result=published_evidence_curve(material_db.evidence_rows('PP','outdoor'),'MDPI-RPP1X',120,80)
    blob=result_pdf(result,'Rapport PP')
    assert blob.startswith(b'%PDF-')
    reader=PdfReader(BytesIO(blob))
    assert len(reader.pages)>=2
    text='\n'.join(page.extract_text() or '' for page in reader.pages)
    assert 'Validité du résultat' in text
    assert '10.3390/polym16131788' in text
    assert 'Module conservé' in text
    assert 'Origine' in text and 'Observé' in text


def test_pdf_chart_uses_requested_horizon_unit():
    result=published_evidence_curve(material_db.evidence_rows('PP','outdoor'),'MDPI-RPP1X',120,80)
    result['manifest']['model']='datasheet-screening-v4'
    result['manifest']['inputs']['horizon_display']={'value':120,'unit':'days','label':'120 jours'}
    text='\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(result_pdf(result))).pages)
    assert 'Temps (jours)' in text


def test_evidence_card_is_one_page_and_keeps_primary_traceability():
    result=published_evidence_curve(material_db.evidence_rows('PP','outdoor'),'MDPI-RPP1X',120,80)
    blob=evidence_card_pdf(result,'Mesures publiées · PP recyclé')
    assert blob.startswith(b'%PDF-')
    reader=PdfReader(BytesIO(blob))
    assert len(reader.pages)==1
    text=reader.pages[0].extract_text() or ''
    assert 'Carte de preuve' in text
    assert 'Domaine couvert' in text
    assert 'Niveau de preuve et incertitude' in text
    assert 'Origine' in text and 'Observé' in text
    assert '10.3390/polym16131788' in text
    assert result['fingerprint'] in text
