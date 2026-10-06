from pathlib import Path

from materia import maintenance, store


def test_backup_archive_contains_database_and_documents(tmp_path,monkeypatch):
    db=tmp_path/'materia.sqlite3'; docs=tmp_path/'documents'; docs.mkdir()
    monkeypatch.setattr(store,'DB',db)
    store.save('alice','simulation','Essai',{'value':42})
    owner_dir=docs/'owner'; owner_dir.mkdir(); (owner_dir/'source.pdf').write_bytes(b'%PDF-test')
    archive=tmp_path/'backup.zip'
    report=maintenance.create_backup_archive(archive,db,docs)
    assert report['archive_bytes']>0
    verified=maintenance.verify_backup_archive(archive)
    assert verified['valid'] is True
    assert verified['record_count']==1
    assert verified['file_count']==2


def test_daily_backup_is_verified_and_created_once_per_day(tmp_path,monkeypatch):
    db=tmp_path/'materia.sqlite3'; documents=tmp_path/'documents'; documents.mkdir()
    monkeypatch.setattr(store,'DB',db)
    monkeypatch.setattr(maintenance,'DOCUMENTS_DIR',documents)
    store.save('alice','simulation','Essai',{'value':42})
    folder=tmp_path/'daily'
    first=maintenance.create_daily_backup(folder,keep=2)
    second=maintenance.create_daily_backup(folder,keep=2)
    assert first['created'] is True
    assert second['created'] is False
    assert second['valid'] is True
    assert len(list(folder.glob('materia-*.zip')))==1
