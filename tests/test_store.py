import sqlite3
import pytest
from materia import store

def test_ownership_and_backup(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'test.sqlite3')
    ident=store.save('alice','simulation','Essai',{'value':42})
    assert store.get('bob',ident) is None
    assert store.records('bob')==[]
    assert store.get('alice',ident)['payload']['value']==42
    dest=tmp_path/'backup.sqlite3'; store.backup(dest)
    with sqlite3.connect(dest) as conn:
        assert conn.execute('SELECT COUNT(*) FROM records').fetchone()[0]==1
    assert store.delete('bob',ident) is False
    assert store.delete('alice',ident) is True
    assert store.get('alice',ident) is None
    monkeypatch.setattr(store,'DB',dest)
    assert store.get('alice',ident)['payload']['value']==42

def test_transfer_guest_records(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'transfer.sqlite3')
    ident=store.save('guest','simulation','Essai invité',{'value':1})
    assert store.transfer_owner('guest','account')==1
    assert store.get('guest',ident) is None
    assert store.get('account',ident)['name']=='Essai invité'

def test_custom_material_record(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'custom.sqlite3')
    ident=store.save('alice','custom_material','Mon PP',{'id':'CUSTOM-1','suggested_modulus_mpa':1250})
    rows=store.records('alice','custom_material')
    assert len(rows)==1 and rows[0]['id']==ident
    assert rows[0]['payload']['suggested_modulus_mpa']==1250

def test_clone_keeps_payload_and_owner_scope(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'clone.sqlite3')
    ident=store.save('alice','simulation','Scénario PP',{'fingerprint':'abc','retention':[100,82]})
    clone_id=store.clone('alice',ident,'Variante PP')
    clone=store.get('alice',clone_id)
    assert clone['name']=='Variante PP'
    assert clone['payload']=={'fingerprint':'abc','retention':[100,82]}
    assert store.get('bob',clone_id) is None
    with pytest.raises(ValueError):
        store.clone('bob',ident)
