import pytest

from materia import auth, store


def test_student_account_and_authentication(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'auth.sqlite3')
    user=auth.create_user('alice.dupont','Alice Dupont','mot-de-passe-solide')
    assert user['role']=='student'
    assert auth.authenticate('ALICE.DUPONT','incorrect') is None
    logged=auth.authenticate('alice.dupont','mot-de-passe-solide')
    assert logged['id']==user['id']
    with store.connect() as conn:
        row=conn.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
    assert row['password_hash']!='mot-de-passe-solide'
    assert row['last_login']


def test_teacher_account_requires_server_token(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'auth.sqlite3')
    monkeypatch.setenv('MATERIA_TEACHER_TOKEN','CODE-ECOLE-FORT')
    with pytest.raises(PermissionError):
        auth.create_user('professeur','Dr Exemple','mot-de-passe-solide','teacher','mauvais')
    teacher=auth.create_user('professeur','Dr Exemple','mot-de-passe-solide','teacher','CODE-ECOLE-FORT')
    assert teacher['role']=='teacher'


def test_account_validation_and_duplicate(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'auth.sqlite3')
    with pytest.raises(ValueError): auth.create_user('A','Alice','mot-de-passe-solide')
    auth.create_user('alice','Alice','mot-de-passe-solide')
    with pytest.raises(ValueError,match='déjà utilisé'):
        auth.create_user('alice','Autre Alice','mot-de-passe-different')


def test_private_local_bootstrap_tokens(tmp_path,monkeypatch):
    monkeypatch.setattr(auth,'DATA_DIR',tmp_path)
    monkeypatch.delenv('MATERIA_TEACHER_TOKEN',raising=False)
    token,created=auth.ensure_server_token('MATERIA_TEACHER_TOKEN','.teacher_token','ENS')
    assert created is True and token.startswith('ENS-')
    assert auth.server_token('MATERIA_TEACHER_TOKEN','.teacher_token')==token
    assert auth.ensure_server_token('MATERIA_TEACHER_TOKEN','.teacher_token','ENS')==(token,False)
    assert (tmp_path/'.teacher_token').stat().st_mode & 0o777 == 0o600
