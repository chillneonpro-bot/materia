"""Deterministic, synthetic teaching model; not a material life prediction."""
from __future__ import annotations
import csv
import io
import json
from hashlib import sha256
import numpy as np
from pydantic import BaseModel, Field, ConfigDict
from scipy.optimize import least_squares

VERSION = 'synthetic-arrhenius-1.0'
CATALOG = {
    'demo-a': dict(name='Polymère A', family='Thermoplastique fictif', tag='Perte de rigidité', e0=2400., k=0.0007, ea=45000., description='Un cas pédagogique de diminution progressive du module. Les paramètres sont inventés pour explorer le calcul.'),
    'demo-b': dict(name='Polymère B', family='Thermoplastique fictif', tag='Cinétique plus lente', e0=1800., k=0.00035, ea=38000., description='Un second cas synthétique pour comparer les courbes. Il ne représente aucun grade commercial.'),
    'demo-c': dict(name='Polymère C', family='Polymère fictif', tag='Rigidification', e0=1200., k=-0.00018, ea=30000., description='Un exemple de rigidification : un module croissant ne démontre pas une absence de fragilisation.'),
}
class Scenario(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra='forbid')
    material: str = 'demo-a'
    e0: float = Field(default=2400, gt=0, le=1e7)
    temperature: float = Field(default=60, ge=-20, le=180)
    horizon: float = Field(default=1200, ge=1, le=100000)
    threshold: float = Field(default=80, gt=0, le=100)
    spread: float = Field(default=20, ge=0, le=60)
    seed: int = Field(default=42, ge=0)

def simulate(s: Scenario) -> dict:
    if s.material not in CATALOG:
        raise ValueError('Matériau inconnu : aucune estimation disponible.')
    if not 20 <= s.temperature <= 100 or s.horizon > 5000:
        raise ValueError('Démonstration limitée à 20–100 °C et 5 000 jours. Aucun modèle validé hors de ce périmètre.')
    m = CATALOG[s.material]
    k = m['k'] * np.exp(-m['ea']/8.314462618 * (1/(s.temperature+273.15)-1/333.15))
    t = np.linspace(0, s.horizon, 241)
    rng = np.random.default_rng(s.seed)
    rates = k * np.exp(rng.normal(0, s.spread/100, 1000))
    paths = s.e0 * np.exp(-rates[:,None]*t)
    center = s.e0*np.exp(-k*t)
    lo, hi = np.quantile(paths,[.05,.95],axis=0)
    target = s.threshold/100
    if target == 1:
        crossings = np.zeros(len(rates)); crossing = 0.
    elif k > 0:
        crossings = -np.log(target)/rates
        crossing = float(-np.log(target)/k)
    else:
        crossings = np.full(len(rates),np.inf); crossing = None
    # Quantiles include the non-crossing population; never condition on crossing.
    qs = []
    for q in [.05,.95]:
        v = float(np.sort(crossings)[int(q*(len(crossings)-1))])
        qs.append(v if np.isfinite(v) and v <= s.horizon else None)
    manifest = dict(model=VERSION, dataset='synthetic-teaching-v1', inputs=s.model_dump(), status='SYNTHÉTIQUE — NON VALIDÉ', interval='Enveloppe de sensibilité 5–95 % ; non calibrée sur des expériences')
    digest = sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return dict(time=t.tolist(), modulus=center.tolist(), lower=lo.tolist(), upper=hi.tolist(), retention=(center/s.e0*100).tolist(), crossing=crossing if crossing is not None and crossing<=s.horizon else None, crossing_interval=qs, fraction_crossing=float(np.mean(crossings<=s.horizon)), rate=float(k), manifest=manifest, fingerprint=digest)

def result_csv(result: dict) -> bytes:
    out=io.StringIO(); w=csv.writer(out)
    manifest=result.get('manifest',{}); model=str(manifest.get('model',VERSION))
    times=result['time']
    if model.startswith('datasheet-screening-'):
        unit=manifest.get('inputs',{}).get('horizon_display',{}).get('unit','years')
        factor={'days':365.25,'months':12.,'years':1.}.get(unit,1.)
        times=[value*factor for value in times]; time_column=f'time_{unit}'
    else: time_column='time_days'
    status=manifest.get('status','SYNTHETIC_NOT_VALIDATED')
    status_code=('EXPLORATORY_PROJECTION' if model.startswith('datasheet-screening-')
                 else 'PUBLISHED_OBSERVATION' if model.startswith('piecewise-linear-published-')
                 else 'ACCEPTED_OBSERVATION' if model.startswith('piecewise-linear-observed-')
                 else 'SYNTHETIC_NOT_VALIDATED')
    w.writerow([time_column,'modulus_MPa','lower_MPa','upper_MPa','retention_percent','status_code','status','model_version','fingerprint'])
    for values in zip(times,result['modulus'],result['lower'],result['upper'],result['retention']):
        w.writerow([*values,status_code,status,model,result['fingerprint']])
    return out.getvalue().encode('utf-8-sig')

def comparison_csv(results: list[tuple[str,dict]]) -> bytes:
    """Export several curves in a long, analysis-friendly CSV table."""
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(['scenario','time','time_unit','modulus_MPa','lower_MPa','upper_MPa','retention_percent','status','model_version','fingerprint'])
    for name,result in results:
        manifest=result.get('manifest',{}); model=str(manifest.get('model',VERSION))
        if model.startswith('datasheet-screening-'):
            unit=manifest.get('inputs',{}).get('horizon_display',{}).get('unit','years')
            factor={'days':365.25,'months':12.,'years':1.}.get(unit,1.); times=[value*factor for value in result['time']]
        else: unit='days'; times=result['time']
        for values in zip(times,result['modulus'],result['lower'],result['upper'],result['retention']):
            w.writerow([name,values[0],unit,*values[1:],manifest.get('status',''),model,result.get('fingerprint','')])
    return out.getvalue().encode('utf-8-sig')

