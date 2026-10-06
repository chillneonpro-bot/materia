"""Local document evidence. No LLM, OCR or scientific validation is implied."""
from __future__ import annotations
import base64
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import os
from pathlib import Path
from pypdf import PdfReader

MAX_BYTES = 8_000_000
MAX_PAGES = 100
MAX_TEXT = 1_000_000
DOCUMENTS_DIR = Path(os.environ.get('MATERIA_DOCUMENTS_DIR',Path(__file__).parents[1]/'data'/'documents'))

def _owner_folder(owner: str) -> Path:
    folder=DOCUMENTS_DIR/hashlib.sha256(owner.encode()).hexdigest()[:24]
    folder.mkdir(parents=True,exist_ok=True)
    try:
        DOCUMENTS_DIR.chmod(0o700); folder.chmod(0o700)
    except OSError: pass
    return folder

def _write_original(owner: str, digest: str, raw: bytes) -> str:
    path=_owner_folder(owner)/(digest+'.pdf')
    if not path.exists(): path.write_bytes(raw)
    try: path.chmod(0o600)
    except OSError: pass
    return str(path.relative_to(DOCUMENTS_DIR))

def original_pdf(owner: str, payload: dict) -> bytes | None:
    """Read a separately stored original, with compatibility for earlier embedded files."""
    relative=payload.get('original_path')
    if relative:
        root=DOCUMENTS_DIR.resolve(); path=(DOCUMENTS_DIR/relative).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError('Fichier PDF original inaccessible.')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=payload.get('sha256'):
            raise ValueError('L’empreinte du PDF original ne correspond plus à la source.')
        expected_folder=hashlib.sha256(owner.encode()).hexdigest()[:24]
        if path.parent.name!=expected_folder:
            raise ValueError('Document inaccessible dans cette session.')
        return raw
    embedded=payload.get('original_base64')
    return base64.b64decode(embedded) if embedded else None

def _extract(raw: bytes) -> dict:
    if len(raw)>MAX_BYTES or not raw.startswith(b'%PDF-'):
        raise ValueError('PDF invalide ou supérieur à 8 Mo.')
    try:
        reader=PdfReader(io.BytesIO(raw),strict=False)
        if reader.is_encrypted: raise ValueError('PDF chiffré : fournissez une version accessible.')
        if not 1<=len(reader.pages)<=MAX_PAGES: raise ValueError('Le PDF doit contenir entre 1 et 100 pages.')
        pages=[]; total=0
        for i,page in enumerate(reader.pages,1):
            contents=page.get_contents()
            if contents and len(contents.get_data())>8_000_000:
                raise ValueError('Une page est trop complexe pour cet import.')
            text=(page.extract_text() or '').strip()
            total+=len(text)
            if total>MAX_TEXT: raise ValueError('Le texte dépasse la limite de cet import.')
            pages.append({'page':i,'text':text})
        return dict(pages=pages,page_count=len(pages),empty_pages=[p['page'] for p in pages if not p['text']],characters=total,sha256=hashlib.sha256(raw).hexdigest(),status='extracted_unreviewed',method='pypdf-text-v1')
    except ValueError: raise
    except Exception as exc: raise ValueError('PDF illisible ou endommagé.') from exc

def extract_pdf(raw: bytes) -> dict:
    """Bounded separate process: parsing cannot monopolize the web event loop."""
    if len(raw)>MAX_BYTES or not raw.startswith(b'%PDF-'):
        raise ValueError('PDF invalide ou supérieur à 8 Mo.')
    with tempfile.TemporaryDirectory(prefix='materia-pdf-') as folder:
        path=Path(folder)/'input.pdf'; path.write_bytes(raw)
        try:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),str(path)],capture_output=True,text=True,timeout=30,check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Extraction trop longue : essayez un document plus court.') from exc
    if result.returncode!=0:
        raise ValueError('Le document dépasse les ressources autorisées ou est illisible.')
    try: payload=json.loads(result.stdout)
    except json.JSONDecodeError as exc: raise ValueError('Extraction interrompue.') from exc
    if 'error' in payload: raise ValueError(payload['error'])
    return payload

def import_pdf(owner: str,name: str,raw: bytes,reference: str) -> str:
    from materia import store
    if not reference.strip(): raise ValueError('Indiquez une référence ou un titre pour identifier la source.')
    if not name.lower().endswith('.pdf'): raise ValueError('Seuls les fichiers PDF sont acceptés.')
    digest=hashlib.sha256(raw).hexdigest()
    if any(r['payload'].get('sha256')==digest for r in store.records(owner,'document')):
        raise ValueError('Ce PDF est déjà présent dans votre bibliothèque.')
    payload=extract_pdf(raw)
    original_path=_write_original(owner,digest,raw)
    payload.update(reference=reference.strip()[:500],filename=Path(name).name,original_path=original_path,storage='filesystem-v1')
    try:
        return store.save(owner,'document',reference.strip(),payload)
    except Exception:
        try: (DOCUMENTS_DIR/original_path).unlink(missing_ok=True)
        except OSError: pass
        raise

