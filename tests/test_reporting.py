from materia.modeling import estimate_from_datasheet
from materia.reporting import markdown_report


def test_markdown_report_contains_reproducibility_fields():
    material={'id':'PP','name':'Polypropylène','family':'Polyoléfine','subtype':'Thermoplastique',
              'mechanisms':'Photo-oxydation','source_title':'Source test','source_url':'https://example.test'}
    result=estimate_from_datasheet(material,1200,23,50,2,2,80,'outdoor')
    text=markdown_report(result,'Étude PP').decode()
    assert '# Étude PP' in text
    assert 'Empreinte' in text
    assert 'Niveau de preuve' in text
    assert 'Usage interdit' in text
    assert '| Temps (années) |' in text
    assert 'Origine de la valeur à l’horizon : Estimé' in text
    assert '| Origine |' in text