REQUIRED = ['experiment_id','time','time_unit','modulus','modulus_unit','initial_modulus','initial_modulus_unit',
            'temperature_C','humidity_RH','thickness_mm','measurement_temperature_C',
            'material','protocol','source','location']
def parse_measurements(raw: bytes) -> list[dict]:
    if len(raw)>2_000_000: raise ValueError('Fichier trop volumineux : maximum 2 Mo.')
    try:
        text=raw.decode('utf-8-sig'); reader=csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not set(REQUIRED)<=set(reader.fieldnames):
            raise ValueError('Colonnes manquantes. Utilisez le modèle CSV proposé.')
        rows=[]; seen=set()
        for i,row in enumerate(reader,2):
            if len(rows)>=10000: raise ValueError('Maximum 10 000 mesures par fichier.')
            if any(row.get(k) is None or not str(row[k]).strip() for k in REQUIRED): raise ValueError(f'Ligne {i} : un champ obligatoire est vide.')
            tf={'days':1.,'hours':1/24,'seconds':1/86400}.get(row['time_unit'])
            ef={'MPa':1.,'GPa':1000.,'Pa':1e-6}.get(row['modulus_unit'])
            e0f={'MPa':1.,'GPa':1000.,'Pa':1e-6}.get(row['initial_modulus_unit'])
            if tf is None or ef is None or e0f is None: raise ValueError(f'Ligne {i} : unité inconnue.')
            hours=float(row['time'])/({'hours':1.,'days':1/24,'seconds':3600.}.get(row['time_unit']) or float('nan'))
            t=hours/24; e=float(row['modulus'])*ef; e0=float(row['initial_modulus'])*e0f
            temp=float(row['temperature_C']); rh=float(row['humidity_RH']); thickness=float(row['thickness_mm']); mt=float(row['measurement_temperature_C'])
            if not np.all(np.isfinite([t,hours,e,e0,temp,rh,thickness,mt])) or t<0 or e<=0 or e0<=0 or not 0<=rh<=100 or thickness<=0 or temp<=-273.15 or mt<=-273.15:
                raise ValueError(f'Ligne {i} : valeur physique invalide.')
            if row['protocol']!='tensile': raise ValueError(f'Ligne {i} : seul le protocole tensile (traction) est accepté.')
            key=(row['experiment_id'],t)
            if key in seen: raise ValueError(f'Ligne {i} : temps dupliqué dans une expérience. Fournissez les répétitions avec des identifiants distincts.')
            seen.add(key)
            retention=e/e0
            if not 0 < retention <= 2: raise ValueError(f'Ligne {i} : propriété résiduelle E/E₀ hors de la plage 0–2.')
            rows.append(dict(experiment_id=row['experiment_id'],time_hours=hours,time_days=t,
                modulus_MPa=e,initial_modulus_MPa=e0,residual_property=retention,
                temperature_C=temp,humidity_RH=rh,thickness_mm=thickness,
                measurement_temperature_C=mt,material=row['material'],protocol=row['protocol'],
                source=row['source'],location=row['location'],raw=row,status='pending'))
        if not rows: raise ValueError('Le fichier ne contient aucune mesure.')
        return rows
    except (UnicodeDecodeError,TypeError,OverflowError) as exc:
        raise ValueError('CSV UTF-8 invalide.') from exc

def fit_measurements(rows: list[dict]) -> dict:
    """Single-condition log-linear baseline, group-held-out evaluation when possible."""
    for field in ['material','temperature_C','measurement_temperature_C','protocol']:
        if len({r[field] for r in rows})!=1: raise ValueError('La calibration exige un matériau, une température et un protocole uniques.')
    groups=sorted({r['experiment_id'] for r in rows})
    if len(rows)<4 or len({r['time_days'] for r in rows})<3:
        raise ValueError('Il faut au moins quatre mesures et trois temps distincts.')
    def fit(part):
        t=np.array([r['time_days'] for r in part]); y=np.log([r['modulus_MPa'] for r in part])
        scale=max(float(t.max()),1.)
        if np.ptp(t)==0: raise ValueError('Les mesures doivent couvrir plusieurs temps.')
        # Each independent experiment has equal total weight.
        weights=np.array([1/np.sqrt(sum(q['experiment_id']==r['experiment_id'] for q in part)) for r in part])
        opt=least_squares(lambda p:weights*(p[0]+p[1]*t/scale-y),[float(np.mean(y)),0.])
        if not opt.success or not np.all(np.isfinite(opt.x)) or abs(opt.x[0])>650: raise ValueError('La calibration ne converge pas ou ses paramètres ne sont pas identifiables.')
        return float(np.exp(opt.x[0])),float(-opt.x[1]/scale)
    e0,k=fit(rows); score=None; holdout=None
    if len(groups)>=2:
        holdout=groups[-1]; train=[r for r in rows if r['experiment_id']!=holdout]; test=[r for r in rows if r['experiment_id']==holdout]
        try:
            a,b=fit(train)
            score=float(np.mean([abs(a*np.exp(-b*r['time_days'])-r['modulus_MPa']) for r in test]))
        except ValueError: pass
    return dict(e0=e0,rate=k,groups=len(groups),holdout=holdout,holdout_mae_MPa=score,status='Calibration exploratoire, aucune validation de durée de vie',model='log-linear-group-weighted-v1')