def delete_document(owner: str, ident: str) -> bool:
    from materia import store
    record=store.get(owner,ident)
    if not record or record['kind']!='document': return False
    relative=record['payload'].get('original_path')
    deleted=store.delete(owner,ident)
    if deleted and relative:
        try:
            path=(DOCUMENTS_DIR/relative).resolve()
            if DOCUMENTS_DIR.resolve() in path.parents: path.unlink(missing_ok=True)
        except OSError: pass
    return deleted

def migrate_embedded_documents(owner: str) -> int:
    """Move legacy Base64 originals out of SQLite when their owner opens the library."""
    from materia import store
    migrated=0
    for record in store.records(owner,'document'):
        payload=record['payload']; embedded=payload.get('original_base64')
        if not embedded or payload.get('original_path'): continue
        try: raw=base64.b64decode(embedded,validate=True)
        except Exception: continue
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=payload.get('sha256'): continue
        updated=dict(payload); updated.pop('original_base64',None)
        updated['original_path']=_write_original(owner,digest,raw); updated['storage']='filesystem-v1-migrated'
        if store.update_payload(owner,record['id'],updated): migrated+=1
    return migrated

def pasted_document(reference: str,text: str,page: int) -> dict:
    if not reference.strip() or not text.strip(): raise ValueError('La référence et le passage sont obligatoires.')
    if not 1<=page<=100000 or len(text)>100000: raise ValueError('Page ou longueur de passage invalide.')
    return dict(reference=reference.strip()[:500],pages=[{'page':page,'text':text.strip()}],page_count=1,empty_pages=[],characters=len(text.strip()),sha256=hashlib.sha256(text.encode()).hexdigest(),status='extracted_unreviewed',method='manual-paste-v1',note='Passage et page déclarés par l’utilisateur, non vérifiés.')

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))
STOP={'les','des','une','dans','pour','avec','est','sur','que','quel','quelle','quels','quelles','the','and','of','for','comment','materiau','document'}
def search_passages(documents: list[dict],query: str) -> list[dict]:
    if not 2<=len(query.strip())<=300: raise ValueError('Saisissez entre 2 et 300 caractères.')
    words={w for w in re.findall(r'\w+',normalize(query)) if len(w)>1 and w not in STOP}
    if not words: raise ValueError('Précisez un terme scientifique, par exemple « module » ou « température ».')
    results=[]
    for doc in documents:
        payload=doc['payload']
        for page in payload['pages']:
            text=page['text']
            # Exact offsets into stored extraction; no generated text in quotes.
            for start in range(0,len(text),700):
                end=min(start+900,len(text)); passage=text[start:end]
                tokens=set(re.findall(r'\w+',normalize(passage)))
                score=len(words&tokens)
                if score:
                    results.append(dict(document_id=doc['id'],reference=payload['reference'],page=page['page'],start=start,end=end,text=passage,matches=score,method=payload['method'],sha256=payload['sha256']))
    return sorted(results,key=lambda r:(-r['matches'],r['reference'],r['page'],r['start']))[:8]

def keep_evidence(owner: str,hit: dict,note: str) -> str:
    from materia import store
    doc=store.get(owner,hit['document_id'])
    if not doc or doc['kind']!='document': raise ValueError('Document inaccessible.')
    source=next((p['text'] for p in doc['payload']['pages'] if p['page']==hit['page']),None)
    if source is None or source[hit['start']:hit['end']]!=hit['text']:
        raise ValueError('Le passage ne correspond plus à la source.')
    return store.save(owner,'evidence',f"{doc['name']} · p. {hit['page']}",dict(document_id=doc['id'],reference=doc['payload']['reference'],page=hit['page'],start=hit['start'],end=hit['end'],text=hit['text'],sha256=doc['payload']['sha256'],note=note[:4000],status='personal_note_not_scientific_validation'))

if __name__=='__main__':
    try:
        # CPU/file descriptor limits on Unix; subprocess timeout also applies.
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU,(20,20))
            resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
        except (ImportError,ValueError): pass
        print(json.dumps(_extract(Path(sys.argv[1]).read_bytes()),ensure_ascii=False))
    except Exception as exc: print(json.dumps({'error':str(exc)}))
