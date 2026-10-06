"""Verified backup archives for the local Materia deployment."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from materia import store
from materia.documents import DOCUMENTS_DIR


def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def create_backup_archive(destination: str | Path, db_path: str | Path | None = None,
                          documents_dir: str | Path | None = None) -> dict:
    destination=Path(destination); source_db=Path(db_path or store.DB); source_docs=Path(documents_dir or DOCUMENTS_DIR)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='materia-backup-') as temp:
        snapshot=Path(temp)/'materia.sqlite3'
        with sqlite3.connect(source_db) as source,sqlite3.connect(snapshot) as target: source.backup(target)
        files={'database/materia.sqlite3':snapshot}
        if source_docs.exists():
            for path in source_docs.rglob('*'):
                if path.is_file(): files['documents/'+str(path.relative_to(source_docs))]=path
        manifest={'format':'materia-backup-v1','created_at':datetime.now(timezone.utc).isoformat(),
                  'schema_version':store.SCHEMA_VERSION,'files':{name:{'sha256':_sha256(path),'bytes':path.stat().st_size} for name,path in files.items()}}
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,path in files.items(): archive.write(path,name)
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    try: destination.chmod(0o600)
    except OSError: pass
    return manifest|{'archive':str(destination),'archive_bytes':destination.stat().st_size}


def verify_backup_archive(archive_path: str | Path) -> dict:
    archive_path=Path(archive_path)
    with tempfile.TemporaryDirectory(prefix='materia-verify-') as temp:
        root=Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            names=archive.namelist()
            if 'manifest.json' not in names or 'database/materia.sqlite3' not in names:
                raise ValueError('Archive Materia incomplète.')
            if any(name.startswith('/') or '..' in Path(name).parts for name in names):
                raise ValueError('Chemin dangereux dans l’archive.')
            manifest=json.loads(archive.read('manifest.json'))
            if manifest.get('format')!='materia-backup-v1': raise ValueError('Format de sauvegarde inconnu.')
            archive.extractall(root)
        for name,expected in manifest.get('files',{}).items():
            path=root/name
            if not path.is_file() or _sha256(path)!=expected.get('sha256') or path.stat().st_size!=expected.get('bytes'):
                raise ValueError('Échec de vérification : '+name)
        with sqlite3.connect(root/'database/materia.sqlite3') as conn:
            integrity=conn.execute('PRAGMA integrity_check').fetchone()[0]
            records=conn.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        if integrity!='ok': raise ValueError('La base sauvegardée est corrompue.')
    return {'valid':True,'created_at':manifest['created_at'],'schema_version':manifest['schema_version'],
            'file_count':len(manifest['files']),'record_count':records}


def create_daily_backup(folder: str | Path | None = None, keep: int = 14) -> dict:
    """Create at most one verified backup per UTC day and keep a bounded history."""
    if not 2<=keep<=365:
        raise ValueError('La rétention doit être comprise entre 2 et 365 sauvegardes.')
    root=Path(folder or Path(__file__).parents[1]/'data'/'backups'/'daily'); root.mkdir(parents=True,exist_ok=True)
    today=datetime.now(timezone.utc).date().isoformat(); destination=root/f'materia-{today}.zip'
    if destination.exists():
        result=verify_backup_archive(destination)|{'archive':str(destination),'created':False}
    else:
        result=create_backup_archive(destination)|{'created':True}
        verify_backup_archive(destination)
    archives=sorted(root.glob('materia-*.zip'),reverse=True)
    for old in archives[keep:]: old.unlink(missing_ok=True)
    result['retained']=min(len(archives),keep); return result


def main(args: list[str] | None = None) -> int:
    args=list(sys.argv[1:] if args is None else args)
    if not args or args[0] not in {'backup','verify','daily'} or (args[0] in {'backup','verify'} and len(args)!=2):
        print('Usage: python -m materia.maintenance backup <archive.zip> | verify <archive.zip> | daily [folder]')
        return 2
    result=(create_backup_archive(args[1]) if args[0]=='backup' else
            verify_backup_archive(args[1]) if args[0]=='verify' else
            create_daily_backup(args[1] if len(args)>1 else None))
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__=='__main__': raise SystemExit(main())
