"""Local accounts for classroom pilots, designed to be replaceable by institutional SSO."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from materia import store

USERNAME_RE=re.compile(r'^[a-z0-9._-]{3,80}$')
ROLES={'student','teacher','admin'}
DATA_DIR=Path(__file__).parents[1]/'data'


def server_token(env_name: str, filename: str) -> str:
    """Read a server secret from the environment, then from a private local file."""
    configured=os.environ.get(env_name,'').strip()
    if configured:
        return configured
    path=DATA_DIR/filename
    try:
        return path.read_text().strip() if path.exists() else ''
    except OSError:
        return ''


def ensure_server_token(env_name: str, filename: str, prefix: str) -> tuple[str,bool]:
    """Create a private bootstrap token for a local pilot when none is configured."""
    existing=server_token(env_name,filename)
    if existing:
        return existing,False
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    token=prefix+'-'+secrets.token_urlsafe(12)
    path=DATA_DIR/filename
    path.write_text(token); path.chmod(0o600)
    return token,True


def migrate() -> None:
    with store.connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL, password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL,
            last_login TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_username_active ON users(username,active);
        """)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _password_hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode('utf-8'),salt=salt,n=2**14,r=8,p=1,dklen=32).hex()


def role_registration_available(role: str) -> bool:
    if role=='student': return True
    return bool(server_token('MATERIA_TEACHER_TOKEN','.teacher_token'))


def create_user(username: str, display_name: str, password: str, role: str = 'student',
                role_token: str = '') -> dict:
    migrate(); username=normalize_username(username); display_name=display_name.strip()
    if not USERNAME_RE.fullmatch(username):
        raise ValueError('Identifiant invalide : 3 à 80 caractères, lettres minuscules, chiffres, point, tiret ou soulignement.')
    if len(display_name)<2 or len(display_name)>160:
        raise ValueError('Le nom affiché doit contenir entre 2 et 160 caractères.')
    if len(password)<10 or len(password)>200:
        raise ValueError('Le mot de passe doit contenir au moins 10 caractères.')
    if role not in ROLES: raise ValueError('Rôle inconnu.')
    if role in {'teacher','admin'}:
        expected=server_token('MATERIA_TEACHER_TOKEN','.teacher_token')
        if not expected or not hmac.compare_digest(role_token.strip(),expected):
            raise PermissionError('Le code enseignant est absent ou incorrect.')
    salt=secrets.token_bytes(16); ident=str(uuid4()); now=datetime.now(timezone.utc).isoformat()
    try:
        with store.connect() as conn:
            conn.execute('INSERT INTO users VALUES (?,?,?,?,?,?,1,?,NULL)',
                         (ident,username,display_name, salt.hex(),_password_hash(password,salt),role,now))
            conn.commit()
    except Exception as exc:
        if 'UNIQUE constraint failed' in str(exc): raise ValueError('Cet identifiant est déjà utilisé.') from exc
        raise
    return get_user(ident)


def authenticate(username: str, password: str) -> dict | None:
    migrate(); username=normalize_username(username)
    with store.connect() as conn:
        row=conn.execute('SELECT * FROM users WHERE username=? AND active=1',(username,)).fetchone()
        if not row: return None
        salt=bytes.fromhex(row['password_salt']); expected=row['password_hash']
        if not hmac.compare_digest(_password_hash(password,salt),expected): return None
        now=datetime.now(timezone.utc).isoformat()
        conn.execute('UPDATE users SET last_login=? WHERE id=?',(now,row['id'])); conn.commit()
    return get_user(row['id'])


def get_user(user_id: str | None) -> dict | None:
    if not user_id: return None
    migrate()
    with store.connect() as conn:
        row=conn.execute('SELECT id,username,display_name,role,active,created,last_login FROM users WHERE id=? AND active=1',(user_id,)).fetchone()
    return dict(row) if row else None


def public_user(user: dict) -> dict:
    return {key:user.get(key) for key in ('id','username','display_name','role')}
