"""Local SQLite store. Browser ownership enforced in all record queries."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
DB = Path(os.environ.get('MATERIA_DB',Path(__file__).parents[1]/'data'/'materia.sqlite3'))
SCHEMA_VERSION = 5
def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB,timeout=10); conn.row_factory=sqlite3.Row
    try: DB.chmod(0o600)
    except OSError: pass
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, name TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_records_owner_kind_created ON records(owner,kind,created DESC)')
    conn.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)')
    conn.execute('DELETE FROM schema_version')
    conn.execute('INSERT INTO schema_version VALUES (?)',(SCHEMA_VERSION,))
    conn.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
    conn.commit()
    return conn

def save(owner,kind,name,payload):
    if not owner or kind not in {'simulation','dataset','publication','calibration','document','evidence','custom_material'}: raise ValueError('Enregistrement invalide.')
    ident=str(uuid4())
    with connect() as c:
        c.execute('INSERT INTO records VALUES (?,?,?,?,?,?)',(ident,owner,kind,name[:200],json.dumps(payload,ensure_ascii=False,allow_nan=False),datetime.now(timezone.utc).isoformat()))
    return ident

def records(owner,kind=None):
    with connect() as c:
        query='SELECT * FROM records WHERE owner=?'; args=[owner]
        if kind: query+=' AND kind=?'; args.append(kind)
        data=c.execute(query+' ORDER BY created DESC',args).fetchall()
    return [dict(r)|{'payload':json.loads(r['payload'])} for r in data]

def get(owner,ident):
    with connect() as c: row=c.execute('SELECT * FROM records WHERE owner=? AND id=?',(owner,ident)).fetchone()
    return dict(row)|{'payload':json.loads(row['payload'])} if row else None

def delete(owner: str, ident: str) -> bool:
    if not owner or not ident:
        return False
    with connect() as conn:
        cursor=conn.execute('DELETE FROM records WHERE owner=? AND id=?',(owner,ident))
        conn.commit()
    return bool(cursor.rowcount)

def update_payload(owner: str, ident: str, payload: dict) -> bool:
    with connect() as conn:
        cursor=conn.execute('UPDATE records SET payload=? WHERE owner=? AND id=?',
                            (json.dumps(payload,ensure_ascii=False,allow_nan=False),owner,ident))
        conn.commit()
    return bool(cursor.rowcount)

def clone(owner: str, ident: str, name: str | None = None) -> str:
    """Duplicate one user-owned record while preserving the immutable payload."""
    record=get(owner,ident)
    if not record:
        raise ValueError('Enregistrement introuvable.')
    clone_name=(name or ('Copie de '+record['name'])).strip()
    return save(owner,record['kind'],clone_name,record['payload'])

def transfer_owner(source_owner: str, target_owner: str) -> int:
    """Attach records created as a guest to a newly authenticated account."""
    if not source_owner or not target_owner or source_owner == target_owner:
        return 0
    with connect() as conn:
        cursor=conn.execute('UPDATE records SET owner=? WHERE owner=?',(target_owner,source_owner))
        conn.commit()
    return int(cursor.rowcount)

def backup(destination):
    with connect() as source,sqlite3.connect(destination) as target: source.backup(target)
