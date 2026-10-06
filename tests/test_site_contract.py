import pytest
from fastapi import HTTPException

import main
from materia import __version__


def test_french_number_format_uses_unambiguous_separators():
    assert main.number_fr(1502) == '1\u202f502'
    assert main.number_fr(48.5, 1) == '48,5'
    with pytest.raises(ValueError):
        main.number_fr(float('nan'))


def test_unknown_material_api_uses_http_404():
    with pytest.raises(HTTPException) as error:
        main.material_api('not-a-material')
    assert error.value.status_code == 404
    assert error.value.detail['material_id'] == 'not-a-material'


def test_material_api_is_case_insensitive():
    response = main.material_api('pp')
    assert response['material']['id'] == 'PP'
    assert 'scientific_audit' in response


def test_health_uses_the_package_version():
    assert main.health()['version'] == __version__
