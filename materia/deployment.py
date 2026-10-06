"""Deployment diagnostics and a non-destructive classroom concurrency probe."""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from pathlib import Path

import httpx

from materia import auth, store


def readiness_report() -> dict:
    db_ok=False
    try:
        with store.connect() as conn:
            db_ok=conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    except Exception:
        pass
    checks=[
        {'item':'Base locale','status':'ready' if db_ok else 'blocked','detail':'SQLite intègre en mode WAL.' if db_ok else 'Base inaccessible ou corrompue.'},
        {'item':'Secrets serveur','status':'ready' if auth.server_token('MATERIA_TEACHER_TOKEN','.teacher_token') and auth.server_token('MATERIA_REVIEW_TOKEN','.review_token') else 'blocked','detail':'Codes enseignant et revue configurés.'},
        {'item':'Comptes et rôles','status':'pilot','detail':'Comptes locaux hachés ; connexion SSO institutionnelle non configurée.'},
        {'item':'Stockage institutionnel','status':'blocked','detail':'PostgreSQL et stockage objet restent à connecter avant une exploitation multi-serveur.'},
        {'item':'HTTPS et reverse proxy','status':'ready' if os.environ.get('MATERIA_EXTERNAL_URL','').startswith('https://') else 'blocked','detail':'Configurer MATERIA_EXTERNAL_URL et un reverse proxy HTTPS.'},
    ]
    return {'pilot_ready':all(c['status']!='blocked' for c in checks[:2]),'institution_ready':all(c['status']=='ready' for c in checks),
            'storage':'sqlite-local','checks':checks}


async def concurrency_probe(base_url: str='http://127.0.0.1:8087', users: int=30) -> dict:
    """Run simultaneous read-only student journeys against health, catalogue and simulation pages."""
    if not 1<=users<=200:
        raise ValueError('Le nombre d’utilisateurs doit être compris entre 1 et 200.')
    async def journey(index: int) -> dict:
        durations=[]; errors=[]
        async with httpx.AsyncClient(base_url=base_url,timeout=20,follow_redirects=True) as client:
            for path in ('/health','/api/materials','/simuler/estimation'):
                start=time.perf_counter()
                try:
                    response=await client.get(path); response.raise_for_status()
                except Exception as exc:
                    errors.append(f'{path}: {type(exc).__name__}')
                durations.append((time.perf_counter()-start)*1000)
        return {'user':index,'durations_ms':durations,'errors':errors}
    started=time.perf_counter(); results=await asyncio.gather(*(journey(i+1) for i in range(users)))
    durations=[value for result in results for value in result['durations_ms']]
    errors=[error for result in results for error in result['errors']]
    ordered=sorted(durations); p95=ordered[min(len(ordered)-1,max(0,int(.95*len(ordered))-1))]
    return {'users':users,'requests':users*3,'errors':len(errors),'error_details':errors[:20],
            'mean_ms':statistics.fmean(durations),'p95_ms':p95,'max_ms':max(durations),
            'elapsed_s':time.perf_counter()-started,'passed':not errors}


if __name__=='__main__':
    base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8087'
    users=int(sys.argv[2]) if len(sys.argv)>2 else 30
    print(json.dumps(asyncio.run(concurrency_probe(base,users)),ensure_ascii=False,indent=2))
