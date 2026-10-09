from __future__ import annotations
import csv
import io
import json
import logging
import os
import secrets
from pathlib import Path
from uuid import uuid4
import numpy as np
from fastapi import HTTPException
from nicegui import app, ui, run
from materia import __version__, store, literature, material_db, classroom, auth, experiments, deployment, maintenance
from materia.science import CATALOG, VERSION, Scenario, simulate, parse_measurements, fit_measurements, REQUIRED
from materia.excel_reporting import (MIME_XLSX, blind_validation_template_workbook,
    blind_validation_workbook, result_workbook, comparison_workbook, table_workbook)
from materia.modeling import (evaluate_baselines, observed_projection, standard_profile,
    estimate_from_datasheet, format_years_months, evidence_assessment,
    sampled_curve_rows, published_evidence_curve, curve_value_origin, refresh_result_fingerprint,
    duration_to_days, duration_to_years, duration_label)
from materia.charts import curve, comparison, base
from materia.reporting import markdown_report
from materia.pdf_reporting import evidence_card_pdf, result_pdf
from materia.validation import (pp_literature_only_benchmark, pp_temporal_holdout,
    pp_short_term_prediction, validity_diagnostic, iir_temporal_holdout,
    iir_temperature_holdout, flax_temperature_transfer_benchmark)
from materia.blind_prediction import compare_with_experiment, freeze_prediction, parse_validation_file
from materia.readiness import comparison_assessment, preparation_assessment
from materia.planning import experiment_plan, experiment_plan_workbook
import plotly.graph_objects as go

ROOT=Path(__file__).parent
ui.add_css((ROOT/'materia/style.css').read_text(),shared=True)
NAV=[('/', 'Accueil','space_dashboard'),('/materiaux','Matériaux','category'),('/simuler','Simuler','science'),('/comparer','Comparer','compare_arrows'),('/validite','Validité','verified'),('/projets','Mes projets','folder_open'),('/classe','Espace classe','groups'),('/connexion','Mon compte','account_circle'),('/comprendre','Comprendre','school'),('/documents','Mes documents','menu_book'),('/donnees','Données et modèles','database')]

ROLE_LABELS={'student':'Étudiant','teacher':'Enseignant','admin':'Administrateur'}

def session_owner() -> str:
    if 'owner' not in app.storage.user:
        app.storage.user['owner']=str(uuid4())
    return app.storage.user['owner']

def current_user() -> dict | None:
    user=auth.get_user(app.storage.user.get('user_id'))
    if not user and app.storage.user.get('user_id'):
        app.storage.user.pop('user_id',None)
        app.storage.user.pop('reviewer_authorized',None)
    return user

def reviewer_authorized() -> bool:
    user=current_user()
    return bool(user and user['role'] in {'teacher','admin'} and app.storage.user.get('reviewer_authorized'))

def reviewer_configured() -> bool:
    return bool(auth.server_token('MATERIA_REVIEW_TOKEN','.review_token'))

def owner():
    user=current_user()
    return user['id'] if user else session_owner()

def custom_materials() -> list[dict]:
    """Return the current user's materials in the same shape as catalogue entries."""
    result=[]
    for record in store.records(owner(),'custom_material'):
        payload=dict(record['payload'])
        payload.update(record_id=record['id'],custom=True,readiness='custom_input',
                       source_title='Fiche saisie par l’utilisateur',source_url='',source_doi=None,
                       accepted_observations=0,accepted_experiments=0,pending_observations=0,
                       verified_evidence_observations=0,verified_evidence_experiments=0,
                       evidence_status='user_declared')
        result.append(payload)
    return result

def available_materials() -> dict[str,dict]:
    return {m['id']:m for m in material_db.catalog()+custom_materials()}

def sign_out() -> None:
    app.storage.user.pop('user_id',None)
    app.storage.user.pop('reviewer_authorized',None)
    ui.navigate.to('/connexion')

def button(text,url,icon=None): return ui.button(text,icon=icon,on_click=lambda:ui.navigate.to(url)).props('unelevated')
def pill(text,kind=''): ui.label(text).classes('pill '+kind)
def intro(kicker,title,desc):
    ui.label(kicker).classes('eyebrow'); ui.label(title).props('role=heading aria-level=1').classes('page-title'); ui.label(desc).classes('subtitle')
def number_fr(value: float, decimals: int = 0) -> str:
    """Format a finite number for the French interface without ambiguous comma grouping."""
    numeric=float(value)
    if not np.isfinite(numeric): raise ValueError('Valeur numérique invalide.')
    return f'{numeric:,.{decimals}f}'.replace(',', '\u202f').replace('.', ',')
def warning():
    with ui.row().classes('note w-full items-center gap-2'):
        ui.icon('info_outline',size='18px'); ui.label('Démonstration pédagogique · Données synthétiques, aucune durée de vie validée.').classes('flex-1')
def validity_panel(result: dict):
    diagnostic=validity_diagnostic(result)
    with ui.expansion('Vérifier la validité de ce résultat',icon='verified_user').classes('w-full'):
        with ui.column().classes('w-full gap-3 p-3'):
            pill(diagnostic['level'],'pill-teal' if all(c['status']=='bon' for c in diagnostic['checks']) else 'pill-amber')
            ui.label(diagnostic['conclusion']).classes('body-copy')
            table_rows(diagnostic['checks'],['criterion','status','finding'])
            ui.label('Expérience recommandée : '+diagnostic['recommended_experiment']).classes('note w-full')
            ui.link('Ouvrir le centre de validité →','/validite').classes('text-sm text-primary no-underline')

def comparison_panel(report: dict):
    with ui.row().classes('w-full items-center justify-between gap-3'):
        ui.label('Compatibilité de la comparaison').classes('font-medium')
        pill(f"{report['score']}/100 · {report['label']}",'pill-teal' if report['tone']=='teal' else 'pill-amber')
    with ui.expansion('Voir les différences',icon='rule').classes('w-full'):
        table_rows(report['checks'],['criterion','status','finding'])
def shell(path,title):
    ui.colors(primary='#235abe',secondary='#13958b',accent='#235abe')
    with ui.left_drawer(value=False,top_corner=True,bottom_corner=True).props('show-if-above bordered width=236 breakpoint=1024').classes('sidebar') as drawer:
        with ui.row().classes('items-center gap-3'):
            ui.icon('blur_on',size='25px').classes('brand-symbol'); ui.label('materia').classes('brand')
        ui.label('Le temps, la matière.').classes('brand-sub')
        for href,label,icon in NAV:
            if href=='/projets': ui.label('Votre espace').classes('nav-section')
            with ui.link(target=href).classes('nav-link '+('active' if href==path else '')):
                ui.icon(icon,size='21px'); ui.label(label)
        ui.space()
        ui.label('Version bêta locale · v'+'.'.join(__version__.split('.')[:2])).classes('footer-note')
    with ui.row().classes('topbar'):
        with ui.row().classes('items-center gap-3'):
            ui.button(icon='menu',on_click=drawer.toggle).props('flat round aria-label="Ouvrir la navigation"').classes('menu-mobile')
            ui.label('Espace de recherche').classes('crumb'); ui.icon('chevron_right',size='16px',color='grey'); ui.label(title).classes('text-sm font-medium')
        with ui.row().classes('items-center gap-3'):
            user=current_user()
            if user:
                ui.label(f"{user['display_name']} · {ROLE_LABELS[user['role']].lower()}").classes('top-meta')
                initials=''.join(part[0] for part in user['display_name'].split()[:2]).upper() or 'MP'
                ui.label(initials).classes('avatar')
                ui.button(icon='logout',on_click=sign_out).props('flat round dense aria-label="Se déconnecter"')
            else:
                ui.link('Session invitée · se connecter','/connexion').classes('top-meta no-underline')
                ui.label('IN').classes('avatar')
    return ui.column().classes('page gap-0')

def table_rows(rows,fields=None):
    if not rows: ui.label('Aucune donnée pour le moment.').classes('small'); return
    fields=fields or list(rows[0])
    labels={'temperature':'Température','scenario':'Scénario','materiau':'Matériau','niveau':'Base du calcul','seuil':'Temps au seuil','franchissement':'Franchissement','usage':'Usage','origine':'Origine de la valeur','retention_finale_pct':'Module conservé (%)','seuil_80_jours':'Seuil à 80 % (jours)','jours':'Temps (jours)','module_MPa':'Module (MPa)','retention_pct':'Module conservé (%)','experiment_id':'Expérience','time_hours':'Temps (h)','time_days':'Temps (jours)','replicates':'Répétitions','modulus_MPa':'Module (MPa)','modulus_mpa':'Module mesuré (MPa)','initial_modulus_MPa':'E₀ (MPa)','residual_property':'E/E₀','temperature_C':'Exposition (°C)','humidity_RH':'Humidité relative (%)','thickness_mm':'Épaisseur (mm)','measurement_temperature_C':'Essai (°C)','material':'Matériau','source':'Source','location':'Emplacement','capacite':'Capacité','etat':'État','preuve':'Preuve / limite','priorite':'Priorité','priority':'Priorité','phase':'Phase','role':'Rôle de la mesure','information_score':'Score informatif / 100','replicates_per_lot':'Éprouvettes / lot','lots':'Lots','lot_id':'Lot','specimen_id':'Éprouvette','specimens':'Éprouvettes','mean_mpa':'Moyenne (MPa)','sd_mpa':'Écart-type (MPa)','cv_pct':'CV (%)','median_mpa':'Médiane (MPa)','minimum_mpa':'Minimum (MPa)','maximum_mpa':'Maximum (MPa)','outlier_candidates':'À vérifier','outlier_label':'Contrôle atypique','robust_z':'z robuste','outlier_reason':'Justification','included_in_validation':'Incluse dans le calcul','faille':'Faille','impact':'Impact','critere':'Critère','objectif':'Objectif','resultat':'Résultat','temps':'Temps','unite':'Unité','module_mpa':'Module central (MPa)','module_min_mpa':'Borne basse (MPa)','module_max_mpa':'Borne haute (MPa)','label':'Facteur','value':'Valeur','meaning':'Interprétation','display_name':'Étudiant','assignment_title':'Travail','simulation_name':'Résultat remis','simulation':'Simulation','horizon':'Horizon comparé','temps_au_seuil':'Temps au seuil','statut':'Statut scientifique','status':'Statut','grade':'Note / 20','submitted':'Date de remise','formulation':'Formulation','module_initial_mpa':'Module initial (MPa)','module_final_mpa':'Module final (MPa)','module_120_mpa':'Module à 120 j (MPa)','retention_120_pct':'Conservation à 120 j (%)','loss_120_pct':'Perte à 120 j (%)','observed_mpa':'Observé (MPa)','observed_sd_mpa':'Écart-type observé (MPa)','predicted_mpa':'Prédit (MPa)','lower_mpa':'Borne basse (MPa)','upper_mpa':'Borne haute (MPa)','absolute_error_mpa':'Erreur absolue (MPa)','relative_error_pct':'Erreur relative (%)','covered':'Dans la bande','within_reported_sd':'Dans ±1 écart-type','points':'Points','distinct_times':'Temps distincts','start_days':'Début (j)','end_days':'Fin (j)','has_t0':'Temps initial','max_step_change_pct':'Variation max. (%)','criterion':'Critère','finding':'Constat','method':'Modèle','model':'Modèle','mae_mpa':'MAE (MPa)','rmse_mpa':'RMSE (MPa)','mape_pct':'Erreur relative moyenne (%)','r2':'R²','r2_mean':'R² moyen','rmse_mean':'RMSE moyenne','mae_mean':'MAE moyenne','train_r2_mean':'R² apprentissage moyen','overfit_gap':'Écart de surapprentissage','importance':'Importance','max_relative_error_pct':'Erreur relative max. (%)','within_reported_sd_count':'Dans ±1 écart-type'}
    ui.table(columns=[dict(name=k,label=labels.get(k,k),field=k,align='left',sortable=True) for k in fields],rows=[{k:r.get(k) for k in fields} for r in rows],pagination=8).classes('w-full').props('flat')

def download_json(payload,name): ui.download(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False).encode(),name,'application/json')
def catalog_csv() -> bytes:
    out=io.StringIO(); fields=['id','name','abbreviation','category','subcategory','family','subtype','evidence_status','mechanisms','target_property','readiness','accepted_observations','accepted_experiments','pending_observations','verified_evidence_observations','verified_evidence_experiments','verified_reference_properties','source_title','source_url']
    writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(material_db.catalog()+custom_materials())
    return out.getvalue().encode('utf-8-sig')

def submissions_csv(rows: list[dict]) -> bytes:
    out=io.StringIO(); fields=['display_name','assignment_title','simulation_name','status','grade','feedback','submitted']
    writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    return out.getvalue().encode('utf-8-sig')

@ui.page('/')
def home():
    with shell('/','Accueil'):
        with ui.row().classes('w-full justify-between items-center gap-4 mb-6'):
            with ui.column().classes('gap-0'):
                intro('Votre laboratoire numérique','Comprendre la matière. Anticiper le temps.','Explorez le vieillissement des polymères, construisez un scénario et donnez du sens à vos résultats.')
            button('Nouvelle simulation','/simuler','add')
        with ui.element('div').classes('actions-grid w-full mb-6'):
            for icon,title,desc,url,cta in [('category','Explorer les matériaux','Découvrez les cas pédagogiques et leurs propriétés.','/materiaux','Voir les matériaux'),('science','Construire un scénario','Modifiez les conditions et observez leur influence.','/simuler','Lancer une simulation'),('auto_stories','Comprendre les courbes','Module, seuil, incertitude : les clés pour bien lire.','/comprendre','Parcourir le guide')]:
                with ui.column().classes('action-card gap-3'):
                    ui.icon(icon,size='23px').classes('icon-well'); ui.label(title).classes('font-bold text-base'); ui.label(desc).classes('small')
                    ui.link(cta+' →',url).classes('text-primary text-sm no-underline font-medium')
        with ui.element('div').classes('work-grid w-full'):
            with ui.column().classes('panel gap-0'):
                with ui.row().classes('justify-between items-center w-full'):
                    with ui.column().classes('gap-1'):
                        ui.label('Le vieillissement, en une courbe').classes('section-title'); ui.label('Polymère A · exposition constante à 60 °C').classes('small')
                    pill('Exemple synthétique','pill-amber')
                r=simulate(Scenario())
                with ui.element('div').classes('stat-grid w-full'):
                    for label,value,sub in [('Module initial','2 400 MPa','Rigidité au début du scénario'),('Seuil choisi','80 %','Du module initial'),('Franchissement',f"{r['crossing']:.0f} jours",'Calcul illustratif uniquement')]:
                        with ui.column().classes('gap-0'):
                            ui.label(label).classes('stat-label'); ui.label(value).classes('stat-value'); ui.label(sub).classes('small')
                ui.plotly(curve(r,1920)).classes('w-full')
                with ui.row().classes('w-full justify-between items-center mt-4'):
                    ui.link('Modifier ce scénario →','/simuler').classes('text-primary text-sm no-underline')
            with ui.column().classes('gap-5 w-full'):
                with ui.column().classes('panel w-full gap-4'):
                    ui.label('Votre espace de travail').classes('section-title')
                    count=len(store.records(owner(),'simulation'))
                    ui.label(str(count)).classes('stat-value'); ui.label('simulation'+('s' if count!=1 else '')+' enregistrée'+('s' if count!=1 else '')).classes('small')
                    button('Retrouver mes projets','/projets','folder_open').props('outline').classes('w-full')
                with ui.column().classes('panel w-full gap-3'):
                    ui.icon('verified_user',size='25px',color='secondary'); ui.label('Savoir ce que l’on sait').classes('section-title')
                    ui.label('Chaque projection conserve ses paramètres, sa version et ses limites. Aucun modèle de durée de vie n’est encore validé.').classes('body-copy')
                    ui.link('Voir la maturité du projet →','/donnees').classes('text-sm text-primary no-underline')

@ui.page('/materiaux')
def materials():
    with shell('/materiaux','Matériaux'):
        intro('Bibliothèque','Des matériaux à explorer','Le catalogue rassemble les polymères réels, leurs sources et le niveau de preuve disponible pour chaque propriété.')
        all_materials=material_db.catalog()
        with ui.element('div').classes('stat-grid w-full mt-5'):
            for label,value,detail in [
                ('Référentiel',str(len(all_materials)),'matériaux classés et sourcés'),
                ('Taxonomie vérifiée',str(sum(bool(m.get('taxonomy_source_id')) for m in all_materials)),'fiches reliées au référentiel NIMS/IUPAC'),
                ('Observations acceptées',str(sum(m['accepted_observations'] for m in all_materials)),'seules données autorisées pour un entraînement réel'),
                ('Preuves publiées',str(sum(m['verified_evidence_observations'] for m in all_materials)),'valeurs de tableaux relues et traçables'),
                ('Profils recoupés',str(sum(m['verified_reference_properties'] for m in all_materials)),'profils fabricant contrôlés par une seconde source officielle'),
            ]:
                with ui.column().classes('panel gap-1'):
                    ui.label(label).classes('stat-label'); ui.label(value).classes('stat-value'); ui.label(detail).classes('small')
        with ui.expansion('Ajouter un matériau personnalisé',icon='add_circle').classes('w-full mt-5'):
            with ui.column().classes('p-4 gap-4 w-full'):
                ui.label('Créer une fiche utilisable dans les estimations et comparaisons').classes('section-title')
                ui.label('Cette fiche reste déclarée par l’utilisateur. Elle n’est pas ajoutée au corpus scientifique tant qu’aucune campagne de mesures n’a été revue.').classes('note w-full')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    custom_name=ui.input('Nom du matériau',placeholder='PP recyclé — grade interne').props('outlined').classes('grow min-w-64')
                    custom_abbr=ui.input('Abréviation',placeholder='R-PP').props('outlined').classes('min-w-48')
                    custom_family=ui.input('Famille',placeholder='Polyoléfine').props('outlined').classes('grow min-w-56')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    custom_e0=ui.number('Module initial de la fiche (MPa)',min=.01,value=1000).props('outlined').classes('grow min-w-56')
                    custom_mechanisms=ui.input('Mécanismes attendus',placeholder='Photo-oxydation; thermo-oxydation').props('outlined').classes('grow min-w-72')
                custom_reference=ui.input('Référence de la fiche ou du grade',placeholder='Fabricant, grade, lot, URL ou document interne').props('outlined').classes('w-full')
                def save_custom_material():
                    name=(custom_name.value or '').strip(); abbreviation=(custom_abbr.value or '').strip().upper()
                    family_name=(custom_family.value or '').strip(); mechanisms=(custom_mechanisms.value or '').strip()
                    try: modulus=float(custom_e0.value)
                    except (TypeError,ValueError): modulus=0
                    if len(name)<2 or len(abbreviation)<1 or len(family_name)<2 or modulus<=0:
                        ui.notify('Renseignez un nom, une abréviation, une famille et un module positif.',type='negative'); return
                    ident='CUSTOM-'+uuid4().hex[:10].upper()
                    store.save(owner(),'custom_material',name,{
                        'id':ident,'name':name[:120],'abbreviation':abbreviation[:20],
                        'category':'Matériau personnalisé','subcategory':family_name[:100],
                        'family':family_name[:100],'subtype':'Grade ou formulation utilisateur',
                        'priority':3,'mechanisms':mechanisms[:300] or 'Non renseigné',
                        'target_property':'Module de Young en traction',
                        'note':(custom_reference.value or 'Fiche saisie manuellement, référence non renseignée.')[:500],
                        'suggested_modulus_mpa':modulus,
                    })
                    ui.notify('Matériau personnalisé ajouté.',type='positive'); ui.navigate.to('/materiaux')
                ui.button('Ajouter à mes matériaux',icon='add',on_click=save_custom_material).props('unelevated')
        mine=custom_materials()
        if mine:
            with ui.column().classes('panel w-full mt-5 gap-3'):
                ui.label('Mes matériaux personnalisés').classes('section-title')
                for custom in mine:
                    with ui.row().classes('row-line w-full items-center justify-between gap-3'):
                        with ui.column().classes('gap-1'):
                            ui.label(f"{custom['name']} ({custom['abbreviation']})").classes('font-medium')
                            ui.label(f"{custom['family']} · E₀ = {custom['suggested_modulus_mpa']:g} MPa · données utilisateur non validées").classes('small')
                        with ui.row().classes('gap-2'):
                            button('Utiliser',f"/simuler/estimation?material={custom['id']}",'science').props('outline')
                            def ask_remove_custom(custom=custom):
                                with ui.dialog() as dialog, ui.card().classes('gap-4'):
                                    ui.label('Supprimer ce matériau personnalisé ?').classes('section-title')
                                    ui.label(custom['name']).classes('body-copy')
                                    ui.label('Les simulations déjà enregistrées restent conservées.').classes('small')
                                    with ui.row().classes('justify-end w-full'):
                                        ui.button('Annuler',on_click=dialog.close).props('flat')
                                        def remove():
                                            store.delete(owner(),custom['record_id']); dialog.close(); ui.navigate.to('/materiaux')
                                        ui.button('Supprimer',icon='delete',on_click=remove).props('unelevated color=negative')
                                dialog.open()
                            ui.button('Supprimer',icon='delete_outline',on_click=ask_remove_custom).props('flat color=negative')
        with ui.row().classes('w-full items-center gap-3 my-5 flex-wrap'):
            search=ui.input('Rechercher un matériau',placeholder='PE, polyester, hydrolyse…').props('outlined clearable').classes('flex-1')
            category=ui.select(['Toutes les classes']+sorted({m['category'] for m in all_materials}),value='Toutes les classes',label='Grande classe').props('outlined').classes('min-w-64')
            family=ui.select(['Toutes les sous-catégories']+sorted({m['subcategory'] for m in all_materials}),value='Toutes les sous-catégories',label='Sous-catégorie').props('outlined').classes('min-w-64')
            mechanisms=sorted({part.strip() for m in all_materials for part in m['mechanisms'].split(';') if part.strip()})
            mechanism=ui.select(['Tous les mécanismes']+mechanisms,value='Tous les mécanismes',label='Mécanisme').props('outlined use-input').classes('min-w-64')
            maturity=ui.select({'all':'Tous les états','datasheet':'Modules initiaux recoupés','published':'Mesures publiées','accepted':'Observations acceptées','pending':'En attente de revue','documentary':'Fiches documentaires','ready':'Seuil logiciel atteint'},value='all',label='Données disponibles').props('outlined').classes('min-w-64')
            sort_by=ui.select({'name':'Nom A–Z','family':'Famille','maturity':'Maturité','data':'Quantité de données'},value='name',label='Trier par').props('outlined').classes('min-w-48')
            def reset_filters():
                search.value=''; category.value='Toutes les classes'; family.value='Toutes les sous-catégories'
                mechanism.value='Tous les mécanismes'; maturity.value='all'; sort_by.value='name'; refresh_filters()
            ui.button('Réinitialiser',icon='filter_alt_off',on_click=reset_filters).props('outline')
            ui.button('Exporter le catalogue Excel',icon='download',on_click=lambda:ui.download(
                table_workbook(material_db.catalog()+custom_materials(),'Catalogue des matériaux','Matériaux'),
                'catalogue-materia.xlsx',MIME_XLSX)).props('outline')
        page_state={'page':1}; page_size=12
        @ui.refreshable
        def cards():
            ui.label('Catalogue documentaire réel').classes('section-title mb-1')
            filtered=[]
            for m in material_db.catalog():
                searchable=' '.join(str(m.get(k,'')) for k in ('name','abbreviation','category','subcategory','family','subtype','mechanisms','target_property','readiness','note'))
                if (search.value or '').lower() not in searchable.lower(): continue
                if category.value!='Toutes les classes' and m['category']!=category.value: continue
                if family.value!='Toutes les sous-catégories' and m['subcategory']!=family.value: continue
                if mechanism.value!='Tous les mécanismes' and mechanism.value not in [part.strip() for part in m['mechanisms'].split(';')]: continue
                if maturity.value=='datasheet' and not m['verified_reference_properties']: continue
                if maturity.value=='published' and not m['verified_evidence_observations']: continue
                if maturity.value=='accepted' and not m['accepted_observations']: continue
                if maturity.value=='pending' and not m['pending_observations']: continue
                if maturity.value=='documentary' and (m['pending_observations'] or m['accepted_observations'] or m['verified_evidence_observations'] or m['verified_reference_properties']): continue
                if maturity.value=='ready' and m['readiness'] not in {'model_ready','validated'}: continue
                filtered.append(m)
            if sort_by.value=='name': filtered.sort(key=lambda m:m['name'].casefold())
            elif sort_by.value=='family': filtered.sort(key=lambda m:(m['family'].casefold(),m['name'].casefold()))
            elif sort_by.value=='maturity': filtered.sort(key=lambda m:(m['readiness'],m['name'].casefold()))
            else: filtered.sort(key=lambda m:-(m['accepted_observations']+m['pending_observations']+m['verified_evidence_observations']+m['verified_reference_properties']))
            total=len(filtered); pages=max(1,(total+page_size-1)//page_size); page_state['page']=min(page_state['page'],pages)
            start=(page_state['page']-1)*page_size; visible=filtered[start:start+page_size]
            ui.label(f"{total} matériau(x) trouvé(s) sur {len(material_db.catalog())} · page {page_state['page']} sur {pages}. Les fiches sans données restent documentaires.").classes('small mb-4')
            with ui.element('div').classes('actions-grid w-full'):
                for m in visible:
                    label,detail=material_db.READINESS[m['readiness']]
                    with ui.column().classes('panel gap-4'):
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.icon('science',size='32px',color='primary'); pill(label,'pill-teal' if m['readiness'] in {'verified_datasheet','accepted_limited','published_evidence','model_ready','validated'} else 'pill-amber')
                        ui.label(f"{m['name']} ({m['abbreviation']})").classes('section-title')
                        ui.label(m['category']+' › '+m['subcategory']+' · '+m['subtype']).classes('small')
                        evidence_labels={'taxonomy_verified':'Référentiel vérifié','experimental_pending':'Données expérimentales en revue',
                            'experimental_accepted_limited':'Données expérimentales acceptées','published_table_verified':'Tableau publié vérifié',
                            'datasheet_cross_checked':'Fiche fabricant recoupée'}
                        ui.label(evidence_labels.get(m['evidence_status'],m['evidence_status'])).classes('pill pill-teal' if m['evidence_status'] in {'taxonomy_verified','datasheet_cross_checked','experimental_accepted_limited','published_table_verified'} else 'pill pill-amber')
                        ui.label('Mécanismes suivis : '+m['mechanisms']).classes('body-copy')
                        ui.label(detail).classes('small')
                        references=material_db.reference_properties(m['id'])
                        if references:
                            default=next((row for row in references if row['screening_default']),references[0])
                            interval=(f"{default['representative_mpa']:,.0f} MPa" if default['minimum_mpa']==default['maximum_mpa']
                                      else f"{default['representative_mpa']:,.0f} MPa (plage {default['minimum_mpa']:,.0f}–{default['maximum_mpa']:,.0f})")
                            ui.label(('E₀ recoupé : '+interval).replace(',', '\u202f')).classes('font-medium text-primary')
                        decision=material_db.domain_decision(m['id'])
                        ui.label(decision['label']+' — '+decision['reason']).classes('note w-full')
                        with ui.expansion('Source et critères scientifiques',icon='verified').classes('w-full'):
                            ui.label(m['note']).classes('body-copy p-3')
                            ui.label(m['source_scope']).classes('small px-3')
                            ui.link(m['source_title'],m['source_url'],new_tab=True).classes('text-sm p-3')
                            ui.label(f"Observations hygrothermiques acceptées : {m['accepted_observations']} sur {m['accepted_experiments']} expérience(s) · en attente : {m['pending_observations']}").classes('small px-3')
                            ui.label(f"Valeurs publiées vérifiées : {m['verified_evidence_observations']} sur {m['verified_evidence_experiments']} série(s)").classes('small px-3 pb-3')
                        if references:
                            with ui.expansion(f"Modules initiaux recoupés ({len(references)})",icon='fact_check').classes('w-full'):
                                for reference in references:
                                    with ui.column().classes('p-3 gap-1 w-full'):
                                        suffix=' · valeur proposée' if reference['screening_default'] else ''
                                        ui.label(f"{reference['grade']} · {reference['representative_mpa']:g} MPa{suffix}").classes('font-medium')
                                        ui.label(f"{reference['test_standard']} · {reference['conditioning']} · {reference['process']}").classes('small')
                                        ui.label(reference['cross_check_note']).classes('small')
                                        with ui.row().classes('gap-3 flex-wrap'):
                                            ui.link('Source principale',reference['primary_source_url'],new_tab=True).classes('text-sm')
                                            ui.link('Source de recoupement',reference['cross_source_url'],new_tab=True).classes('text-sm')
                        button('Préparer une projection exploratoire',f"/simuler/estimation?material={m['id']}",'arrow_forward').props('outline').classes('w-full')
                        if m['id']=='PP':
                            button('Voir les mesures publiées','/simuler/mesures','verified').classes('w-full')
            if pages>1:
                def change_page(delta):
                    page_state['page']=max(1,min(pages,page_state['page']+delta)); cards.refresh()
                with ui.row().classes('w-full justify-center items-center gap-3 mt-5'):
                    ui.button('Précédent',icon='chevron_left',on_click=lambda:change_page(-1)).props('outline').set_enabled(page_state['page']>1)
                    ui.label(f"Page {page_state['page']} / {pages}").classes('small')
                    ui.button('Suivant',icon='chevron_right',on_click=lambda:change_page(1)).props('outline').set_enabled(page_state['page']<pages)
        def refresh_filters(): page_state['page']=1; cards.refresh()
        search.on_value_change(lambda:refresh_filters()); category.on_value_change(lambda:refresh_filters()); family.on_value_change(lambda:refresh_filters()); mechanism.on_value_change(lambda:refresh_filters()); maturity.on_value_change(lambda:refresh_filters()); sort_by.on_value_change(lambda:refresh_filters()); cards()

def simulation_switcher(active: str):
    items=[('Choisir un parcours','/simuler','apps'),('Fiche matériau','/simuler/estimation','description'),
           ('Mesures publiées','/simuler/mesures','verified')]
    with ui.row().classes('w-full gap-2 flex-wrap my-5').props('role=navigation aria-label="Parcours de simulation"'):
        for label,url,icon in items:
            props='unelevated' if url==active else 'outline'
            ui.button(label,icon=icon,on_click=lambda url=url:ui.navigate.to(url)).props(props)

@ui.page('/simuler')
def simulator_hub(material: str | None=None):
    if material in CATALOG:
        ui.navigate.to('/simuler')
        return
    with shell('/simuler','Simuler'):
        intro('Laboratoire numérique','Que souhaitez-vous faire ?',
              'Choisissez le parcours correspondant à vos données. Materia indique ensuite ce qui est mesuré, estimé ou uniquement illustré.')
        simulation_switcher('/simuler')
        with ui.element('div').classes('path-grid w-full'):
            paths=[
                ('description','J’ai une fiche matériau','Construire une estimation exploratoire à partir du module initial et des conditions de service.','Exploration · hypothèses explicites','/simuler/estimation','Commencer'),
                ('verified','Je veux voir des mesures publiées','Tracer directement les valeurs d’un article avec leur dispersion, sans extrapoler au-delà des essais.','Données réelles · traçables','/simuler/mesures','Explorer les mesures'),
            ]
            for icon,title,desc,status,url,cta in paths:
                with ui.column().classes('path-card gap-4'):
                    ui.icon(icon,size='30px').classes('icon-well')
                    ui.label(title).classes('path-title')
                    ui.label(desc).classes('body-copy')
                    ui.label(status).classes('pill pill-teal' if 'réelles' in status else 'pill pill-amber')
                    ui.space(); button(cta,url,'arrow_forward').classes('w-full')
        ui.label('Le niveau de preuve et les sources sont affichés avec chaque résultat.').classes('small mt-5')

@ui.page('/simuler/estimation')
def datasheet_simulator(material: str | None=None):
    own=owner(); materials=available_materials()
    selected=material if material in materials else 'PP'; initial=standard_profile(materials[selected])
    with shell('/simuler','Fiche matériau'):
        intro('Parcours 1 · exploration','Estimer depuis une fiche matériau',
              'Renseignez l’état initial et l’environnement. Le résultat reste une projection de présélection, accompagnée de ses preuves et limites.')
        simulation_switcher('/simuler/estimation')
        with ui.element('div').classes('work-grid simulation-work-grid w-full'):
            with ui.column().classes('panel gap-5 simulation-controls'):
                ui.label('1. Matériau et état initial').classes('section-title')
                options={m['id']:f"{m['name']} ({m['abbreviation']}) · {m['family']}"+(' · personnalisé' if m.get('custom') else '') for m in materials.values()}
                material_select=ui.select(options,value=selected,label='Matériau').props('outlined use-input').classes('w-full')
                e0=ui.number('Module de Young initial E₀ (MPa)',value=initial['suggested_modulus_mpa'],min=.01).props('outlined').classes('w-full')
                basis=ui.label(initial['basis']).classes('field-help')
                with ui.expansion('Préciser le grade et le procédé',icon='inventory_2').classes('w-full'):
                    grade_reference=ui.input('Grade / référence commerciale',placeholder='Ex. PP H301').props('outlined').classes('w-full p-3')
                    process_state=ui.input('Procédé / état de conditionnement',placeholder='Ex. injection, conditionné à 23 °C').props('outlined').classes('w-full px-3 pb-3')
                ui.separator(); ui.label('2. Conditions de service').classes('section-title')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    temperature=ui.number('Température (°C)',value=23,min=-40,max=160).props('outlined').classes('grow min-w-48')
                    humidity=ui.number('Humidité relative (%)',value=50,min=0,max=100).props('outlined').classes('grow min-w-48')
                    thickness=ui.number('Épaisseur (mm)',value=2,min=.01).props('outlined').classes('grow min-w-48')
                exposure=ui.select({'indoor':'Intérieur / abrité','outdoor':'Extérieur / UV','immersion':'Immersion / contact permanent'},value='outdoor',label='Milieu').props('outlined').classes('w-full')
                immersion_medium=ui.select({'unspecified':'Non précisé / autre liquide','water':'Eau','milform64':'Milform 64 SST'},
                    value='unspecified',label='Liquide, si immersion').props('outlined').classes('w-full')
                ui.label('En immersion, l’humidité relative de l’air est ignorée. Les données IIR publiées ne sont activées que pour Milform 64 SST entre 80 et 120 °C.').classes('field-help')
                ui.separator(); ui.label('3. Objectif de lecture').classes('section-title')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    horizon=ui.number('Horizon affiché',value=120 if selected=='PP' else 2,min=.01).props('outlined').classes('grow min-w-48')
                    horizon_unit=ui.select({'days':'Jours','months':'Mois','years':'Années'},value='days' if selected=='PP' else 'years',label='Unité').props('outlined').classes('min-w-48')
                    threshold=ui.number('Seuil conservé (%)',value=80,min=1,max=100).props('outlined').classes('grow min-w-48')
                ui.label('Conversion utilisée : 1 année = 365,25 jours et 1 mois moyen = 30,4375 jours.').classes('field-help')
                def selected_evidence():
                    mat=materials[material_select.value]
                    if mat.get('custom'):
                        return []
                    rows=material_db.evidence_rows(mat['id'],exposure.value)
                    if exposure.value=='immersion' and immersion_medium.value!='milform64':
                        return []
                    if mat['id']=='IIR' and not 80<=float(temperature.value or 0)<=120:
                        return []
                    return rows
                @ui.refreshable
                def preparation_panel():
                    try:
                        mat=materials[material_select.value]; profile=standard_profile(mat)
                        report=preparation_assessment(mat,float(e0.value),profile['suggested_modulus_mpa'],
                            grade_reference.value or '',process_state.value or '',
                            duration_to_days(float(horizon.value),horizon_unit.value),exposure.value,
                            selected_evidence(),immersion_medium.value)
                        with ui.row().classes('w-full items-center justify-between gap-3'):
                            ui.label('Préparation du calcul').classes('font-medium')
                            pill(f"{report['score']}/100 · {report['label']}",'pill-teal' if report['tone']=='teal' else 'pill-amber')
                        with ui.expansion('Vérifier les entrées',icon='checklist').classes('w-full'):
                            table_rows(report['checks'],['criterion','status','finding'])
                    except (ValueError,TypeError):
                        ui.label('Complétez les valeurs numériques pour évaluer la préparation.').classes('note w-full')
                preparation_panel()
                calculate_slot=ui.row().classes('w-full')
                output=ui.column().classes('w-full')
                def change_material():
                    profile=standard_profile(materials[material_select.value])
                    e0.value=profile['suggested_modulus_mpa']; basis.text=profile['basis']
                    grade_reference.value=''; process_state.value=''
                    if material_select.value=='PP': horizon.value=120; horizon_unit.value='days'
                    else: horizon.value=2; horizon_unit.value='years'
                    preparation_panel.refresh()
                material_select.on_value_change(lambda:change_material())
                for control in (e0,grade_reference,process_state,temperature,humidity,thickness,exposure,immersion_medium,horizon,horizon_unit):
                    control.on_value_change(lambda:preparation_panel.refresh())
                def calculate():
                    output.clear()
                    try:
                        mat=materials[material_select.value]
                        horizon_days=duration_to_days(float(horizon.value),horizon_unit.value)
                        horizon_years=horizon_days/365.25
                        if horizon_days<1 or horizon_years>100: raise ValueError('L’horizon doit être compris entre un jour et 100 ans.')
                        evidence=selected_evidence()
                        result=estimate_from_datasheet(mat,float(e0.value),float(temperature.value),float(humidity.value),
                            float(thickness.value),horizon_years,float(threshold.value),exposure.value,evidence,
                            immersion_medium.value)
                        result['manifest']['inputs']['horizon_display']={'value':float(horizon.value),'unit':horizon_unit.value,
                            'label':duration_label(float(horizon.value),horizon_unit.value)}
                        result['manifest']['inputs']['grade_reference']=(grade_reference.value or '').strip() or None
                        result['manifest']['inputs']['process_state']=(process_state.value or '').strip() or None
                        result['manifest']['input_readiness']=preparation_assessment(mat,float(e0.value),
                            standard_profile(mat)['suggested_modulus_mpa'],grade_reference.value or '',process_state.value or '',
                            horizon_days,exposure.value,evidence,immersion_medium.value)
                        refresh_result_fingerprint(result)
                        assessment=evidence_assessment(result); crossing=result['crossing_estimate_years']; lo,hi=result['crossing_interval']
                        assumptions=result['manifest']['assumptions']; informed=bool(assumptions['evidence_calibrated'])
                        with output:
                            ui.separator()
                            with ui.row().classes('w-full items-center justify-between gap-3'):
                                ui.label('Résultat de la projection').classes('section-title')
                                with ui.row().classes('gap-2 flex-wrap'):
                                    origin=curve_value_origin(result)
                                    pill('À l’horizon : '+origin,'pill-teal' if origin in {'Observé','Interpolé'} else 'pill-amber')
                                    pill(assessment['level']+' · '+assessment['label'],'pill-teal' if assessment['tone']=='teal' else 'pill-amber')
                            interval_validated=bool(result['manifest']['uncertainty'].get('predictive_interval_validated'))
                            match=assumptions.get('documentary_match') or {'score':0,'label':'Non renseigné'}
                            uncertainty_kind=result['manifest']['uncertainty']['kind']
                            threshold_extrapolated=bool(informed and crossing is not None and assumptions['evidence_window_days'] and crossing*365.25>assumptions['evidence_window_days'])
                            dispersion_detail=('Calibrage hors publication · couverture pilote'
                                if uncertainty_kind=='source_level_predictive_interval' else
                                'Écart-type publié ; pas encore un intervalle prédictif'
                                if uncertainty_kind=='reported_standard_deviation' else
                                'Quartiles des formulations ; pas encore un intervalle prédictif')
                            horizon_text=result['manifest']['inputs']['horizon_display']['label']
                            if informed:
                                threshold_inside=bool(crossing is not None and crossing*365.25<=assumptions['evidence_window_days'])
                                if threshold_inside:
                                    threshold_card=('Temps au seuil dans la fenêtre publiée',format_years_months(crossing),
                                                    f"Fenêtre observée : 0–{assumptions['evidence_window_days']:.0f} jours")
                                elif crossing is not None:
                                    threshold_card=('Estimation centrale du temps au seuil',format_years_months(crossing),
                                                    f"Après {assumptions['evidence_window_days']:.0f} jours · sensibilité {format_years_months(lo)}–{format_years_months(hi)}")
                                else:
                                    threshold_card=('Estimation du temps au seuil','Non calculable',
                                                    f"Fenêtre observée : 0–{assumptions['evidence_window_days']:.0f} jours")
                                band_detail=('P10–P90 pilote dans la fenêtre publiée'
                                             if uncertainty_kind=='source_level_predictive_interval' else
                                             'Sensibilité d’extrapolation ×0,65–×1,50'
                                             if uncertainty_kind=='extrapolation_sensitivity' else
                                             result['manifest']['uncertainty']['label'])
                                result_cards=[
                                    (f'Prévision P50 à {horizon_text}',f"{number_fr(result['modulus'][-1])} MPa",f"{number_fr(result['retention'][-1],1)} % du module initial"),
                                    ('Bornes à ce même horizon',f"{number_fr(result['lower'][-1])} – {number_fr(result['upper'][-1])} MPa",
                                     band_detail),
                                    threshold_card,
                                ]
                            else:
                                result_cards=[
                                    ('Estimation centrale du temps au seuil',format_years_months(crossing),'Valeur de travail recommandée'),
                                    ('Plage de sensibilité',f"{format_years_months(lo)} – {format_years_months(hi)}",'Transfert de vitesse ×1,50 à ×0,65'),
                                    (f'Module estimé à {horizon_text}',f"{number_fr(result['modulus'][-1])} MPa",f"{number_fr(result['retention'][-1],1)} % du module initial"),
                                ]
                            with ui.element('div').classes('result-grid w-full'):
                                for label,value,detail in result_cards:
                                    with ui.column().classes('result-stat gap-1'):
                                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                            band_mode=None
                            if result.get('outer_lower'):
                                band_mode=ui.select({
                                    'central':'Bande centrale recommandée',
                                    'outer':'Enveloppe complète min–max observée',
                                },value='central',label='Bande affichée').props('outlined').classes('w-full')
                                ui.label("L’enveloppe min–max montre les extrêmes du corpus et s’arrête à la fin des observations. Elle n’est pas extrapolée.").classes('field-help')
                            @ui.refreshable
                            def result_chart():
                                selected_band=band_mode.value if band_mode else 'central'
                                with ui.element('div').props('role=img aria-label="Courbe du module de Young en fonction du temps, avec bande d’incertitude et seuil choisi"').classes('w-full'):
                                    ui.plotly(curve(result,float(e0.value)*float(threshold.value)/100,selected_band)).classes('w-full')
                            if band_mode:
                                band_mode.on_value_change(lambda:result_chart.refresh())
                            result_chart()
                            if informed:
                                guidance=("Utilisez la courbe centrale. La bande ±3,41 % est calibrée en interne sur huit prédictions PP H301 masquées."
                                    if uncertainty_kind=='internal_holdout_interval' else
                                    "Utilisez la courbe centrale. Après 120 jours, les bornes prolongent les vitesses extrêmes réellement observées."
                                    if uncertainty_kind=='observed_rate_envelope_extrapolation' else
                                    "Utilisez la courbe P50. Pour un scénario prudent, utilisez P10 ; sa couverture reste pilote."
                                    if interval_validated else
                                    "Utilisez la courbe P50. Les bornes montrent la sensibilité de l’extrapolation."
                                    if uncertainty_kind=='extrapolation_sensitivity' else
                                    "Utilisez la courbe centrale. La borne basse reste indicative.")
                                ui.label(f"Valeur à retenir : {guidance} Sources compatibles : {match['score']}/100.").classes('note w-full')
                            else:
                                ui.label(f"Valeur à retenir : {format_years_months(crossing)} pour atteindre {threshold.value:g} %. La plage {format_years_months(lo)}–{format_years_months(hi)} reste indicative.").classes('note w-full')
                            with ui.expansion('Afficher les valeurs de la courbe',icon='table_chart').classes('w-full'):
                                table_rows(sampled_curve_rows(result),['temps','unite','module_mpa','module_min_mpa','module_max_mpa','retention_pct','origine'])
                            if assumptions['evidence_calibrated'] and assumptions['extrapolation_multiple']>1:
                                ui.label(f"Après {assumptions['evidence_window_days']:.0f} jours, la zone orangée signale une extrapolation.").classes('note w-full')
                            elif not assumptions['evidence_calibrated']:
                                with ui.expansion('Comprendre la plage de sensibilité',icon='tune').classes('w-full'):
                                    ui.label('La ligne centrale reste le résultat recommandé. Les deux autres valeurs montrent l’effet d’une vitesse de vieillissement 50 % plus forte ou 35 % plus faible. Elles ne sont pas des probabilités.').classes('field-help')
                                    table_rows([
                                        {'scenario':'Vieillissement plus rapide · vitesse ×1,50','franchissement':format_years_months(lo),'usage':'Borne indicative basse'},
                                        {'scenario':'Estimation centrale · vitesse ×1','franchissement':format_years_months(crossing),'usage':'Valeur à utiliser'},
                                        {'scenario':'Vieillissement plus lent · vitesse ×0,65','franchissement':format_years_months(hi),'usage':'Borne indicative haute'},
                                    ],['scenario','franchissement','usage'])
                            with ui.expansion('Planifier une campagne de validation',icon='event_note').classes('w-full'):
                                ui.label('Materia propose les temps qui couvrent le départ, la fenêtre documentaire, le seuil central et l’horizon final.').classes('body-copy p-3 pb-0')
                                with ui.row().classes('w-full gap-3 flex-wrap px-3'):
                                    planned_times=ui.number('Temps distincts',value=5,min=5,max=10,step=1).props('outlined').classes('grow min-w-40')
                                    planned_replicates=ui.number('Éprouvettes par lot et par temps',value=5,min=3,max=20,step=1).props('outlined').classes('grow min-w-52')
                                    planned_lots=ui.number('Lots indépendants',value=3,min=1,max=8,step=1).props('outlined').classes('grow min-w-40')
                                plan_output=ui.column().classes('w-full gap-3 p-3')
                                plan_state={'value':None}
                                def update_experiment_plan():
                                    plan_output.clear()
                                    try:
                                        plan=experiment_plan(result,int(planned_times.value),int(planned_replicates.value),int(planned_lots.value))
                                        plan_state['value']=plan
                                        with plan_output:
                                            with ui.element('div').classes('result-grid w-full'):
                                                for label,value,detail in [
                                                    ('Temps de mesure',str(plan['timepoints']),f"0 à {number_fr(plan['horizon_days'],1)} jours"),
                                                    ('Éprouvettes totales',str(plan['total_specimens']),f"{plan['lots']} lots × {plan['replicates_per_lot']} répétitions"),
                                                    ('Lot réservé','Oui' if plan['reserved_validation_lots'] else 'Non','Ouvert seulement après gel de la prédiction'),
                                                ]:
                                                    with ui.column().classes('result-stat gap-1'):
                                                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                                            table_rows(plan['rows'],['phase','time_days','priority','role','information_score','predicted_mpa','lower_mpa','upper_mpa'])
                                            ui.label(plan['score_warning']).classes('field-help')
                                            with ui.row().classes('gap-3 flex-wrap'):
                                                ui.button('Exporter le plan Excel',icon='table_view',on_click=lambda:ui.download(
                                                    experiment_plan_workbook(plan_state['value'],result,'Plan d’expérience · '+mat['name']),
                                                    'plan-experience-materia.xlsx',MIME_XLSX)).props('outline')
                                                ui.button('Figer la prédiction associée',icon='lock_clock',on_click=lambda:download_json(
                                                    freeze_prediction(result,f"{mat['name']} · prédiction avant essais"),
                                                    'prediction-aveugle-materia.json')).props('outline')
                                                button('Comparer après les essais','/validation-aveugle','fact_check').props('flat')
                                    except (ValueError,TypeError) as exc:
                                        with plan_output: ui.label(str(exc)).classes('note w-full')
                                ui.button('Mettre à jour le plan',icon='refresh',on_click=update_experiment_plan).props('unelevated').classes('mx-3 mb-3')
                                update_experiment_plan()
                            validity_panel(result)
                            with ui.expansion('Méthode, facteurs et traçabilité',icon='fact_check').classes('w-full'):
                                if assumptions['evidence_calibrated']:
                                    if uncertainty_kind in {'source_level_predictive_interval','extrapolation_sensitivity'}:
                                        calibration=result['manifest']['uncertainty']['calibration']
                                        method_rows=[
                                            {'label':'Profil central','value':'Médiane de 3 publications','meaning':'Chaque publication compte une fois, quel que soit son nombre de formulations'},
                                            {'label':'Bande affichée','value':('P10–P90 pilote' if uncertainty_kind=='source_level_predictive_interval' else 'Sensibilité ×0,65 à ×1,50'),
                                             'meaning':('Résidus obtenus en laissant une publication entière de côté' if uncertainty_kind=='source_level_predictive_interval' else 'Variation de la dégradation cumulée autour de la P50 ; non probabiliste')},
                                            {'label':'Fenêtre commune','value':f"0–{assumptions['evidence_window_days']:.0f} jours",'meaning':'Aucune source n’est extrapolée pendant le calibrage'},
                                            {'label':'Couverture observée','value':f"{number_fr(calibration['empirical_point_coverage_pct'],1)} %",'meaning':f"Cible {number_fr(calibration['target_coverage_pct'])} % ; seulement {calibration['calibration_units']} unités de calibration"},
                                        ]
                                        if uncertainty_kind=='extrapolation_sensitivity':
                                            method_rows.append({'label':'Au-delà de la fenêtre','value':'P50 prolongée','meaning':'Le P10–P90 publié n’est pas revendiqué après 120 jours'})
                                    elif uncertainty_kind=='reported_standard_deviation':
                                        method_rows=[
                                            {'label':'Profil central','value':'Interpolation du tableau MDPI','meaning':'Courbes de module à 80, 100 et 120 °C, de 0 à 24 h'},
                                            {'label':'Bande affichée','value':'±1 écart-type publié','meaning':'Dispersion des mesures de l’article ; pas un intervalle prédictif'},
                                            {'label':'Domaine strict','value':'Milform 64 SST · 80–120 °C · 0–24 h','meaning':'Aucun transfert vers l’eau, un autre liquide ou 23 °C'},
                                        ]
                                    elif uncertainty_kind in {'internal_holdout_interval','observed_rate_envelope_extrapolation'}:
                                        calibration=result['manifest']['uncertainty']['calibration']
                                        method_rows=[
                                            {'label':'Cas de référence','value':'PP H301 · 4 formulations','meaning':'Tableau 2, 0, 30 et 120 jours, sept éprouvettes par point'},
                                            {'label':'Test hors formulation','value':f"{calibration['test_predictions']} prédictions masquées",'meaning':'La formulation cible ne participe jamais au calcul de sa propre rétention'},
                                            {'label':'Erreur relative moyenne','value':f"{number_fr(calibration['mape_pct'],2)} %",'meaning':'Comparaison directe entre modules prédits et modules publiés'},
                                            {'label':'Bande dans la fenêtre','value':f"± {number_fr(calibration['empirical_half_width_pct'],2)} %",'meaning':'Erreur relative maximale des huit prédictions masquées'},
                                            {'label':'Couverture interne','value':f"{number_fr(calibration['empirical_point_coverage_pct'],0)} %",'meaning':'Couverture observée sur les huit valeurs masquées ; pas une garantie externe'},
                                            {'label':'Après 120 jours','value':'Vitesses min–max observées' if uncertainty_kind=='observed_rate_envelope_extrapolation' else 'Non applicable','meaning':'Extrapolation signalée et élargie avec les quatre cinétiques tardives'},
                                        ]
                                    else:
                                        method_rows=[
                                            {'label':'Profil central','value':'Médiane de 4 formulations','meaning':'Mesures normalisées à 0, 30 et 120 jours'},
                                            {'label':'Bande affichée','value':'Quartiles 25–75 %','meaning':'Zone centrale, plus lisible ; ce n’est pas un IC'},
                                            {'label':'Après 120 jours','value':'Vitesses tardives interquartiles','meaning':'Extrapolation ; les extrêmes min–max restent signalés'},
                                            {'label':'Facteur température','value':f"× {assumptions['temperature_factor']:.2f}",'meaning':'Sensibilité Q10 non ajustée'},
                                            {'label':'Humidité et épaisseur','value':'Non calibrées','meaning':'Affichées dans le scénario, sans correction du profil PP'},
                                        ]
                                    method_rows += [
                                        {'label':'Sources indépendantes','value':str(assumptions['independent_sources']),'meaning':'Une publication homogène pour le cas PP H301 ; plusieurs publications compatibles restent nécessaires pour valider le transfert' if uncertainty_kind in {'internal_holdout_interval','observed_rate_envelope_extrapolation'} else '3 minimum exigées avant de parler d’intervalle prédictif calibré'},
                                        {'label':'Correspondance documentaire','value':f"{match['score']}/100",'meaning':match['meaning']},
                                    ]
                                else:
                                    method_rows=[
                                        {'label':'Demi-vie de référence','value':f"{assumptions['reference_half_life_years']:g} ans",'meaning':'Hypothèse de famille'},
                                        {'label':'Facteur température','value':f"× {assumptions['temperature_factor']:.2f}",'meaning':'Doublement par tranche de 10 °C'},
                                        {'label':'Facteur humidité','value':f"× {assumptions['humidity_factor']:.2f}",'meaning':'Selon les mécanismes déclarés'},
                                        {'label':'Facteur milieu','value':f"× {assumptions['environment_factor']:.2f}",'meaning':'Intérieur, extérieur ou immersion'},
                                        {'label':'Plage de transfert','value':'Vitesse ×0,65 à ×1,50','meaning':'Sensibilité resserrée autour de la meilleure estimation disponible'},
                                    ]
                                method_rows.append({'label':'Empreinte du calcul','value':result['fingerprint'][:16]+'…','meaning':'Identifie exactement les hypothèses'})
                                table_rows(method_rows,['label','value','meaning'])
                                for warning_text in result['manifest']['warnings']: ui.label('• '+warning_text).classes('small')
                                source=result['manifest'].get('source',{})
                                if source.get('sources'):
                                    ui.label('Publications utilisées').classes('font-bold text-sm')
                                    for source_item in source['sources']:
                                        label=f"{source_item.get('title') or source_item['id']} · {source_item['experiments']} série(s)"
                                        ui.link(label,source_item['url'],new_tab=True).classes('text-sm')
                                        ui.label('Extraction : '+', '.join(source_item['extraction_methods'])).classes('field-help')
                                elif source.get('url'):
                                    ui.link(source.get('title') or 'Source de la fiche',source['url'],new_tab=True).classes('text-sm')
                            def save_projection():
                                store.save(own,'simulation',f"{mat['name']} · {temperature.value:g} °C",result)
                                ui.notify('Projection enregistrée dans Mes projets.',type='positive')
                            with ui.row().classes('gap-3 flex-wrap'):
                                ui.button('Enregistrer',icon='bookmark_border',on_click=save_projection).props('unelevated')
                                ui.button('Figer avant essais',icon='lock_clock',on_click=lambda:download_json(
                                    freeze_prediction(result,f"{mat['name']} · prédiction avant essais"),
                                    'prediction-aveugle-materia.json')).props('outline')
                                ui.button('Exporter le classeur Excel',icon='table_view',on_click=lambda:ui.download(
                                    result_workbook(result,'Projection · '+mat['name']),
                                    'projection-materia.xlsx',MIME_XLSX)).props('outline')
                                ui.button('Plan d’expérience',icon='event_note',on_click=lambda:ui.download(
                                    experiment_plan_workbook(experiment_plan(result),result,'Plan d’expérience · '+mat['name']),
                                    'plan-experience-materia.xlsx',MIME_XLSX)).props('outline')
                                ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda:ui.download(
                                    result_pdf(result,'Projection · '+mat['name']),'rapport-materia.pdf','application/pdf')).props('outline')
                                ui.button('Carte de preuve',icon='fact_check',on_click=lambda:ui.download(
                                    evidence_card_pdf(result,'Projection · '+mat['name']),'carte-preuve-materia.pdf','application/pdf')).props('outline')
                                ui.button('Rapport étudiant',icon='article',on_click=lambda:ui.download(markdown_report(result,'Projection · '+mat['name']),'rapport-materia.md','text/markdown')).props('outline')
                                ui.button('Exporter le rapport JSON',icon='download',on_click=lambda:download_json(result,'rapport-projection-materia.json')).props('outline')
                    except (ValueError,TypeError) as exc:
                        with output: ui.label(str(exc)).classes('note w-full')
                with calculate_slot:
                    ui.button('Calculer',icon='show_chart',on_click=calculate).props('unelevated size=lg').classes('w-full')
                calculate()
            with ui.column().classes('panel gap-4 simulation-results'):
                ui.label('Aperçu instantané').classes('section-title')
                result_mount=ui.column().classes('w-full gap-4')
            output.move(result_mount)

@ui.page('/simuler/mesures')
def published_measurements():
    source_id='mdpi-pp-natural-aging-2024'
    rows=[row for row in material_db.evidence_rows('PP','outdoor') if row.get('source_id')==source_id]
    source=material_db.source(source_id)
    experiments=sorted({r['experiment_id'] for r in rows})
    labels={'MDPI-RPP1X':'PP recyclé · 1 cycle','MDPI-RPP3X':'PP recyclé · 3 cycles',
            'MDPI-RPP3X-3CHF':'PP recyclé · 3 % fibres de maïs','MDPI-RPP3X-5CHF':'PP recyclé · 5 % fibres de maïs'}
    formulation_details={
        'MDPI-RPP1X':'Grade PP H301 (Braskem), extrudé une fois puis injecté — R-PP1x',
        'MDPI-RPP3X':'Grade PP H301 (Braskem), extrudé trois fois puis injecté — R-PP3x',
        'MDPI-RPP3X-3CHF':'PP H301 retransformé, avec 3 % massiques de fibres de balle de maïs',
        'MDPI-RPP3X-5CHF':'PP H301 retransformé, avec 5 % massiques de fibres de balle de maïs',
    }
    with shell('/simuler','Mesures publiées'):
        intro('Parcours 2 · données réelles','Explorer les mesures publiées',
              'Cette vue trace les valeurs du tableau scientifique et la bande choisie. Materia interpole entre les points mais refuse toute extrapolation.')
        simulation_switcher('/simuler/mesures')
        with ui.element('div').classes('work-grid w-full'):
            with ui.column().classes('panel gap-5'):
                with ui.row().classes('w-full justify-between items-center gap-3'):
                    ui.label('Polypropylène vieilli naturellement').classes('section-title'); pill('Article en libre accès · CC BY 4.0','pill-teal')
                formulation=ui.select({key:labels.get(key,key) for key in experiments},value=experiments[0],label='Formulation publiée').props('outlined').classes('w-full')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    horizon=ui.number('Horizon observé',value=120,min=0).props('outlined').classes('grow min-w-48')
                    horizon_unit=ui.select({'days':'Jours','months':'Mois','years':'Années'},value='days',label='Unité').props('outlined').classes('min-w-48')
                    threshold=ui.number('Seuil conservé (%)',value=90,min=1,max=100).props('outlined').classes('grow min-w-48')
                uncertainty_mode=ui.select({
                    'sd':'Dispersion des éprouvettes (±1 écart-type)',
                    'ci95':'Précision de la moyenne (IC95 %)',
                },value='sd',label='Bande affichée').props('outlined').classes('w-full')
                ui.label('L’écart-type décrit la dispersion des éprouvettes. L’IC95 % décrit la précision de la moyenne publiée ; aucun des deux ne prédit la dispersion d’un futur grade.').classes('field-help')
                output=ui.column().classes('w-full')
                def calculate():
                    output.clear()
                    try:
                        horizon_days=duration_to_days(float(horizon.value),horizon_unit.value)
                        result=published_evidence_curve(rows,formulation.value,horizon_days,float(threshold.value),uncertainty_mode.value)
                        observed=result['observed_points']; loss=100-result['retention'][-1]
                        with output:
                            with ui.element('div').classes('result-grid w-full'):
                                for label,value,detail in [
                                    ('Module initial moyen publié',f"{number_fr(observed[0]['modulus_mpa'],1)} MPa",'Moyenne de 7 éprouvettes'),
                                    ('Module à la fin',f"{number_fr(result['modulus'][-1],1)} MPa",f"{curve_value_origin(result)} · perte {number_fr(loss,1)} %"),
                                    ('Domaine observé','0 à 120 jours','Extrapolation bloquée')]:
                                    with ui.column().classes('result-stat gap-1'):
                                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                            ui.label(f"La formulation {labels.get(formulation.value,formulation.value)} conserve {number_fr(result['retention'][-1],1)} % de son module initial après {horizon_days:g} jours. Les lignes entre 0, 30 et 120 jours sont une interpolation ; elles ne constituent pas de nouvelles mesures.").classes('result-summary')
                            ui.label(formulation_details[formulation.value]).classes('pill pill-teal')
                            with ui.element('div').props('role=img aria-label="Mesures publiées du module de Young à 0, 30 et 120 jours avec écart-type"').classes('w-full'):
                                ui.plotly(curve(result,observed[0]['modulus_mpa']*float(threshold.value)/100)).classes('w-full')
                            with ui.expansion('Afficher les valeurs accessibles',icon='table_chart').classes('w-full'):
                                table_rows(sampled_curve_rows(result,time_unit='jours'),['temps','unite','module_mpa','module_min_mpa','module_max_mpa','retention_pct','origine'])
                            ui.label(result['manifest']['status']+' · Cette série décrit la formulation de l’article et ne représente pas tous les PP.').classes('note w-full')
                            validity_panel(result)
                            with ui.row().classes('gap-3 flex-wrap'):
                                ui.button('Rapport étudiant',icon='article',on_click=lambda:ui.download(markdown_report(result,'Mesures publiées · PP'),'rapport-mesures-pp.md','text/markdown')).props('outline')
                                ui.button('Exporter le classeur Excel',icon='table_view',on_click=lambda:ui.download(
                                    result_workbook(result,'Mesures publiées · '+labels.get(formulation.value,formulation.value)),
                                    'mesures-publiees-pp.xlsx',MIME_XLSX)).props('outline')
                                ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda:ui.download(
                                    result_pdf(result,'Mesures publiées · '+labels.get(formulation.value,formulation.value)),
                                    'rapport-mesures-pp.pdf','application/pdf')).props('outline')
                                ui.button('Carte de preuve',icon='fact_check',on_click=lambda:ui.download(
                                    evidence_card_pdf(result,'Mesures publiées · '+labels.get(formulation.value,formulation.value)),
                                    'carte-preuve-mesures-pp.pdf','application/pdf')).props('outline')
                                ui.button('Exporter cette courbe',icon='download',on_click=lambda:download_json(result,'mesures-publiees-pp.json')).props('outline')
                    except (ValueError,TypeError) as exc:
                        with output: ui.label(str(exc)).classes('note w-full')
                formulation.on_value_change(lambda:calculate()); horizon.on_value_change(lambda:calculate()); horizon_unit.on_value_change(lambda:calculate()); threshold.on_value_change(lambda:calculate()); uncertainty_mode.on_value_change(lambda:calculate())
                calculate()
            with ui.column().classes('panel gap-4 sticky-help'):
                ui.icon('verified',size='28px',color='secondary'); ui.label('Preuve utilisée').classes('section-title')
                if source:
                    ui.label(source['title']).classes('font-medium'); ui.label(source['organization']).classes('small')
                    ui.link('Ouvrir l’article source',source['url'],new_tab=True).classes('text-sm')
                    ui.label('Matos et al., Polymers 2024 · tableau 2 · moyenne ± écart-type, n = 7.').classes('body-copy')
                    with ui.expansion('Pourquoi 604,1 MPa et pas 1 à 1,8 GPa ?',icon='help_outline').classes('w-full'):
                        ui.label('604,1 MPa n’est pas une valeur générique du PP. C’est la moyenne mesurée sur sept éprouvettes du grade PP H301 après un cycle d’extrusion puis injection. Le grade, le retraitement, la cristallinité, la vitesse d’essai et le conditionnement expliquent qu’elle puisse être inférieure aux plages commerciales souvent annoncées pour du PP vierge.').classes('body-copy p-3')
                        ui.label('La comparaison correcte doit utiliser le même grade, la même transformation et le même protocole. Materia conserve donc cette série sous le nom R-PP1x et ne la présente plus comme « le module du PP ».').classes('note m-3')
                    ui.label('Source primaire relue · licence CC BY 4.0').classes('pill pill-teal')
                ui.label('Domaine publié : 0 à 120 jours.').classes('note w-full')
        with ui.column().classes('panel w-full gap-4 mt-6'):
            ui.label('Comparer les quatre formulations mesurées').classes('section-title')
            ui.label('Les points et barres représentent directement les moyennes et écarts-types du tableau 2. Les lignes servent uniquement à guider la lecture entre les trois temps mesurés.').classes('body-copy')
            comparison_figure=base(); comparison_figure.update_xaxes(title='Temps de vieillissement naturel (jours)')
            summary=[]
            for index,experiment in enumerate(experiments):
                group=sorted((row for row in rows if row['experiment_id']==experiment),key=lambda row:row['time_days'])
                times=[row['time_days'] for row in group]; values=[row['modulus_mpa'] for row in group]
                deviations=[row['standard_deviation_mpa'] for row in group]
                comparison_figure.add_trace(go.Scatter(x=times,y=values,mode='lines+markers',name=labels.get(experiment,experiment),
                    line=dict(color=['#2156bc','#13958b','#8b64b6','#dc8535'][index],width=2),marker=dict(size=8),
                    error_y=dict(type='data',array=deviations,visible=True)))
                summary.append({'formulation':labels.get(experiment,experiment),'module_initial_mpa':round(values[0],1),
                    'module_120_mpa':round(values[-1],1),'retention_120_pct':round(values[-1]/values[0]*100,1),
                    'loss_120_pct':round((1-values[-1]/values[0])*100,1)})
            comparison_figure.update_yaxes(title='Module de Young publié (MPa)',rangemode='tozero')
            with ui.element('div').props('role=img aria-label="Comparaison des quatre formulations de polypropylène mesurées à 0, 30 et 120 jours"').classes('w-full'):
                ui.plotly(comparison_figure).classes('w-full')
            table_rows(summary,['formulation','module_initial_mpa','module_120_mpa','retention_120_pct','loss_120_pct'])

@ui.page('/simuler/apprendre')
def guided_simulator(material: str | None=None):
    # Ancienne URL conservée uniquement pour ne pas produire de page cassée.
    ui.navigate.to('/simuler')

@ui.page('/simuler/legacy')
def legacy_simulator(material: str | None=None):
    own=owner()
    existing=app.storage.user.get('draft')
    selected=material if material in CATALOG else 'demo-a'
    data=dict(existing) if existing else Scenario(material=selected,e0=CATALOG[selected]['e0']).model_dump()
    if material in CATALOG: data.update(material=material,e0=CATALOG[material]['e0'])
    state={'step':0,'data':data,'result':None}
    with shell('/simuler','Simuler'):
        intro('Estimateur de vieillissement','Du matériau à la courbe','Choisissez un matériau, renseignez le module de Young de sa fiche technique et décrivez son environnement pour obtenir une première estimation de vieillissement.')
        with ui.column().classes('panel w-full gap-4 mt-5'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Estimer depuis une fiche matériau').classes('section-title')
                pill(f"{len(material_db.catalog())} matériaux disponibles",'pill-teal')
            ui.label('Cet estimateur part du module initial de la fiche technique. Il applique une cinétique générique de la famille du matériau et des facteurs explicites de température, humidité, épaisseur et milieu.').classes('body-copy')
            materials=available_materials()
            estimate_options={m['id']:f"{m['name']} ({m['abbreviation']}) · {m['family']}" for m in materials.values()}
            estimate_material=ui.select(estimate_options,value='PP',label='Matériau').props('outlined use-input').classes('w-full')
            initial=standard_profile(materials['PP'])
            with ui.row().classes('w-full gap-3 flex-wrap'):
                estimate_e0=ui.number('Module de Young initial de la fiche (MPa)',value=initial['suggested_modulus_mpa'],min=.01).props('outlined').classes('min-w-64 grow')
                estimate_temp=ui.number('Température de service (°C)',value=23).props('outlined').classes('min-w-48')
                estimate_rh=ui.number('Humidité relative (%)',value=50,min=0,max=100).props('outlined').classes('min-w-48')
                estimate_thickness=ui.number('Épaisseur (mm)',value=2,min=.01).props('outlined').classes('min-w-48')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                estimate_exposure=ui.select({'indoor':'Intérieur / abrité','outdoor':'Extérieur / UV','immersion':'Immersion / contact permanent'},value='outdoor',label='Milieu').props('outlined').classes('min-w-64 grow')
                estimate_horizon=ui.number('Durée à tracer',value=10,min=.01).props('outlined').classes('min-w-48')
                estimate_horizon_unit=ui.select({'days':'Jours','months':'Mois','years':'Années'},value='years',label='Unité').props('outlined').classes('min-w-40')
                estimate_threshold=ui.number('Seuil de module conservé (%)',value=80,min=1,max=100).props('outlined').classes('min-w-64')
            estimate_basis=ui.label(initial['basis']).classes('note w-full')
            estimate_output=ui.column().classes('w-full')
            def update_estimate_material():
                profile=standard_profile(materials[estimate_material.value])
                estimate_e0.value=profile['suggested_modulus_mpa']; estimate_basis.text=profile['basis']
            def run_estimate():
                estimate_output.clear()
                try:
                    mat=materials[estimate_material.value]
                    horizon_years=duration_to_years(float(estimate_horizon.value),estimate_horizon_unit.value)
                    result=estimate_from_datasheet(mat,float(estimate_e0.value),float(estimate_temp.value),
                        float(estimate_rh.value),float(estimate_thickness.value),horizon_years,
                        float(estimate_threshold.value),estimate_exposure.value,
                        material_db.evidence_rows(mat['id'],estimate_exposure.value) if not mat.get('custom') else [])
                    result['manifest']['inputs']['horizon_display']={'value':float(estimate_horizon.value),'unit':estimate_horizon_unit.value,
                        'label':duration_label(float(estimate_horizon.value),estimate_horizon_unit.value)}
                    refresh_result_fingerprint(result)
                    threshold=float(estimate_e0.value)*float(estimate_threshold.value)/100
                    with estimate_output:
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label(mat['name']).classes('section-title'); pill('Estimation', 'pill-amber')
                        ui.plotly(curve(result,threshold)).classes('w-full')
                        crossing=result['crossing_estimate_years']; lo,hi=result['crossing_interval']
                        ui.label(f"Seuil estimé : {format_years_months(crossing)}").classes('section-title')
                        ui.label(f"Enveloppe de scénarios : de {format_years_months(lo)} à {format_years_months(hi)} · valeurs exactes : {number_fr(lo,2)}–{number_fr(hi,2)} ans").classes('small')
                        assumptions=result['manifest']['assumptions']
                        if assumptions['evidence_calibrated']:
                            ui.label(f"Profil en deux phases construit sur {assumptions['evidence_experiments']} formulations publiées, 0–120 jours. La zone après la ligne verticale est extrapolée.").classes('pill pill-teal')
                            ui.label(f"Sensibilité température Q10 : ×{assumptions['temperature_factor']:.2f}. Ce facteur n’est pas ajusté par la publication ; humidité et épaisseur ne modifient pas le profil PP publié.").classes('small')
                        else:
                            ui.label(f"Hypothèses de famille : demi-vie {assumptions['reference_half_life_years']:g} ans ; facteurs température {assumptions['temperature_factor']:.2f}, humidité {assumptions['humidity_factor']:.2f}, milieu {assumptions['environment_factor']:.2f}.").classes('small')
                        ui.label(result['manifest']['status']+' — La formulation, les additifs et le procédé peuvent fortement déplacer cette courbe.').classes('note w-full')
                        with ui.row().classes('gap-3 flex-wrap'):
                            ui.button('Exporter le classeur Excel',icon='table_view',on_click=lambda:ui.download(
                                result_workbook(result,'Estimation de vieillissement'),
                                'estimation-vieillissement.xlsx',MIME_XLSX)).props('outline')
                            ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda:ui.download(
                                result_pdf(result,'Estimation de vieillissement'),
                                'estimation-vieillissement.pdf','application/pdf')).props('outline')
                            ui.button('Carte de preuve',icon='fact_check',on_click=lambda:ui.download(
                                evidence_card_pdf(result,'Estimation de vieillissement'),
                                'carte-preuve-estimation.pdf','application/pdf')).props('outline')
                            ui.button('Exporter JSON',icon='download',on_click=lambda:download_json(result,'estimation-vieillissement.json')).props('outline')
                except (ValueError,TypeError) as exc:
                    with estimate_output: ui.label(str(exc)).classes('note w-full')
            estimate_material.on_value_change(lambda: update_estimate_material())
            ui.button('Calculer la courbe de vieillissement',icon='show_chart',on_click=run_estimate).props('unelevated')
            run_estimate()
        ui.label('Vérifier avec des mesures publiées').classes('section-title mt-8')
        with ui.column().classes('panel w-full gap-4 mt-5'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Explorer un matériau de la base').classes('section-title')
                pill('Données réelles uniquement','pill-teal')
            lin_epoxy=material_db.material('FLAX_EPOXY')
            ui.label('La base contient 75 fiches. Le composite lin/époxy possède 10 points relus avec la publication primaire. Materia peut les interpoler jusqu’à 38 jours aux conditions exactes, sans extrapoler ni annoncer une durée de vie.').classes('body-copy')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                with ui.column().classes('stat-card grow'):
                    ui.label('75').classes('stat-value'); ui.label('fiches documentaires').classes('small')
                with ui.column().classes('stat-card grow'):
                    ui.label('1').classes('stat-value'); ui.label('matériau avec mesures').classes('small')
                with ui.column().classes('stat-card grow'):
                    ui.label(str(lin_epoxy['accepted_observations'])).classes('stat-value'); ui.label('points publiés acceptés').classes('small')
                with ui.column().classes('stat-card grow'):
                    ui.label(str(lin_epoxy['accepted_experiments'])).classes('stat-value'); ui.label('expériences relues').classes('small')
            real_material=ui.select({'FLAX_EPOXY':'Composite fibres de lin / époxy (Lin/époxy)'},value='FLAX_EPOXY',label='Matériau avec données traçables').props('outlined').classes('w-full')
            series_data={
                'SCIDA-20C-90RH':dict(temperature=20.,humidity=90.,thickness=2.5,horizon=38.),
                'SCIDA-40C-90RH':dict(temperature=40.,humidity=90.,thickness=2.5,horizon=38.),
            }
            series=ui.select({
                'SCIDA-20C-90RH':'Série publiée · 20 °C · 90 % HR · 2,5 mm · 5 points',
                'SCIDA-40C-90RH':'Série publiée · 40 °C · 90 % HR · 2,5 mm · 5 points',
            },value='SCIDA-20C-90RH',label='Série expérimentale disponible').props('outlined').classes('w-full')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                real_temp=ui.number('Température mesurée (°C)',value=20).props('outlined readonly').classes('min-w-48')
                real_rh=ui.number('Humidité mesurée (%)',value=90,min=0,max=100).props('outlined readonly').classes('min-w-48')
                real_thickness=ui.number('Épaisseur mesurée (mm)',value=2.5,min=.001).props('outlined readonly').classes('min-w-48')
                real_horizon=ui.number('Horizon (jours)',value=38,min=0).props('outlined').classes('min-w-48')
                real_threshold=ui.number('Seuil conservé (%)',value=80,min=1,max=100).props('outlined').classes('min-w-48')
            pending_preview=ui.checkbox('Inclure les données encore en attente lorsqu’elles existent',value=False)
            ui.label('Les 10 points sont acceptés pour une interpolation descriptive. Deux expériences restent insuffisantes pour la validation croisée minimale de trois expériences et pour toute prédiction de durée de vie.').classes('note w-full')
            real_output=ui.column().classes('w-full')
            def select_series():
                chosen=series_data[series.value]
                real_temp.value=chosen['temperature']; real_rh.value=chosen['humidity']
                real_thickness.value=chosen['thickness']; real_horizon.value=chosen['horizon']
            def run_real():
                real_output.clear()
                try:
                    mat=material_db.material(real_material.value)
                    rows=material_db.observation_rows(real_material.value,include_pending=pending_preview.value)
                    result=observed_projection(rows,float(real_temp.value),float(real_rh.value),float(real_thickness.value),float(real_horizon.value),float(real_threshold.value))
                    with real_output:
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label(mat['name']).classes('section-title')
                            pill('En attente de revue' if result['pending'] else 'Corpus accepté','pill-amber' if result['pending'] else 'pill-teal')
                        ui.plotly(curve(result,result['manifest']['inputs']['e0']*float(real_threshold.value)/100)).classes('w-full')
                        ui.label(f"{len(result['observed_points'])} points · interpolation linéaire · domaine 0–{max(p['time_days'] for p in result['observed_points']):g} jours").classes('small')
                        ui.label('La bande ±3 % représente seulement l’incertitude estimée de lecture de la figure. La dispersion entre éprouvettes et l’incertitude prédictive ne sont pas disponibles.').classes('small')
                        ui.label(result['manifest']['status']).classes('note w-full')
                        validity_panel(result)
                        with ui.row().classes('gap-3 flex-wrap'):
                            ui.button('Exporter le classeur Excel',icon='table_view',on_click=lambda:ui.download(
                                result_workbook(result,'Observations Lin / époxy'),
                                'observations-lin-epoxy.xlsx',MIME_XLSX)).props('outline')
                            ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda:ui.download(
                                result_pdf(result,'Observations Lin / époxy'),
                                'observations-lin-epoxy.pdf','application/pdf')).props('outline')
                            ui.button('Carte de preuve',icon='fact_check',on_click=lambda:ui.download(
                                evidence_card_pdf(result,'Observations Lin / époxy'),
                                'carte-preuve-observations.pdf','application/pdf')).props('outline')
                            ui.button('Exporter JSON',icon='download',on_click=lambda:download_json(result,'exploration-observations.json')).props('outline')
                except (ValueError,TypeError) as exc:
                    with real_output:
                        ui.label(str(exc)).classes('note w-full')
                        ui.link('Importer ou examiner les données →','/donnees').classes('text-sm text-primary no-underline')
            series.on_value_change(lambda:select_series())
            ui.button('Tracer la courbe disponible',icon='show_chart',on_click=run_real).props('unelevated')
            run_real()
        ui.label('Mode pédagogique synthétique').classes('section-title mt-8')
        warning()
        @ui.refreshable
        def wizard():
            step=state['step']; d=state['data']
            with ui.element('div').classes('step-list'):
                for i,title in enumerate(['Mon matériau','Environnement','Mon objectif','Vérification','Résultats']):
                    ui.label(f'{i+1}  {title}').classes('step-item '+('current' if i==step else 'done' if i<step else ''))
            def setval(key,v):
                d[key]=v; app.storage.user['draft']=dict(d)
            def move(n):
                try:
                    Scenario(**d)
                    if n==4:
                        state['result']=simulate(Scenario(**d))
                    state['step']=n; wizard.refresh()
                except (ValueError,TypeError): ui.notify('Vérifiez les valeurs : module positif, seuil entre 0 et 100 %, température 20–100 °C et horizon 1–5 000 jours.',type='negative')
            if step<4:
                with ui.element('div').classes('work-grid w-full'):
                    with ui.column().classes('panel w-full gap-5'):
                        if step==0:
                            ui.label('Quel matériau souhaitez-vous explorer ?').classes('section-title')
                            def change_material(e):
                                setval('material',e.value); setval('e0',CATALOG[e.value]['e0']); wizard.refresh()
                            ui.select({k:m['name']+' · '+m['tag'] for k,m in CATALOG.items()},value=d['material'],label='Cas pédagogique · obligatoire',on_change=change_material).props('outlined').classes('w-full')
                            ui.label(CATALOG[d['material']]['description']).classes('body-copy')
                            ui.number('Module de Young initial (MPa) · obligatoire',value=d['e0'],min=1,max=1e7,on_change=lambda e:setval('e0',e.value)).props('outlined').classes('w-full')
                            ui.label('La rigidité initiale seule ne permet pas de connaître une cinétique réelle. Ici, la cinétique est fictive et fixée par le cas choisi.').classes('small')
                        elif step==1:
                            ui.label('Dans quel environnement ?').classes('section-title')
                            ui.number('Température constante (°C) · obligatoire',value=d['temperature'],min=20,max=100,on_change=lambda e:setval('temperature',e.value)).props('outlined').classes('w-full')
                            ui.label('Plage de démonstration : 20 à 100 °C. La dépendance thermique est illustrative.').classes('small')
                            with ui.expansion('Conditions retenues et limites',icon='tune').classes('w-full'):
                                ui.label('Exposition constante, essai de traction de référence inchangé. Humidité, UV, oxygène, géométrie et couplages ne sont pas modélisés dans cette démonstration.').classes('body-copy p-4')
                        elif step==2:
                            ui.label('Quel seuil souhaitez-vous suivre ?').classes('section-title')
                            ui.number('Horizon (jours) · obligatoire',value=d['horizon'],min=1,max=5000,on_change=lambda e:setval('horizon',e.value)).props('outlined').classes('w-full')
                            ui.number('Module conservé au seuil (%) · obligatoire',value=d['threshold'],min=1,max=100,on_change=lambda e:setval('threshold',e.value)).props('outlined').classes('w-full')
                            ui.label('80 % conservés correspondent à une perte de 20 % de rigidité. Ce seuil ne définit pas à lui seul la fin de service.').classes('small')
                            with ui.expansion('Explorer la sensibilité des paramètres',icon='tune').classes('w-full'):
                                ui.number('Dispersion logarithmique de la vitesse (%)',value=d['spread'],min=0,max=60,on_change=lambda e:setval('spread',e.value)).props('outlined').classes('w-full p-3')
                                ui.label('Hypothèse de dispersion réglable, non mesurée. L’enveloppe 5–95 % ne constitue pas un intervalle de prédiction calibré.').classes('small p-3')
                        else:
                            ui.label('Vérifiez vos hypothèses').classes('section-title')
                            for label,value in [('Matériau',CATALOG[d['material']]['name']),('Module initial',f"{d['e0']} MPa"),('Température',f"{d['temperature']} °C"),('Horizon',f"{d['horizon']} jours"),('Seuil',f"{d['threshold']} % du module initial"),('Sensibilité',f"Dispersion logarithmique : {d['spread']} %")]:
                                with ui.row().classes('justify-between w-full row-line'):
                                    ui.label(label).classes('small'); ui.label(value).classes('text-sm font-medium')
                            ui.label('Le calcul utilise une loi exponentielle et une accélération thermique fictive. Il ne doit pas servir à dimensionner une pièce réelle.').classes('note w-full')
                        with ui.row().classes('w-full justify-between mt-4'):
                            if step>0: ui.button('Retour',icon='arrow_back',on_click=lambda:move(step-1)).props('flat')
                            else: ui.space()
                            ui.button('Calculer le scénario' if step==3 else 'Continuer',icon='arrow_forward',on_click=lambda:move(step+1)).props('unelevated')
                    with ui.column().classes('panel gap-4'):
                        ui.icon('lightbulb',color='secondary',size='27px'); ui.label('Un repère pour comprendre').classes('section-title')
                        tips=['Le module de Young mesure la rigidité : plus il est élevé, plus le matériau résiste à une petite déformation.','Une température plus élevée peut accélérer certains mécanismes. Le passage aux conditions réelles exige une validation.','Un seuil est un objectif que vous choisissez. Il ne correspond pas automatiquement à une rupture.','Tous les paramètres et la version du calcul seront inclus dans vos exports.']
                        ui.label(tips[step]).classes('body-copy'); ui.link('Approfondir dans le guide →','/comprendre').classes('text-sm text-primary no-underline')
            else:
                r=state['result']; s=Scenario(**d)
                with ui.column().classes('panel w-full gap-3'):
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label('Votre scénario, dans le temps').classes('section-title'); pill('Synthétique · non validé','pill-amber')
                    with ui.element('div').classes('stat-grid w-full'):
                        for label,value in [('Module en fin d’horizon',f"{number_fr(r['modulus'][-1])} MPa"),('Module conservé',f"{number_fr(r['retention'][-1],1)} %"),('Premier franchissement',f"{r['crossing']:.0f} jours" if r['crossing'] is not None else 'Non atteint')]:
                            with ui.column().classes('gap-0'): ui.label(label).classes('stat-label'); ui.label(value).classes('stat-value')
                    ui.plotly(curve(r,s.e0*s.threshold/100)).classes('w-full')
                    a,b=r['crossing_interval']; ui.label('Franchissement dans l’enveloppe de sensibilité : '+(f'{a:.0f}' if a is not None else 'au-delà de l’horizon')+' à '+(f'{b:.0f} jours' if b is not None else 'au-delà de l’horizon')+'. Non calibré expérimentalement.').classes('small')
                    if r['crossing'] is None: ui.label('Seuil non atteint sur l’horizon étudié. Cela ne signifie pas une durée de vie infinie.').classes('note w-full')
                    validity_panel(r)
                    name=ui.input('Nom de la simulation',value=f"{CATALOG[s.material]['name']} · {s.temperature:g} °C").props('outlined').classes('w-full')
                    def save_result():
                        store.save(own,'simulation',name.value or 'Simulation',r); ui.notify('Simulation enregistrée dans Mes projets.',type='positive')
                    with ui.row().classes('gap-3'):
                        ui.button('Enregistrer',icon='bookmark_border',on_click=save_result).props('unelevated')
                        ui.button('Exporter le classeur Excel',icon='download',on_click=lambda:ui.download(
                            result_workbook(r,'Exercice synthétique · '+CATALOG[s.material]['name']),
                            'materia-synthetique.xlsx',MIME_XLSX)).props('outline')
                        ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda:ui.download(
                            result_pdf(r,'Exercice synthétique · '+CATALOG[s.material]['name']),
                            'materia-synthetique.pdf','application/pdf')).props('outline')
                        ui.button('Carte de preuve',icon='fact_check',on_click=lambda:ui.download(
                            evidence_card_pdf(r,'Exercice synthétique · '+CATALOG[s.material]['name']),
                            'carte-preuve-synthetique.pdf','application/pdf')).props('outline')
                        ui.button('Fiche JSON',icon='description',on_click=lambda:download_json(r,'materia-simulation.json')).props('outline')
                        ui.button('Modifier',on_click=lambda:move(0)).props('flat')
                    with ui.expansion('Données accessibles et reproductibilité',icon='table_chart').classes('w-full mt-3'):
                        ui.label(f"Modèle : {VERSION} · Empreinte : {r['fingerprint'][:16]}").classes('small p-3')
                        table_rows([dict(jours=round(t,2),module_MPa=round(e,2),retention_pct=round(p,2)) for t,e,p in zip(r['time'],r['modulus'],r['retention'])])
        wizard()

@ui.page('/comparer')
def compare():
    with shell('/comparer','Comparer'):
        intro('Mettre en perspective','Comparer matériaux et conditions','Comparez jusqu’à quatre matériaux, plusieurs températures ou vos simulations enregistrées. Les courbes sont normalisées en pourcentage du module initial.')
        with ui.tabs(value='Matériaux').classes('w-full min-w-0 mt-4') as tabs:
            ui.tab('Matériaux'); ui.tab('Mes simulations')
        @ui.refreshable
        def selected_panel():
            if tabs.value=='Matériaux':
                materials=available_materials(); default_ids=[ident for ident in ('PP','LDPE') if ident in materials]
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    material_select=ui.select({key:f"{m['name']} ({m['abbreviation']})"+(' · personnalisé' if m.get('custom') else '') for key,m in materials.items()},
                        value=default_ids,multiple=True,label='Matériaux à comparer (1 à 4)').props('outlined use-chips use-input').classes('w-full')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        compare_temp=ui.number('Température (°C)',value=23,min=-40,max=160).props('outlined').classes('grow min-w-40')
                        compare_rh=ui.number('Humidité relative (%)',value=50,min=0,max=100).props('outlined').classes('grow min-w-40')
                        compare_thickness=ui.number('Épaisseur (mm)',value=2,min=.01).props('outlined').classes('grow min-w-40')
                        compare_exposure=ui.select({'indoor':'Intérieur','outdoor':'Extérieur / UV','immersion':'Immersion'},value='outdoor',label='Milieu').props('outlined').classes('grow min-w-48')
                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        compare_horizon=ui.number('Horizon',value=2,min=.01).props('outlined').classes('grow min-w-40')
                        compare_unit=ui.select({'days':'Jours','months':'Mois','years':'Années'},value='years',label='Unité').props('outlined').classes('min-w-40')
                        compare_threshold=ui.number('Seuil conservé (%)',value=80,min=1,max=100).props('outlined').classes('grow min-w-48')
                    material_area=ui.column().classes('w-full')
                    def compare_materials():
                        material_area.clear(); selected_ids=list(material_select.value or [])
                        with material_area:
                            if not 1<=len(selected_ids)<=4:
                                ui.label('Choisissez entre un et quatre matériaux.').classes('note w-full'); return
                            try:
                                horizon_days=duration_to_days(float(compare_horizon.value),compare_unit.value)
                                horizon_years=horizon_days/365.25
                                if horizon_days<1 or horizon_years>100: raise ValueError('L’horizon doit être compris entre un jour et 100 ans.')
                                values=[]; summary=[]
                                for ident in selected_ids:
                                    mat=materials[ident]; profile=standard_profile(mat)
                                    result=estimate_from_datasheet(mat,profile['suggested_modulus_mpa'],float(compare_temp.value),
                                        float(compare_rh.value),float(compare_thickness.value),horizon_years,
                                        float(compare_threshold.value),compare_exposure.value,
                                        material_db.evidence_rows(ident,compare_exposure.value) if not mat.get('custom') else [])
                                    result['manifest']['inputs']['horizon_display']={'value':float(compare_horizon.value),'unit':compare_unit.value,
                                        'label':duration_label(float(compare_horizon.value),compare_unit.value)}
                                    refresh_result_fingerprint(result)
                                    values.append((mat['name'],result))
                                    summary.append({'materiau':mat['name'],'module_initial_mpa':round(profile['suggested_modulus_mpa'],2),
                                        'module_final_mpa':round(result['modulus'][-1],2),'retention_finale_pct':round(result['retention'][-1],1),
                                        'seuil':format_years_months(result['crossing_estimate_years']),
                                        'origine':curve_value_origin(result),
                                        'niveau':'Personnalisé / hypothèses' if mat.get('custom') else evidence_assessment(result)['label']})
                                compatibility=comparison_assessment(values); comparison_panel(compatibility)
                                if not compatibility['can_compare']:
                                    ui.label('Les courbes ne sont pas tracées tant que la propriété comparée diffère.').classes('note w-full'); return
                                ui.plotly(comparison(values,compare_unit.value,float(compare_threshold.value))).classes('w-full')
                                table_rows(summary,['materiau','module_initial_mpa','module_final_mpa','retention_finale_pct','seuil','origine','niveau'])
                                ui.label('Comparaison exploratoire à conditions communes. Chaque matériau conserve son module initial et ses hypothèses de famille ; aucune courbe ne constitue une qualification.').classes('note w-full')
                                ui.button('Exporter la comparaison Excel',icon='table_view',on_click=lambda values=values:ui.download(
                                    comparison_workbook(values,'Comparaison de matériaux'),'comparaison-materiaux.xlsx',MIME_XLSX)).props('outline')
                            except (ValueError,TypeError) as exc: ui.label(str(exc)).classes('note w-full')
                    ui.button('Comparer les matériaux',icon='compare_arrows',on_click=compare_materials).props('unelevated')
                    compare_materials()
            else:
                saved=store.records(owner(),'simulation')
                if not saved:
                    with ui.column().classes('panel w-full mt-4'):
                        ui.label('Enregistrez une première simulation pour la retrouver ici.').classes('body-copy'); button('Créer une simulation','/simuler')
                else:
                    select=ui.select({r['id']:r['name'] for r in saved},multiple=True,value=[r['id'] for r in saved[:2]],label='Simulations à comparer (maximum 4)').props('outlined use-chips').classes('w-full my-4')
                    @ui.refreshable
                    def saved_plot():
                        chosen=[r for r in saved if r['id'] in select.value]
                        if not 1<=len(chosen)<=4:
                            ui.label('Choisissez une à quatre simulations.').classes('note'); return
                        values=[(r['name'],r['payload']) for r in chosen]
                        thresholds={float((r['payload'].get('manifest',{}).get('inputs') or {}).get('threshold'))
                                    for r in chosen if (r['payload'].get('manifest',{}).get('inputs') or {}).get('threshold') is not None}
                        common_threshold=next(iter(thresholds)) if len(thresholds)==1 else None
                        compatibility=comparison_assessment(values); comparison_panel(compatibility)
                        if not compatibility['can_compare']:
                            ui.label('Les simulations ne portent pas sur la même propriété.').classes('note w-full'); return
                        ui.plotly(comparison(values,threshold_percent=common_threshold)).classes('w-full')
                        saved_summary=[]
                        for record in chosen:
                            result=record['payload']; manifest=result.get('manifest',{}); model=str(manifest.get('model',''))
                            horizon_label=(manifest.get('inputs',{}).get('horizon_display') or {}).get('label') or f"{max(result.get('time') or [0]):g} jours"
                            crossing=(format_years_months(result['crossing_estimate_years'])
                                      if model.startswith('datasheet-screening-') and result.get('crossing_estimate_years') is not None
                                      else f"{result['crossing']:.0f} jours" if result.get('crossing') is not None else 'Non atteint')
                            saved_summary.append({'simulation':record['name'],'horizon':horizon_label,
                                                  'retention_finale_pct':round(float(result['retention'][-1]),1),
                                                  'temps_au_seuil':crossing,'origine':curve_value_origin(result),
                                                  'statut':manifest.get('status','Non renseigné')})
                        table_rows(saved_summary,['simulation','horizon','retention_finale_pct','temps_au_seuil','origine','statut'])
                        ui.label('Toutes les courbes utilisent la même unité de temps. Quand les horizons diffèrent, chaque ligne s’arrête à sa propre dernière date.').classes('small')
                        ui.button('Exporter la comparaison Excel',icon='table_view',on_click=lambda values=values:ui.download(
                            comparison_workbook(values,'Comparaison de projets'),'comparaison-projets.xlsx',MIME_XLSX)).props('outline')
                    ui.button('Afficher la comparaison',on_click=saved_plot.refresh); saved_plot()
        tabs.on_value_change(lambda:selected_panel.refresh())
        selected_panel()

@ui.page('/validite')
def validity_page():
    rows=material_db.evidence_rows('PP','outdoor')
    literature_report=pp_literature_only_benchmark(rows)
    report=pp_temporal_holdout(rows)
    iir_rows=material_db.evidence_rows('IIR','immersion')
    iir_temporal=iir_temporal_holdout(iir_rows)
    iir_temperature=iir_temperature_holdout(iir_rows)
    flax_report=flax_temperature_transfer_benchmark(
        material_db.observation_rows('FLAX_EPOXY',include_pending=True))
    with shell('/validite','Validité scientifique'):
        intro('Contrôle scientifique','Ce que Materia sait vraiment prédire',
              'Cette page compare les prédictions de Materia aux modules réellement publiés et sépare clairement la fenêtre vérifiée de l’extrapolation.')
        with ui.row().classes('w-full justify-end'):
            button('Comparer une prédiction figée','/validation-aveugle','fact_check').props('outline')
        with ui.element('div').classes('result-grid w-full mt-5'):
            for label,value,detail in [
                ('Erreur absolue moyenne',f"{number_fr(literature_report['mae_mpa'],1)} MPa",'Prédictions à 30 et 120 jours'),
                ('Erreur relative moyenne',f"{number_fr(literature_report['mape_pct'],2)} %",f"{literature_report['test_count']} prédictions hors formulation"),
                ('Bande empirique interne',f"± {number_fr(literature_report['empirical_half_width_pct'],1)} %",f"{number_fr(literature_report['empirical_coverage_pct'],0)} % des valeurs masquées couvertes"),
            ]:
                with ui.column().classes('result-stat gap-1'):
                    ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Cas de référence sans nouvelle expérience : PP H301').classes('section-title'); pill(literature_report['status'],'pill-teal')
            ui.label(literature_report['method']).classes('body-copy')
            ui.label(literature_report['protocol']+' · '+literature_report['independence']).classes('small')
            display_details=[{
                'formulation':row['formulation'],
                'time_days':int(row['time_days']),
                'observed_mpa':round(row['observed_mpa'],1),
                'predicted_mpa':round(row['predicted_mpa'],1),
                'absolute_error_mpa':round(row['absolute_error_mpa'],1),
                'relative_error_pct':round(row['relative_error_pct'],2),
                'covered':'Oui' if row['relative_error_pct']<=literature_report['empirical_half_width_pct']+1e-12 else 'Non',
            } for row in literature_report['details']]
            table_rows(display_details,['formulation','time_days','observed_mpa','predicted_mpa','absolute_error_mpa','relative_error_pct','covered'])
            ui.label(literature_report['conclusion']).classes('note w-full')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            with ui.row().classes('w-full justify-between items-center gap-3'):
                ui.label('Essai masqué n°2 : composite caoutchouc butyle IIR').classes('section-title')
                pill(iir_temporal['status'],'pill-teal')
            ui.label(iir_temporal['protocol']).classes('body-copy')
            with ui.element('div').classes('result-grid w-full'):
                for label,value,detail in [
                    ('Valeurs publiées','21','Tableau 1 vérifié · 80, 100 et 120 °C'),
                    ('Erreur moyenne',f"{number_fr(iir_temporal['mape_pct'],2)} %",f"MAE {number_fr(iir_temporal['mae_mpa'],2)} MPa"),
                    ('Bande interne 80 %',f"± {number_fr(iir_temporal['empirical_half_width_pct'],1)} %",f"Pire écart {number_fr(iir_temporal['max_relative_error_pct'],1)} %"),
                ]:
                    with ui.column().classes('result-stat gap-1'):
                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
            iir_details=[{
                'temperature_c':int(row['temperature_c']),'time_hours':round(row['time_hours'],1),
                'observed_mpa':round(row['observed_mpa'],2),'predicted_mpa':round(row['predicted_mpa'],2),
                'relative_error_pct':round(row['relative_error_pct'],2),
            } for row in iir_temporal['details']]
            with ui.expansion('Voir les 15 valeurs masquées',icon='table_view').classes('w-full'):
                table_rows(iir_details,['temperature_c','time_hours','observed_mpa','predicted_mpa','relative_error_pct'])
            ui.label(iir_temporal['conclusion']).classes('note w-full')
            ui.separator()
            with ui.row().classes('w-full justify-between items-center gap-3'):
                ui.label('Contrôle plus difficile : masquer toute la courbe à 100 °C').classes('font-medium')
                pill(iir_temperature['status'],'pill-amber')
            ui.label(f"L’interpolation depuis 80 et 120 °C donne {number_fr(iir_temperature['mape_pct'],2)} % d’erreur moyenne, jusqu’à {number_fr(iir_temperature['max_relative_error_pct'],2)} %. Le R² est {number_fr(iir_temperature['r2'],2)} : cette loi en température est donc rejetée.").classes('body-copy')
            ui.label('Décision logicielle : utiliser les courbes publiées exactes à 80, 100 ou 120 °C. Pour une température intermédiaire, afficher une alerte et ne pas promettre la bande ±10,9 %.').classes('pill pill-amber')
            ui.link('Source primaire IIR · DOI 10.3390/jcs3020048','https://www.mdpi.com/2504-477X/3/2/48',new_tab=True).classes('text-sm')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            with ui.row().classes('w-full justify-between items-center gap-3'):
                ui.label('Essai masqué n°3 : composite lin / époxy').classes('section-title')
                pill(flax_report['status'],'pill-teal')
            ui.label(flax_report['protocol']).classes('body-copy')
            with ui.element('div').classes('result-grid w-full'):
                for label,value,detail in [
                    ('Prédictions masquées',str(flax_report['test_count']),'Jours 1, 3, 9 et 38 · 20/40 °C'),
                    ('Erreur moyenne',f"{number_fr(flax_report['mape_pct'],2)} %",f"MAE {number_fr(flax_report['mae_mpa'],0)} MPa · R² {number_fr(flax_report['r2'],3)}"),
                    ('Bande empirique interne',f"± {number_fr(flax_report['empirical_half_width_pct'],1)} %",f"{number_fr(flax_report['empirical_coverage_pct'],0)} % des 8 valeurs couvertes"),
                ]:
                    with ui.column().classes('result-stat gap-1'):
                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
            flax_details=[{
                'temperature_c':int(row['temperature_c']),'time_days':int(row['time_days']),
                'observed_mpa':round(row['observed_mpa']), 'predicted_mpa':round(row['predicted_mpa']),
                'relative_error_pct':round(row['relative_error_pct'],2),
            } for row in flax_report['details']]
            table_rows(flax_details,['temperature_c','time_days','observed_mpa','predicted_mpa','relative_error_pct'])
            ui.label(flax_report['conclusion']).classes('note w-full')
            ui.label('Décision logicielle : ±11,4 % est une bande pilote raisonnable dans la fenêtre 0–38 jours pour ce composite exact. La numérisation de la figure (±3 %) et la variabilité entre lots restent des composantes distinctes.').classes('pill pill-teal')
            ui.link('Source primaire lin/époxy · DOI 10.1016/j.compositesb.2012.12.010','https://doi.org/10.1016/j.compositesb.2012.12.010',new_tab=True).classes('text-sm')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            ui.label('Contrôle complémentaire avec une mesure à 30 jours').classes('section-title')
            ui.label(report['method']+' · '+report['split']).classes('body-copy')
            ui.label(f"Lorsque E30 est disponible, l’erreur relative moyenne à 120 jours descend à {number_fr(report['mape_pct'],2)} %, avec une erreur maximale de {number_fr(report['empirical_half_width_pct'],2)} %. Cette méthode reste optionnelle.").classes('pill pill-teal')
        benchmark=report['benchmark']
        with ui.column().classes('panel w-full mt-5 gap-4'):
            ui.label('Comparer les lois avant de les utiliser').classes('section-title')
            ui.label('Toutes les méthodes utilisent seulement 0 et 30 jours pour la formulation testée. Le modèle en deux phases apprend le ralentissement sur les trois autres formulations.').classes('body-copy')
            ranking=[]
            for item in benchmark['ranking']:
                ranking.append({
                    'method':item['label'],'mae_mpa':round(item['mae_mpa'],1),
                    'mape_pct':round(item['mape_pct'],2),'r2':round(item['r2'],3) if item['r2'] is not None else None,
                    'max_relative_error_pct':round(item['max_relative_error_pct'],2),
                })
            table_rows(ranking,['method','mae_mpa','mape_pct','r2','max_relative_error_pct'])
            old=benchmark['methods']['exponential']; gain=(1-report['mape_pct']/old['mape_pct'])*100
            ui.label(f"La loi retenue réduit l’erreur relative moyenne de {number_fr(old['mape_pct'],1)} % à {number_fr(report['mape_pct'],2)} %, soit une baisse de {number_fr(gain,1)} %. Ce gain reste à confirmer sur une campagne indépendante.").classes('pill pill-teal')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            ui.label('Estimer le module à 120 jours avec une mesure à 30 jours').classes('section-title')
            ui.label('Cette estimation est plus précise que la projection depuis une fiche seule, car elle utilise la réponse précoce du grade réel.').classes('body-copy')
            with ui.row().classes('w-full gap-3 flex-wrap'):
                pp_e0=ui.number('Module initial (MPa)',value=600,min=.01).props('outlined').classes('grow min-w-48')
                pp_e30=ui.number('Module mesuré à 30 jours (MPa)',value=560,min=.01).props('outlined').classes('grow min-w-64')
            pp_prediction=ui.column().classes('w-full')
            def calculate_pp_short_term():
                pp_prediction.clear()
                try:
                    prediction=pp_short_term_prediction(float(pp_e0.value),float(pp_e30.value),rows)
                    with pp_prediction:
                        ui.label(f"Module moyen estimé à 120 jours : {number_fr(prediction['predicted_120_mpa'],1)} MPa").classes('section-title')
                        ui.label(f"Enveloppe empirique interne : {number_fr(prediction['lower_120_mpa'],1)} à {number_fr(prediction['upper_120_mpa'],1)} MPa · rétention {number_fr(prediction['retention_120_pct'],1)} %").classes('body-copy')
                        ui.label(prediction['status']+' · '+prediction['meaning']).classes('note w-full')
                except (ValueError,TypeError) as exc:
                    with pp_prediction: ui.label(str(exc)).classes('note w-full')
            ui.button('Calculer l’estimation à 120 jours',icon='calculate',on_click=calculate_pp_short_term).props('unelevated')
            calculate_pp_short_term()
        reference=report['external_reference']
        with ui.column().classes('panel w-full mt-5 gap-4'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('Publication indépendante qualifiée').classes('section-title'); pill(reference['decision'],'pill-amber')
            ui.label(reference['title']).classes('font-medium')
            ui.label(reference['scope']).classes('body-copy')
            ui.label(reference['reason']).classes('note w-full')
            ui.link('Consulter l’article · DOI '+reference['doi'],reference['url'],new_tab=True).classes('text-sm')
        with ui.element('div').classes('work-grid w-full mt-5'):
            with ui.column().classes('panel gap-3'):
                ui.icon('check_circle_outline',color='secondary',size='28px')
                ui.label('Ce qui est acquis').classes('section-title')
                ui.label('Quatre formulations PP, trois temps, moyenne, écart-type, n=7, protocole et source primaire vérifiés.').classes('body-copy')
                ui.label('Materia peut interpoler ces formulations entre 0 et 120 jours.').classes('pill pill-teal')
            with ui.column().classes('panel gap-3'):
                ui.icon('science',color='orange',size='28px')
                ui.label('Expérience prioritaire').classes('section-title')
                ui.label('Tester le grade cible à 0, 30, 60, 90 et 120 jours, avec au moins cinq éprouvettes par temps, puis réserver un lot complet à la validation finale.').classes('body-copy')
                button('Importer une campagne','/donnees','upload_file').props('outline')
        with ui.column().classes('panel w-full mt-5 gap-3'):
            ui.label('Failles scientifiques encore ouvertes').classes('section-title')
            ui.label('Ces limites empêchent encore de qualifier une durée de vie :').classes('body-copy')
            table_rows([
                {'priorite':'Critique','faille':'Validation externe absente','impact':'Les erreurs de 2,75 % sans mesure cible et de 0,77 % avec E30 restent internes à une seule publication.'},
                {'priorite':'Critique','faille':'Transfert de grade non démontré','impact':'Additifs, procédé, cristallinité et lot peuvent changer la cinétique.'},
                {'priorite':'Critique','faille':'Climat et Q10 non calibrés','impact':'Le passage température, humidité et UV reste une analyse de sensibilité.'},
                {'priorite':'Haute','faille':'Seulement trois temps','impact':'Le changement de mécanisme ou l’induction peuvent rester invisibles.'},
                {'priorite':'Haute','faille':'Valeurs brutes par éprouvette absentes','impact':'La couverture prédictive et la variabilité entre lots ne sont pas estimables.'},
                {'priorite':'Haute','faille':'Un seul indicateur mécanique','impact':'Le module peut rester stable alors que l’allongement ou la résistance chutent.'},
            ],['priorite','faille','impact'])
            ui.label('Règle appliquée : Materia resserre la bande uniquement après un contrôle hors formulation. Jusqu’à 120 jours, ±3,41 % vient des huit erreurs masquées ; au-delà, les vitesses tardives minimale et maximale élargissent progressivement les bornes.').classes('note w-full')
        with ui.column().classes('panel w-full mt-5 gap-3'):
            ui.label('Règle de publication').classes('section-title')
            ui.label('Materia ne passera au niveau « validé » qu’après une évaluation sur une campagne indépendante, compatible en formulation, protocole, géométrie et exposition. Une publication seulement contextuelle reste explicitement exclue des métriques.').classes('note w-full')


@ui.page('/validation-aveugle')
def blind_validation_page():
    with shell('/validite','Validation aveugle'):
        intro('Contrôle après essais','Comparer sans réécrire la prédiction',
              'Importez le fichier figé avant vos essais, puis les modules réellement mesurés. Materia vérifie l’empreinte avant de calculer les erreurs.')
        with ui.column().classes('panel w-full mt-5 gap-4'):
            ui.label('1. Prédiction figée').classes('section-title')
            frozen_text=ui.textarea('Contenu du fichier prediction-aveugle-materia.json').props('outlined autogrow').classes('w-full')
            ui.label('Le fichier est produit par le bouton « Figer avant essais » de la fiche matériau. Une seule modification invalide son empreinte.').classes('field-help')
            ui.label('2. Mesures réalisées après le gel').classes('section-title')
            with ui.row().classes('gap-3 flex-wrap'):
                ui.button('Télécharger le modèle Excel',icon='table_view',on_click=lambda:ui.download(
                    blind_validation_template_workbook(),'modele-validation-aveugle-materia.xlsx',MIME_XLSX)).props('outline')
            observations_text=ui.textarea('Mesures importées : temps, module, répétition, lot et éprouvette',
                value='time_days,modulus_mpa,replicate_id,lot_id,specimen_id\n0,1100,L1-T0-E1,L1,L1-T0-E1\n30,1060,L1-J30-E1,L1,L1-J30-E1\n60,1030,L1-J60-E1,L1,L1-J60-E1\n90,1010,L1-J90-E1,L1,L1-J90-E1\n120,990,L1-J120-E1,L1,L1-J120-E1').props('outlined autogrow').classes('w-full')
            async def upload_validation(e):
                try:
                    rows=await run.io_bound(parse_validation_file,await e.file.read(),e.file.name)
                    output=io.StringIO(); writer=csv.DictWriter(output,fieldnames=['time_days','modulus_mpa','replicate_id','lot_id','specimen_id']); writer.writeheader(); writer.writerows(rows)
                    observations_text.value=output.getvalue(); observations_text.update()
                    ui.notify(f"{len(rows)} mesure(s) chargée(s).",type='positive')
                except ValueError as exc: ui.notify(str(exc),type='negative')
                except Exception: logging.exception('Blind validation import failed'); ui.notify('Le fichier n’a pas pu être importé.',type='negative')
            ui.upload(label='Déposer les mesures CSV ou Excel',auto_upload=True,max_file_size=5_000_000,
                on_upload=upload_validation,on_rejected=lambda:ui.notify('Fichier refusé : CSV ou XLSX de 5 Mo maximum.',type='negative')).props('accept=.csv,.xlsx').classes('w-full')
            ui.label('Gardez chaque éprouvette sur une ligne et renseignez son lot. Materia donne le même poids à chaque temps, calcule la dispersion et signale les valeurs à vérifier sans les exclure.').classes('field-help')
            ui.label('Utilisez les mêmes unités, la même propriété et le même protocole que ceux annoncés dans la prédiction.').classes('field-help')
            comparison_output=ui.column().classes('w-full')

            def run_blind_comparison():
                comparison_output.clear()
                try:
                    snapshot=json.loads(frozen_text.value or '{}')
                    observations=parse_validation_file((observations_text.value or '').encode('utf-8'),'mesures.csv')
                    report=compare_with_experiment(snapshot,observations)
                    with comparison_output:
                        with ui.element('div').classes('result-grid w-full'):
                            for label,value,detail in [
                                ('Erreur relative moyenne',f"{number_fr(report['mape_pct'],2)} %",f"{report['distinct_timepoints']} temps · {report['observation_count']} mesures"),
                                ('Erreur absolue moyenne',f"{number_fr(report['mae_mpa'],2)} MPa",f"RMSE normalisée {number_fr(report['nrmse_pct'],2)} % · biais {number_fr(report['bias_mpa'],2)} MPa"),
                                ('Couverture de la bande',f"{number_fr(report['interval_coverage_pct'],1)} %",'Part des mesures entre les bornes figées'),
                            ]:
                                with ui.column().classes('result-stat gap-1'):
                                    ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                        validation=report['validation']
                        ui.label(validation['label']).classes('note w-full')
                        table_rows([
                                {'critere':'Nombre minimal de temps distincts','objectif':f"≥ {validation['targets']['minimum_points']}",'resultat':report['distinct_timepoints'],'statut':'Atteint' if validation['enough_points'] else 'Insuffisant'},
                            {'critere':'Erreur relative moyenne','objectif':f"≤ {validation['targets']['maximum_mape_pct']:g} %",'resultat':f"{number_fr(report['mape_pct'],2)} %",'statut':'Atteint' if report['mape_pct']<=validation['targets']['maximum_mape_pct'] else 'Dépassé'},
                            {'critere':'Biais absolu moyen','objectif':f"≤ {validation['targets']['maximum_absolute_bias_pct']:g} %",'resultat':f"{number_fr(report['absolute_bias_pct'],2)} %",'statut':'Atteint' if report['absolute_bias_pct']<=validation['targets']['maximum_absolute_bias_pct'] else 'Dépassé'},
                            {'critere':'Intervalle prédictif','objectif':'Couverture calibrée hors étude','resultat':f"{number_fr(report['interval_coverage_pct'],1)} %",'statut':'Évaluable' if validation['predictive_interval_evaluable'] else 'Non évaluable'},
                        ],['critere','objectif','resultat','statut'])
                        ui.label(validation['scope']).classes('field-help')
                        table_rows([{**row,'covered':'Oui' if row['covered'] else 'Non'} for row in report['details']],
                                   ['time_days','replicates','observed_mpa','observed_sd_mpa','predicted_mpa','lower_mpa','upper_mpa','relative_error_pct','covered'])
                        analysis=report['specimen_analysis']
                        with ui.expansion('Vue par lot et par éprouvette',icon='biotech',value=True).classes('w-full'):
                            with ui.column().classes('w-full gap-3 p-3'):
                                with ui.element('div').classes('stat-grid w-full'):
                                    for label,value,detail in [
                                        ('Lots',str(len(analysis['lots'])),f"{analysis['evaluated_groups']} groupe(s) évalué(s)"),
                                        ('Éprouvettes',str(report['observation_count']),'Toutes conservées dans le calcul'),
                                        ('À vérifier',str(analysis['flagged_count']),f"{analysis['unevaluated_groups']} groupe(s) trop petit(s)"),
                                    ]:
                                        with ui.column().classes('result-stat gap-1'):
                                            ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                                ui.label(analysis['policy']).classes('note w-full')
                                ui.label('Dispersion par lot et par temps').classes('font-medium')
                                table_rows([{**row,'mean_mpa':round(row['mean_mpa'],2),'sd_mpa':round(row['sd_mpa'],2),'cv_pct':round(row['cv_pct'],2),'median_mpa':round(row['median_mpa'],2),'minimum_mpa':round(row['minimum_mpa'],2),'maximum_mpa':round(row['maximum_mpa'],2)} for row in analysis['groups']],
                                           ['time_days','lot_id','specimens','mean_mpa','sd_mpa','cv_pct','median_mpa','minimum_mpa','maximum_mpa','outlier_candidates'])
                                ui.label('Valeurs brutes par éprouvette').classes('font-medium')
                                table_rows([{**row,'robust_z':'' if row['robust_z'] is None else round(row['robust_z'],2),'included_in_validation':'Oui' if row['included_in_validation'] else 'Non'} for row in analysis['observations']],
                                           ['time_days','lot_id','specimen_id','modulus_mpa','outlier_label','robust_z','outlier_reason','included_in_validation'])
                                ui.label(analysis['method']).classes('field-help')
                                lot_fig=go.Figure()
                                for lot in sorted({row['lot_id'] for row in analysis['observations']}):
                                    lot_rows=[row for row in analysis['observations'] if row['lot_id']==lot]
                                    lot_fig.add_trace(go.Scatter(x=[row['time_days'] for row in lot_rows],y=[row['modulus_mpa'] for row in lot_rows],
                                        mode='markers',marker=dict(size=9),name=lot,
                                        text=[row['specimen_id'] for row in lot_rows],hovertemplate='%{text}<br>%{x:g} j · %{y:.2f} MPa<extra></extra>'))
                                flagged=[row for row in analysis['observations'] if row['outlier_candidate']]
                                if flagged:
                                    lot_fig.add_trace(go.Scatter(x=[row['time_days'] for row in flagged],y=[row['modulus_mpa'] for row in flagged],
                                        mode='markers',marker=dict(size=15,symbol='x',color='#B42318',line=dict(width=2)),name='À vérifier',
                                        text=[row['specimen_id'] for row in flagged],hovertemplate='%{text}<br>Valeur à vérifier<extra></extra>'))
                                lot_fig.update_layout(template='plotly_white',height=330,margin=dict(l=55,r=25,t=30,b=50),
                                    xaxis_title='Temps réel d’exposition (jours)',yaxis_title='Module de Young (MPa)',legend=dict(orientation='h',y=1.15))
                                ui.plotly(lot_fig).classes('w-full')
                        times=[float(value)*365.25 for value in snapshot['time_years']]
                        fig=go.Figure()
                        fig.add_trace(go.Scatter(x=times,y=snapshot['upper_mpa'],mode='lines',line=dict(width=0),showlegend=False,hoverinfo='skip'))
                        fig.add_trace(go.Scatter(x=times,y=snapshot['lower_mpa'],mode='lines',line=dict(width=0),fill='tonexty',fillcolor='rgba(33,86,188,.12)',name='P10–P90 gelé'))
                        fig.add_trace(go.Scatter(x=times,y=snapshot['central_mpa'],mode='lines',line=dict(color='#235ABE',width=3),name='Prédiction P50 gelée'))
                        fig.add_trace(go.Scatter(x=[row['time_days'] for row in report['details']],y=[row['observed_mpa'] for row in report['details']],
                            error_y=dict(type='data',array=[row['observed_sd_mpa'] for row in report['details']],visible=True),
                            mode='markers',marker=dict(size=9,color='#F5A524',line=dict(color='#172033',width=1)),name='Mesures futures'))
                        fig.update_layout(template='plotly_white',height=390,margin=dict(l=55,r=25,t=35,b=50),hovermode='x unified',
                            xaxis_title='Temps réel d’exposition (jours)',yaxis_title='Module de Young (MPa)',legend=dict(orientation='h',y=1.15))
                        ui.plotly(fig).classes('w-full')
                        ui.label(report['interpretation']).classes('pill pill-teal')
                        with ui.row().classes('gap-3 flex-wrap'):
                            ui.button('Exporter le rapport Excel',icon='table_view',on_click=lambda:ui.download(
                                blind_validation_workbook(snapshot,report),'validation-aveugle-materia.xlsx',MIME_XLSX)).props('outline')
                            ui.button('Exporter les données JSON',icon='data_object',on_click=lambda:download_json(
                                report,'validation-aveugle-materia.json')).props('outline')
                except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
                    with comparison_output: ui.label(f'Comparaison impossible : {exc}').classes('note w-full')

            ui.button('Comparer aux mesures',icon='fact_check',on_click=run_blind_comparison).props('unelevated')

@ui.page('/projets')
def projects():
    with shell('/projets','Mes projets'):
        intro('Votre espace','Retrouvez le fil de vos explorations','Simulations conservées sur ce serveur, dans votre compte ou votre session invitée. Exportez vos fiches pour les transmettre ou les archiver.')
        saved=store.records(owner(),'simulation')
        if not saved:
            with ui.column().classes('panel w-full items-center gap-4 mt-6').style('padding:60px 20px'):
                ui.icon('folder_open',size='48px',color='primary'); ui.label('Votre première exploration commence ici.').classes('section-title'); ui.label('Enregistrez un résultat après avoir lancé une simulation.').classes('small'); button('Créer ma première simulation','/simuler','add')
        else:
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Exporter tous mes projets',icon='archive',on_click=lambda:download_json([
                    {'id':r['id'],'name':r['name'],'created':r['created'],'result':r['payload']} for r in saved
                ],'materia-mes-projets.json')).props('outline')
        for row in saved:
            with ui.column().classes('panel w-full gap-3 mt-4'):
                r=row['payload']; manifest=r.get('manifest',{}); d=manifest.get('inputs',{}); model=str(manifest.get('model',''))
                if model.startswith('datasheet-screening-'):
                    badge='Projection exploratoire'; badge_class='pill-teal' if manifest.get('evidence_level') in {'case_calibrated_short_term','calibrated_short_term'} else 'pill-amber'
                    horizon_label=f"{d.get('horizon_years',0):g} ans"
                else:
                    badge='Exercice synthétique'; badge_class='pill-amber'; horizon_label=f"{d.get('horizon',0):g} jours"
                with ui.row().classes('w-full justify-between'): ui.label(row['name']).classes('section-title'); pill(badge,badge_class)
                ui.label(f"{d.get('temperature',0):g} °C · {horizon_label} · seuil {d.get('threshold',0):g} % · enregistré le {row['created'][:10]}").classes('small')
                with ui.expansion('Consulter la projection',icon='show_chart').classes('w-full'):
                    ui.plotly(curve(r,d.get('e0',r['modulus'][0])*d.get('threshold',80)/100)).classes('w-full')
                    ui.label(f"Version conservée : {r['manifest']['model']}").classes('small p-3')
                with ui.row():
                    ui.button('Exporter la fiche',icon='download',on_click=lambda r=r:download_json(r,'materia-simulation.json')).props('outline')
                    ui.button('Rapport étudiant',icon='article',on_click=lambda r=r,row=row:ui.download(markdown_report(r,row['name']),'rapport-materia.md','text/markdown')).props('flat')
                    ui.button('Rapport PDF',icon='picture_as_pdf',on_click=lambda r=r,row=row:ui.download(
                        result_pdf(r,row['name']),'rapport-materia.pdf','application/pdf')).props('flat')
                    ui.button('Carte de preuve',icon='fact_check',on_click=lambda r=r,row=row:ui.download(
                        evidence_card_pdf(r,row['name']),'carte-preuve-materia.pdf','application/pdf')).props('flat')
                    ui.button('Exporter le classeur Excel',on_click=lambda r=r,row=row:ui.download(
                        result_workbook(r,row['name']),'materia-resultat.xlsx',MIME_XLSX)).props('flat')
                    if model.startswith('datasheet-screening-'):
                        ui.button('Plan d’expérience',icon='event_note',on_click=lambda r=r,row=row:ui.download(
                            experiment_plan_workbook(experiment_plan(r),r,'Plan d’expérience · '+row['name']),
                            'plan-experience-materia.xlsx',MIME_XLSX)).props('flat')
                    def duplicate_project(row=row):
                        store.clone(owner(),row['id']); ui.notify('Projet dupliqué.',type='positive'); ui.navigate.to('/projets')
                    ui.button('Dupliquer',icon='content_copy',on_click=duplicate_project).props('flat')
                    def ask_delete(row=row):
                        with ui.dialog() as dialog, ui.card().classes('gap-4'):
                            ui.label('Supprimer ce projet ?').classes('section-title')
                            ui.label(row['name']).classes('body-copy')
                            with ui.row().classes('justify-end w-full'):
                                ui.button('Annuler',on_click=dialog.close).props('flat')
                                def remove():
                                    store.delete(owner(),row['id']); dialog.close(); ui.navigate.to('/projets')
                                ui.button('Supprimer',icon='delete',on_click=remove).props('unelevated color=negative')
                        dialog.open()
                    ui.button('Supprimer',icon='delete_outline',on_click=ask_delete).props('flat color=negative')

@ui.page('/connexion')
def account_page():
    with shell('/connexion','Mon compte'):
        intro('Identité locale','Votre compte Materia',
              'Retrouvez vos projets et accédez à l’espace de votre classe depuis n’importe quel navigateur relié à ce serveur.')
        user=current_user()
        if user:
            with ui.column().classes('panel w-full mt-5 gap-4'):
                with ui.row().classes('items-center gap-4'):
                    initials=''.join(part[0] for part in user['display_name'].split()[:2]).upper() or 'MP'
                    ui.label(initials).classes('avatar')
                    with ui.column().classes('gap-0'):
                        ui.label(user['display_name']).classes('section-title')
                        ui.label('@'+user['username']+' · '+ROLE_LABELS[user['role']]).classes('small')
                ui.label('Vos projets, simulations, documents et activités de classe sont rattachés à ce compte local.').classes('body-copy')
                with ui.row().classes('gap-3'):
                    button('Ouvrir mes projets','/projets','folder_open')
                    button('Ouvrir ma classe','/classe','groups').props('outline')
                    ui.button('Se déconnecter',icon='logout',on_click=sign_out).props('flat color=negative')
            return

        ui.label('Les comptes sont enregistrés sur le serveur local de l’école. Un administrateur pourra ensuite remplacer cette connexion par le compte institutionnel.').classes('note w-full mt-5')
        with ui.tabs().classes('w-full min-w-0 mt-5') as tabs:
            login_tab=ui.tab('Se connecter',icon='login')
            register_tab=ui.tab('Créer un compte',icon='person_add')
        with ui.tab_panels(tabs,value=login_tab).classes('w-full bg-transparent'):
            with ui.tab_panel(login_tab).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Connexion').classes('section-title')
                    login_name=ui.input('Identifiant').props('outlined autocomplete=username').classes('w-full')
                    login_password=ui.input('Mot de passe',password=True,password_toggle_button=True).props('outlined autocomplete=current-password').classes('w-full')
                    def do_login():
                        user=auth.authenticate(login_name.value or '',login_password.value or '')
                        if not user:
                            ui.notify('Identifiant ou mot de passe incorrect.',type='negative'); return
                        guest=session_owner()
                        store.transfer_owner(guest,user['id'])
                        classroom.transfer_owner(guest,user['id'],include_teacher_content=user['role'] in {'teacher','admin'})
                        app.storage.user['user_id']=user['id']
                        ui.notify('Connexion réussie.',type='positive'); ui.navigate.to('/')
                    ui.button('Se connecter',icon='login',on_click=do_login).props('unelevated')
            with ui.tab_panel(register_tab).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Nouveau compte').classes('section-title')
                    display_name=ui.input('Nom affiché',placeholder='Prénom Nom').props('outlined autocomplete=name').classes('w-full')
                    username=ui.input('Identifiant',placeholder='prenom.nom').props('outlined autocomplete=username').classes('w-full')
                    roles={'student':'Étudiant'}
                    if auth.role_registration_available('teacher'):
                        roles['teacher']='Enseignant'
                    role=ui.select(roles,value='student',label='Profil').props('outlined').classes('w-full')
                    if 'teacher' in roles:
                        role_token=ui.input('Code enseignant',password=True,password_toggle_button=True).props('outlined autocomplete=off').classes('w-full')
                        role_token.bind_visibility_from(role,'value',lambda value:value=='teacher')
                    else:
                        role_token=None
                        ui.label('Les comptes enseignants sont créés avec un code fourni par l’administrateur du serveur.').classes('small')
                    password=ui.input('Mot de passe',password=True,password_toggle_button=True).props('outlined autocomplete=new-password').classes('w-full')
                    confirmation=ui.input('Confirmer le mot de passe',password=True,password_toggle_button=True).props('outlined autocomplete=new-password').classes('w-full')
                    ui.label('Au moins 10 caractères. L’identifiant accepte les lettres minuscules, chiffres, points, tirets et soulignements.').classes('small')
                    def do_register():
                        if (password.value or '') != (confirmation.value or ''):
                            ui.notify('Les deux mots de passe ne correspondent pas.',type='negative'); return
                        try:
                            user=auth.create_user(username.value or '',display_name.value or '',password.value or '',role.value or 'student',role_token.value if role_token else '')
                            guest=session_owner()
                            store.transfer_owner(guest,user['id'])
                            classroom.transfer_owner(guest,user['id'],include_teacher_content=user['role'] in {'teacher','admin'})
                            app.storage.user['user_id']=user['id']
                            ui.notify('Compte créé.',type='positive'); ui.navigate.to('/')
                        except (ValueError,PermissionError) as exc:
                            ui.notify(str(exc),type='negative')
                    ui.button('Créer mon compte',icon='person_add',on_click=do_register).props('unelevated')

@ui.page('/classe')
def classroom_space():
    with shell('/classe','Espace classe'):
        intro('Mode pilote local','Cours, consignes et remises',
              'Créez un espace de cours ou rejoignez celui d’un enseignant. Les simulations remises conservent leur modèle, leurs hypothèses et leur empreinte.')
        user=current_user()
        if not user:
            with ui.column().classes('panel w-full mt-5 items-center gap-4').style('padding:45px 20px'):
                ui.icon('lock',size='42px',color='primary')
                ui.label('Connectez-vous pour rejoindre votre classe').classes('section-title')
                ui.label('Votre compte conserve vos cours, vos consignes, vos remises et vos corrections.').classes('body-copy text-center')
                button('Se connecter ou créer un compte','/connexion','login')
            return
        own=user['id']
        is_teacher=user['role'] in {'teacher','admin'}
        ui.label(f"Compte {ROLE_LABELS[user['role']].lower()} · {user['display_name']}").classes('note w-full mt-5')
        with ui.tabs().classes('w-full min-w-0 mt-5') as tabs:
            overview=ui.tab('Mes cours',icon='groups')
            create=ui.tab('Créer un cours',icon='add_circle') if is_teacher else None
            join=ui.tab('Rejoindre un cours',icon='login')
        with ui.tab_panels(tabs,value=overview).classes('w-full bg-transparent'):
            with ui.tab_panel(overview).classes('p-0'):
                @ui.refreshable
                def course_dashboard():
                    courses=classroom.courses_for_owner(own)
                    if not courses:
                        with ui.column().classes('panel w-full mt-4 items-center gap-3').style('padding:45px 20px'):
                            ui.icon('groups',size='42px',color='primary'); ui.label('Aucun cours dans cette session').classes('section-title')
                            ui.label('Créez un cours en tant qu’enseignant ou saisissez le code transmis par votre établissement.').classes('small')
                        return
                    for course in courses:
                        assignments=classroom.assignments(course['id'])
                        with ui.column().classes('panel w-full mt-4 gap-4'):
                            with ui.row().classes('w-full justify-between items-start gap-3'):
                                with ui.column().classes('gap-1'):
                                    ui.label(course['title']).classes('section-title')
                                    ui.label(course['description'] or 'Aucune description.').classes('small')
                                pill('Enseignant' if course['role']=='teacher' else 'Étudiant','pill-teal' if course['role']=='teacher' else '')
                            if course['role']=='teacher':
                                with ui.row().classes('course-code items-center gap-3'):
                                    ui.icon('key',color='primary');
                                    with ui.column().classes('gap-0'):
                                        ui.label('Code à transmettre aux étudiants').classes('small')
                                        ui.label(course['code']).classes('course-code-value')
                                stats=classroom.course_stats(own,course['id'])
                                with ui.element('div').classes('result-grid w-full'):
                                    for label,value,detail in [
                                        ('Étudiants',str(stats['students']),'Inscrits au cours'),
                                        ('Remises',str(stats['submissions']),f"{stats['pending_review']} à corriger"),
                                        ('Moyenne',f"{number_fr(stats['average_grade'],1)} / 20" if stats['average_grade'] is not None else '—','Notes disponibles'),
                                    ]:
                                        with ui.column().classes('result-stat gap-1'):
                                            ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                                with ui.expansion('Créer un travail',icon='assignment_add').classes('w-full'):
                                    title=ui.input('Titre du travail').props('outlined').classes('w-full p-3')
                                    instructions=ui.textarea('Consigne et livrable attendu').props('outlined').classes('w-full px-3')
                                    pathway=ui.select({'estimation':'Projection depuis une fiche','published':'Analyse de mesures publiées'},value='estimation',label='Parcours demandé').props('outlined').classes('w-full px-3')
                                    due=ui.input('Date limite',placeholder='AAAA-MM-JJ').props('outlined').classes('w-full px-3')
                                    def add_assignment(course=course,title=title,instructions=instructions,pathway=pathway,due=due):
                                        try:
                                            classroom.create_assignment(own,course['id'],title.value or '',instructions.value or '',pathway.value,due.value or None)
                                            ui.notify('Travail publié.',type='positive'); course_dashboard.refresh()
                                        except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                                    ui.button('Publier le travail',icon='publish',on_click=add_assignment).props('unelevated').classes('m-3')
                                if assignments:
                                    ui.label('Travaux publiés').classes('font-bold')
                                    for assignment in assignments:
                                        with ui.column().classes('assignment-card gap-2'):
                                            with ui.row().classes('w-full justify-between'):
                                                ui.label(assignment['title']).classes('font-medium')
                                                ui.label(assignment['due_date'] or 'Sans date limite').classes('small')
                                            ui.label(assignment['instructions']).classes('body-copy')
                                            pathway_names={'estimation':'Fiche matériau','published':'Mesures publiées','guided':'Exercice guidé'}
                                            ui.label('Parcours : '+pathway_names[assignment['pathway']]).classes('pill')
                                            def duplicate_work(assignment=assignment):
                                                try:
                                                    classroom.duplicate_assignment(own,assignment['id'])
                                                    ui.notify('Travail dupliqué.',type='positive'); course_dashboard.refresh()
                                                except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                                            ui.button('Dupliquer ce travail',icon='content_copy',on_click=duplicate_work).props('flat dense')
                                try: handed=classroom.submissions(own,course['id'])
                                except PermissionError: handed=[]
                                with ui.expansion(f"Remises reçues ({len(handed)})",icon='inbox').classes('w-full'):
                                    if not handed: ui.label('Aucune remise pour le moment.').classes('small p-3')
                                    else:
                                        table_rows(handed,['display_name','assignment_title','simulation_name','status','grade','submitted'])
                                        for submission in handed:
                                            with ui.column().classes('review-card gap-3'):
                                                with ui.row().classes('w-full justify-between items-start gap-3'):
                                                    with ui.column().classes('gap-1'):
                                                        ui.label(submission['display_name']+' · '+submission['assignment_title']).classes('font-bold')
                                                        ui.label('Résultat : '+submission['simulation_name']).classes('small')
                                                    pill('Corrigé' if submission['status']=='reviewed' else 'À corriger','pill-teal' if submission['status']=='reviewed' else 'pill-amber')
                                                if submission['note']: ui.label('Commentaire étudiant : '+submission['note']).classes('body-copy')
                                                grade=ui.number('Note sur 20 (facultative)',value=submission['grade'],min=0,max=20,step=.5).props('outlined').classes('w-full')
                                                feedback=ui.textarea('Retour à l’étudiant',value=submission['feedback'] or '').props('outlined').classes('w-full')
                                                def review(submission=submission,grade=grade,feedback=feedback):
                                                    try:
                                                        classroom.review_submission(own,submission['id'],grade.value,feedback.value or '')
                                                        ui.notify('Correction enregistrée.',type='positive'); course_dashboard.refresh()
                                                    except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                                                ui.button('Enregistrer la correction',icon='rate_review',on_click=review).props('unelevated')
                                        ui.button('Exporter la liste JSON',icon='download',on_click=lambda handed=handed:download_json([{k:v for k,v in r.items() if k!='simulation_payload'} for r in handed],'remises-materia.json')).props('flat')
                                        ui.button('Exporter les notes Excel',icon='table_view',on_click=lambda handed=handed:ui.download(
                                            table_workbook([{k:v for k,v in row.items() if k!='simulation_payload'} for row in handed],
                                                           'Notes et remises Materia','Notes'),
                                            'notes-materia.xlsx',MIME_XLSX)).props('flat')
                            else:
                                simulations=store.records(own,'simulation')
                                try: student_handed={item['assignment_id']:item for item in classroom.student_submissions(own,course['id'])}
                                except PermissionError: student_handed={}
                                if not assignments: ui.label('L’enseignant n’a encore publié aucun travail.').classes('small')
                                for assignment in assignments:
                                    path_urls={'estimation':'/simuler/estimation','published':'/simuler/mesures','guided':'/simuler/apprendre'}
                                    with ui.column().classes('assignment-card gap-3'):
                                        with ui.row().classes('w-full justify-between items-start gap-3'):
                                            ui.label(assignment['title']).classes('font-bold')
                                            ui.label(assignment['due_date'] or 'Sans date limite').classes('small')
                                        ui.label(assignment['instructions']).classes('body-copy')
                                        button('Ouvrir le parcours demandé',path_urls[assignment['pathway']],'arrow_forward').props('outline')
                                        previous=student_handed.get(assignment['id'])
                                        if previous:
                                            with ui.column().classes('feedback-card gap-2'):
                                                with ui.row().classes('w-full justify-between items-center'):
                                                    ui.label('Votre remise').classes('font-bold')
                                                    pill('Corrigée' if previous['status']=='reviewed' else 'Remise','pill-teal' if previous['status']=='reviewed' else '')
                                                ui.label(previous['simulation_name']+' · '+previous['submitted'][:10]).classes('small')
                                                if previous['status']=='reviewed':
                                                    ui.label('Note : '+(f"{previous['grade']:g} / 20" if previous['grade'] is not None else 'non chiffrée')).classes('result-value')
                                                    ui.label(previous['feedback'] or 'Aucun commentaire.').classes('body-copy')
                                        if simulations:
                                            simulation=ui.select({r['id']:r['name'] for r in simulations},label='Simulation à remettre').props('outlined').classes('w-full')
                                            note=ui.textarea('Commentaire pour l’enseignant').props('outlined').classes('w-full')
                                            def submit_work(assignment=assignment,simulation=simulation,note=note,course=course):
                                                try:
                                                    classroom.submit(own,assignment['id'],simulation.value or '',course['display_name'],note.value or '')
                                                    ui.notify('Travail remis. Une nouvelle remise remplacera celle-ci.',type='positive'); course_dashboard.refresh()
                                                except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                                            ui.button('Remettre ce résultat',icon='send',on_click=submit_work).props('unelevated')
                                        else:
                                            ui.label('Enregistrez d’abord une simulation dans le parcours demandé.').classes('note w-full')
                course_dashboard()
            if create:
                with ui.tab_panel(create).classes('p-0'):
                    with ui.column().classes('panel w-full mt-4 gap-4'):
                        ui.label('Créer un espace enseignant').classes('section-title')
                        ui.label('Un code unique sera généré. Les étudiants l’utiliseront pour rejoindre le cours depuis leur compte.').classes('body-copy')
                        title=ui.input('Nom du cours',placeholder='Ex. MTX3A · Vieillissement des polymères').props('outlined').classes('w-full')
                        description=ui.textarea('Description et objectifs pédagogiques').props('outlined').classes('w-full')
                        def create_course():
                            try:
                                result=classroom.create_course(own,title.value or '',description.value or '',authorized_teacher=is_teacher)
                                ui.notify('Cours créé. Code : '+result['code'],type='positive'); course_dashboard.refresh(); tabs.value=overview
                            except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                        ui.button('Créer le cours',icon='add',on_click=create_course).props('unelevated')
            with ui.tab_panel(join).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Rejoindre un espace étudiant').classes('section-title')
                    code=ui.input('Code du cours',placeholder='Ex. A1B2C3').props('outlined').classes('w-full')
                    display_name=ui.input('Nom ou identifiant étudiant').props('outlined').classes('w-full')
                    def join_course():
                        try:
                            classroom.join_course(own,code.value or '',display_name.value or '')
                            ui.notify('Cours rejoint.',type='positive'); course_dashboard.refresh(); tabs.value=overview
                        except ValueError as exc: ui.notify(str(exc),type='negative')
                    ui.button('Rejoindre le cours',icon='login',on_click=join_course).props('unelevated')

@ui.page('/comprendre')
def learn():
    with shell('/comprendre','Comprendre'):
        intro('Le guide Materia','Les bons repères pour lire une courbe','Des explications courtes, puis les détails scientifiques lorsque vous en avez besoin.')
        lessons=[('01','Le module de Young','C’est une mesure de la rigidité dans le domaine élastique. Un module élevé signifie qu’une petite déformation demande davantage de contrainte.','E = contrainte / déformation, dans le domaine linéaire. Le protocole et la température de mesure doivent être comparables.'),('02','Vieillir ne signifie pas toujours ramollir','Le module peut diminuer, rester stable ou augmenter. Une rigidification ne prouve pas que le matériau résiste mieux à la rupture.','La perte relative 1 − E(t)/E₀ est un indicateur de rigidité. Il faut d’autres mesures, comme l’allongement à rupture, pour caractériser la fragilisation.'),('03','Un seuil, une question précise','Conserver 80 % de son module signifie perdre 20 % de sa rigidité initiale. Le seuil dépend de l’application.','Le temps critique est le premier instant où E(t) ≤ Ecrit. Un seuil non atteint pendant l’observation ne permet pas de conclure sur les temps ultérieurs.'),('04','Une enveloppe n’est pas une garantie','La zone ombrée montre ici les effets d’une variation supposée des paramètres. Elle n’est pas validée sur des mesures réelles.','Un intervalle de prédiction doit être évalué sur des données indépendantes. Sa couverture et sa largeur sont toutes deux importantes.'),('05','Interpoler et extrapoler','Interpoler reste entre des conditions observées. Extrapoler s’en éloigne et demande des preuves supplémentaires.','L’accélération thermique ne doit pas être appliquée sans vérifier la cohérence des mécanismes entre conditions accélérées et conditions de service.'),('06','Reconnaître une validation solide','Des résultats mesurés sur une autre expérience donnent une meilleure idée de la capacité de généralisation.','Les points d’une même courbe restent dans un même groupe. Préparation et sélection du modèle ne doivent pas utiliser le jeu de test final.')]
        for num,title,essential,detail in lessons:
            with ui.column().classes('panel w-full mt-4 gap-3'):
                ui.label(num+' / '+title).classes('section-title'); ui.label(essential).classes('body-copy')
                with ui.expansion('Approfondir',icon='functions').classes('w-full'): ui.label(detail).classes('body-copy p-4')
        with ui.column().classes('panel w-full mt-5 gap-3'):
            ui.label('À vous de jouer').classes('section-title'); ui.label('Un module passe de 2 000 MPa à 1 600 MPa. Quelle part est conservée ?').classes('body-copy')
            answer=ui.radio(['20 %','80 %','125 %']).props('inline')
            ui.button('Vérifier ma réponse',on_click=lambda:ui.notify('Exact : 1 600 / 2 000 = 80 %. La perte est de 20 %.' if answer.value=='80 %' else 'Divisez le module final par le module initial, puis multipliez par 100.',type='positive' if answer.value=='80 %' else 'info'))
        ui.link('NIST · Prédiction de durée de service et vieillissement accéléré','https://www.nist.gov/programs-projects/measurement-science-tools-accelerated-weathering-polymers-project',new_tab=True).classes('text-sm mt-6')

@ui.page('/donnees')
def datasets():
    own=owner()
    with shell('/donnees','Données et modèles'):
        intro('Traçabilité scientifique','De la donnée à la preuve','Importez des mesures, recherchez des publications et consultez les capacités réellement disponibles.')
        with ui.tabs().classes('w-full min-w-0 mt-5') as tabs:
            a=ui.tab('Mesures'); b=ui.tab('Littérature'); d=ui.tab('Revue scientifique'); c=ui.tab('Modèles et maturité')
        with ui.tab_panels(tabs,value=a).classes('w-full bg-transparent'):
            with ui.tab_panel(a).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Importer une série expérimentale').classes('section-title')
                    ui.label('CSV UTF-8 ou Excel .xlsx. Le format exige température, humidité relative, temps, épaisseur, E et E₀ ; Materia calcule E/E₀. Chaque mesure conserve son expérience, son protocole et sa source.').classes('body-copy')
                    out=io.StringIO(); w=csv.writer(out); w.writerow(REQUIRED)
                    for g,temp,rh,thickness in [('SYNTH-A',40,60,1.0),('SYNTH-B',60,75,1.5),('SYNTH-C',80,90,2.0)]:
                        for hours in [0,240,480,960]:
                            e0=2000; e=e0*np.exp(-hours*(0.00005+temp/4_000_000+rh/8_000_000)/thickness)
                            w.writerow([g,hours,'hours',round(e,3),'MPa',e0,'MPa',temp,rh,thickness,23,'SYNTHETIC-example','tensile','Données synthétiques pédagogiques',f'{g}, t={hours} h'])
                    with ui.row().classes('gap-3 flex-wrap'):
                        ui.button('Modèle Excel',icon='table_view',on_click=lambda:ui.download(
                            experiments.measurement_template_xlsx(),'modele-campagne-materia.xlsx',MIME_XLSX)).props('outline')
                        ui.button('Exemple CSV',icon='download',on_click=lambda:ui.download(out.getvalue().encode(),'exemple-synthetique.csv','text/csv')).props('outline')
                    async def upload(e):
                        try:
                            raw=await e.file.read(); rows=await run.io_bound(experiments.parse_measurement_file,raw,e.file.name)
                            quality=experiments.quality_report(rows)
                            store.save(own,'dataset',e.file.name,dict(rows=rows,quality=quality,status='pending',origin='user_import',note='Source déclarée par l’importateur, non vérifiée scientifiquement'))
                            ui.notify(f"{len(rows)} mesures importées. {quality['status']}.",type='positive' if quality['ready_for_review'] else 'warning'); imported.refresh()
                        except ValueError as exc: ui.notify(str(exc),type='negative')
                        except Exception: logging.exception('Import failed'); ui.notify('Le fichier n’a pas pu être importé.',type='negative')
                    ui.upload(label='Déposer un fichier CSV ou Excel',auto_upload=True,max_file_size=5_000_000,on_upload=upload,on_rejected=lambda:ui.notify('Fichier refusé : CSV ou XLSX de 5 Mo maximum.',type='negative')).props('accept=.csv,.xlsx').classes('w-full')
                    with ui.expansion('Ou coller des mesures au format CSV',icon='content_paste').classes('w-full'):
                        pasted=ui.textarea('Contenu CSV avec en-têtes',placeholder=','.join(REQUIRED)).props('outlined').classes('w-full p-3')
                        def import_paste():
                            try:
                                rows=parse_measurements((pasted.value or '').encode('utf-8'))
                                quality=experiments.quality_report(rows)
                                store.save(own,'dataset','Mesures collées',dict(rows=rows,quality=quality,status='pending',origin='user_import',note='Source déclarée, non vérifiée'))
                                ui.notify(f'{len(rows)} mesures importées.',type='positive'); imported.refresh()
                            except ValueError as exc: ui.notify(str(exc),type='negative')
                        ui.button('Importer ce CSV',icon='add',on_click=import_paste).props('outline').classes('m-3')
                @ui.refreshable
                def imported():
                    for record in store.records(own,'dataset'):
                        rows=record['payload']['rows']
                        quality=record['payload'].get('quality') or experiments.quality_report(rows)
                        with ui.column().classes('panel w-full gap-3 mt-4'):
                            ui.label(record['name']).classes('section-title'); pill(quality['status'],'pill-teal' if quality['ready_for_review'] else 'pill-amber')
                            ui.label(f"{len(rows)} mesures · {len({r['experiment_id'] for r in rows})} expérience(s) · unités normalisées").classes('small')
                            with ui.expansion('Contrôle qualité de la campagne',icon='rule').classes('w-full'):
                                table_rows(quality['details'],['experiment_id','points','distinct_times','start_days','end_days','has_t0','max_step_change_pct'])
                                if quality['flags']:
                                    for flag in quality['flags']: ui.label(flag['severity'].upper()+' · '+flag['message']).classes('note w-full')
                                else: ui.label('Aucun blocage automatique détecté. Une revue scientifique reste obligatoire.').classes('pill pill-teal m-3')
                            with ui.expansion('Examiner les mesures et leurs sources',icon='table_chart').classes('w-full'):
                                table_rows(rows,['experiment_id','time_hours','temperature_C','humidity_RH','thickness_mm','modulus_MPa','initial_modulus_MPa','residual_property','material','source','location'])
                            area=ui.column().classes('w-full')
                            with ui.expansion('Proposer ces mesures au corpus matériaux',icon='fact_check').classes('w-full'):
                                choices={m['id']:f"{m['name']} ({m['id']})" for m in material_db.catalog()}
                                target=ui.select(choices,label='Matériau réel correspondant').props('outlined').classes('w-full p-3')
                                source_url=ui.input('URL HTTPS de la publication ou du rapport source',placeholder='https://doi.org/…').props('outlined').classes('w-full px-3')
                                ui.label('Les mesures seront placées en attente. Elles ne pourront pas alimenter une prédiction avant une revue scientifique.').classes('small px-3')
                                def propose(rows=rows,target=target,source_url=source_url):
                                    try:
                                        result=material_db.propose_observations(target.value or '',rows,(source_url.value or '').strip())
                                        ui.notify(f"{result['inserted']} mesure(s) ajoutée(s), {result['duplicates']} doublon(s). Revue requise.",type='positive')
                                        imported.refresh()
                                    except ValueError as exc: ui.notify(str(exc),type='negative')
                                ui.button('Envoyer dans la file de validation',icon='playlist_add_check',on_click=propose).props('outline').classes('m-3')
                            async def calibrate(rows=rows,area=area,record=record):
                                area.clear()
                                try:
                                    fit=await run.io_bound(fit_measurements,rows)
                                    store.save(own,'calibration','Calibration · '+record['name'],dict(dataset_id=record['id'],fit=fit))
                                    with area:
                                        ui.label('Ajustement exploratoire exponentiel').classes('section-title')
                                        ui.label(f"Module initial ajusté : {number_fr(fit['e0'],1)} MPa · vitesse ajustée : {fit['rate']:.6g} jour⁻¹").classes('body-copy')
                                        ui.label('Aucune incertitude calibrée ni extrapolation de durée de vie. Les données importées restent non validées.').classes('note w-full')
                                        fig=base()
                                        for group in sorted({r['experiment_id'] for r in rows}):
                                            part=sorted([r for r in rows if r['experiment_id']==group],key=lambda r:r['time_days'])
                                            fig.add_trace(go.Scatter(x=[r['time_days'] for r in part],y=[r['modulus_MPa'] for r in part],mode='markers',name=group))
                                        times=np.linspace(min(r['time_days'] for r in rows),max(r['time_days'] for r in rows),100)
                                        fig.add_trace(go.Scatter(x=times.tolist(),y=(fit['e0']*np.exp(-fit['rate']*times)).tolist(),name='Ajustement exploratoire',mode='lines'))
                                        ui.plotly(fig).classes('w-full')
                                        if fit['holdout_mae_MPa'] is not None:
                                            ui.label(f"Contrôle exploratoire : erreur absolue moyenne {number_fr(fit['holdout_mae_MPa'],2)} MPa sur l’expérience réservée {fit['holdout']}. Le graphique montre ensuite l’ajustement sur toutes les données. Un seul découpage ne constitue pas une validation complète.").classes('small')
                                        else: ui.label('Pas de contrôle indépendant calculable : il faut plusieurs expériences avec assez de temps distincts dans l’apprentissage.').classes('small')
                                        ui.button('Exporter la calibration',on_click=lambda:download_json(fit,'calibration-exploratoire.json')).props('outline')
                                except ValueError as exc:
                                    with area: ui.label(str(exc)).classes('note')
                                except Exception:
                                    logging.exception('Calibration failed')
                                    with area: ui.label('La calibration n’a pas pu être calculée. Vérifiez les mesures.').classes('note')
                            ui.button('Ajuster un modèle exploratoire',icon='show_chart',on_click=calibrate).props('outline')
                            ml_area=ui.column().classes('w-full')
                            async def compare_ml(rows=rows,ml_area=ml_area,record=record):
                                ml_area.clear()
                                try:
                                    report=await run.io_bound(evaluate_baselines,rows)
                                    store.save(own,'calibration','Comparaison ML · '+record['name'],dict(dataset_id=record['id'],report=report))
                                    with ml_area:
                                        ui.label('Comparaison Machine Learning par expérience').classes('section-title')
                                        ui.label(f"{report['folds']} plis · {report['split']} · cible E/E₀").classes('small')
                                        table_rows(report['metrics'],['model','r2_mean','rmse_mean','mae_mean','train_r2_mean','overfit_gap'])
                                        ui.label('Influence des variables — '+report['importance_method']).classes('small')
                                        table_rows(report['importance'],['label','importance'])
                                        ui.label(report['limits']).classes('note w-full')
                                        ui.button('Exporter le rapport ML',on_click=lambda:download_json(report,'comparaison-ml.json')).props('outline')
                                except ValueError as exc:
                                    with ml_area: ui.label(str(exc)).classes('note')
                                except Exception:
                                    logging.exception('ML comparison failed')
                                    with ml_area: ui.label('La comparaison ML a échoué. Vérifiez le dataset.').classes('note')
                            ui.button('Comparer les modèles de Machine Learning',icon='model_training',on_click=compare_ml).props('unelevated')
                imported()
            with ui.tab_panel(b).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Rechercher dans la littérature').classes('section-title'); ui.label('Recherche de métadonnées Crossref. Les publications trouvées ne sont pas automatiquement des données utilisables pour prédire.').classes('body-copy')
                    query=ui.input('Mots-clés ou DOI',value='polymer aging Young modulus').props('outlined').classes('w-full')
                    results=ui.column().classes('w-full')
                    async def lookup():
                        search_button.disable(); results.clear()
                        with results: ui.spinner(size='25px'); ui.label('Recherche bibliographique en cours…').classes('small')
                        try:
                            found=await literature.search(query.value)
                            results.clear()
                            with results:
                                if not found: ui.label('Aucune publication trouvée. Essayez des mots-clés plus larges.').classes('small')
                                for item in found:
                                    with ui.column().classes('w-full row-line gap-2'):
                                        ui.label(item['title']).classes('font-medium text-base'); ui.label(f"{item['year']} · {item['doi']}").classes('small')
                                        with ui.row():
                                            ui.link('Ouvrir la publication',item['url'],new_tab=True).classes('text-sm')
                                            def keep(item=item):
                                                if any(r['payload'].get('doi')==item['doi'] for r in store.records(own,'publication')): ui.notify('Cette référence est déjà enregistrée.'); return
                                                store.save(own,'publication',item['title'],item); ui.notify('Référence enregistrée.',type='positive'); bibliography.refresh()
                                            ui.button('Conserver la référence',icon='bookmark_border',on_click=keep).props('flat dense')
                        except Exception:
                            results.clear()
                            with results: ui.label('La recherche est indisponible ou la requête invalide. Vérifiez votre connexion et réessayez.').classes('note')
                        finally: search_button.enable()
                    search_button=ui.button('Rechercher',icon='search',on_click=lookup).props('unelevated')
                    ui.label('Extraction IA des tableaux, OCR et numérisation de figures : non implémentés dans cette version. Aucune extraction automatique n’est annoncée comme validée.').classes('note w-full')
                @ui.refreshable
                def bibliography():
                    with ui.column().classes('panel w-full mt-4 gap-3'):
                        ui.label('Références conservées').classes('section-title')
                        refs=store.records(own,'publication')
                        if not refs: ui.label('Votre bibliographie est encore vide.').classes('small')
                        for row in refs:
                            ui.link(row['name'],row['payload']['url'],new_tab=True).classes('text-sm')
                        if refs: ui.button('Exporter la bibliographie',on_click=lambda:download_json([r['payload'] for r in refs],'bibliographie.json')).props('outline')
                bibliography()
            with ui.tab_panel(d).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-3'):
                    ui.label('Revue des expériences proposées').classes('section-title')
                    ui.label('Une décision porte sur une expérience complète. Vérifiez la publication, les conditions, les unités et la fidélité de l’extraction avant toute acceptation.').classes('body-copy')
                    ui.label('Cette zone est réservée au responsable scientifique. Les étudiants peuvent consulter les données, mais ne peuvent plus modifier leur statut.').classes('note w-full')
                    review_user=current_user()
                    if not review_user or review_user['role'] not in {'teacher','admin'}:
                        ui.label('Connectez-vous avec un compte enseignant ou administrateur pour accéder aux décisions de validation.').classes('small')
                        button('Ouvrir mon compte','/connexion','account_circle').props('outline')
                    elif reviewer_configured() and not reviewer_authorized():
                        review_token=ui.input('Code de validation scientifique',password=True,password_toggle_button=True).props('outlined autocomplete=off').classes('w-full')
                        def unlock_review():
                            expected=auth.server_token('MATERIA_REVIEW_TOKEN','.review_token')
                            user=current_user()
                            if user and user['role'] in {'teacher','admin'} and expected and secrets.compare_digest((review_token.value or '').strip(),expected):
                                app.storage.user['reviewer_authorized']=True
                                ui.notify('Espace de validation déverrouillé.',type='positive'); review_queue.refresh()
                            else: ui.notify('Code incorrect.',type='negative')
                        ui.button('Déverrouiller la revue',icon='lock_open',on_click=unlock_review).props('outline')
                    elif not reviewer_configured():
                        ui.label('Validation désactivée : l’administrateur doit définir MATERIA_REVIEW_TOKEN sur le serveur.').classes('small')
                    else:
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('verified_user',color='secondary'); ui.label('Session de validation autorisée').classes('small')
                @ui.refreshable
                def review_queue():
                    if not reviewer_authorized():
                        with ui.column().classes('panel w-full mt-4 gap-2'):
                            ui.icon('lock',size='28px',color='primary')
                            ui.label('File visible après autorisation').classes('section-title')
                            ui.label('La configuration locale protège désormais les décisions d’acceptation et de rejet.').classes('small')
                        return
                    batches=material_db.review_batches('pending')
                    if not batches:
                        with ui.column().classes('panel w-full mt-4 gap-2'):
                            ui.icon('task_alt',size='28px',color='secondary')
                            ui.label('Aucune expérience en attente').classes('section-title')
                            ui.label('Proposez d’abord un dataset depuis l’onglet Mesures.').classes('small')
                        return
                    for batch in batches:
                        with ui.column().classes('panel w-full mt-4 gap-3'):
                            with ui.row().classes('w-full items-center justify-between'):
                                ui.label(f"{batch['material_id']} · {batch['experiment_id']}").classes('section-title')
                                pill(f"{batch['observation_count']} points",'pill-amber')
                            ui.label(f"{batch['temperature_c']:g} °C · {batch['humidity_rh']:g} % HR · {batch['thickness_mm']:g} mm · {batch['distinct_times']} temps").classes('body-copy')
                            ui.link(batch['source_title'],batch['source_url'],new_tab=True).classes('text-sm')
                            ui.label('Premier emplacement déclaré : '+batch['first_location']).classes('small')
                            if batch['extraction_method']:
                                ui.label(f"Méthode : {batch['extraction_method']} · incertitude de lecture estimée : ±{batch['extraction_uncertainty_pct']:g} %").classes('note w-full')
                            rows=material_db.batch_rows(batch['source_id'],batch['experiment_id'])
                            with ui.expansion('Afficher les points',icon='table_chart').classes('w-full'):
                                table_rows(rows,['time_hours','temperature_C','humidity_RH','thickness_mm','modulus_MPa','initial_modulus_MPa','residual_property','location'])
                                ui.button('Exporter ce lot',icon='download',on_click=lambda rows=rows,batch=batch:download_json({'metadata':batch,'observations':rows},f"{batch['material_id']}-{batch['experiment_id']}.json")).props('flat')
                            with ui.expansion('Contrôler et décider',icon='fact_check').classes('w-full'):
                                reviewer=ui.input('Nom ou identifiant du relecteur').props('outlined').classes('w-full p-3')
                                checks={
                                    'source_verified':ui.checkbox('Publication ou rapport source ouvert et vérifié'),
                                    'conditions_verified':ui.checkbox('Température, humidité, épaisseur et temps vérifiés'),
                                    'units_verified':ui.checkbox('Unités et normalisation E/E₀ vérifiées'),
                                    'extraction_verified':ui.checkbox('Points comparés à la figure ou au tableau source'),
                                }
                                note=ui.textarea('Justification de la décision').props('outlined').classes('w-full px-3')
                                def decide(decision,batch=batch,reviewer=reviewer,checks=checks,note=note):
                                    try:
                                        count=material_db.review_batch(batch['source_id'],batch['experiment_id'],decision,
                                            reviewer.value or '',note.value or '',{k:v.value for k,v in checks.items()},
                                            authorized=reviewer_authorized())
                                        ui.notify(f'{count} observation(s) '+('acceptée(s).' if decision=='accepted' else 'rejetée(s).'),type='positive')
                                        review_queue.refresh()
                                    except (ValueError,PermissionError) as exc: ui.notify(str(exc),type='negative')
                                with ui.row().classes('p-3'):
                                    ui.button('Accepter l’expérience',icon='verified',on_click=lambda decide=decide:decide('accepted')).props('unelevated')
                                    ui.button('Rejeter',icon='block',on_click=lambda decide=decide:decide('rejected')).props('outline color=negative')
                review_queue()
            with ui.tab_panel(c).classes('p-0'):
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Diagnostic de maturité scientifique').classes('section-title')
                    ui.label('Ce diagnostic indique ce que Materia peut calculer aujourd’hui et l’expérience minimale à ajouter. Le seuil logiciel autorise une évaluation de modèles ; il ne prouve pas à lui seul une durée de vie.').classes('body-copy')
                    audit_options={m['id']:f"{m['name']} ({m['id']})" for m in material_db.catalog()}
                    audit_material=ui.select(audit_options,value='FLAX_EPOXY',label='Matériau à examiner').props('outlined use-input').classes('w-full')
                    audit_area=ui.column().classes('w-full')
                    def show_audit():
                        audit_area.clear(); audit=material_db.corpus_audit(audit_material.value)
                        with audit_area:
                            with ui.element('div').classes('result-grid w-full'):
                                for label,value,detail in [
                                    ('Points acceptés',f"{audit['accepted_points']} / {audit['minimum_gate']['points']}",f"Manquants : {audit['missing']['points']}"),
                                    ('Expériences',f"{audit['accepted_experiments']} / {audit['minimum_gate']['experiments']}",f"Manquantes : {audit['missing']['experiments']}"),
                                    ('Preuves publiées',str(audit['verified_published_values']),f"{audit['verified_published_series']} série(s)"),
                                ]:
                                    with ui.column().classes('result-stat gap-1'):
                                        ui.label(label).classes('stat-label'); ui.label(value).classes('result-value'); ui.label(detail).classes('small')
                            pill('Évaluation de modèles autorisée' if audit['trainable'] else 'Évaluation de modèles bloquée','pill-teal' if audit['trainable'] else 'pill-amber')
                            if audit['blockers']:
                                ui.label('Pourquoi le calcul est limité').classes('font-medium')
                                for item in audit['blockers']: ui.label('• '+item).classes('small')
                            ui.label('Prochaine campagne recommandée').classes('font-medium')
                            for item in audit['recommendations']: ui.label('• '+item).classes('small')
                            ui.label(audit['uncertainty']['note']).classes('note w-full')
                            if audit['candidate_sources']:
                                with ui.expansion(f"Sources candidates qualifiées ({len(audit['candidate_sources'])})",icon='science').classes('w-full'):
                                    for candidate in audit['candidate_sources']:
                                        with ui.column().classes('row-line w-full gap-2'):
                                            ui.link(candidate['source_title'],candidate['source_url'],new_tab=True).classes('font-medium text-primary no-underline')
                                            ui.label(f"DOI {candidate['source_doi']} · {candidate['target_property']} · {candidate['exposure']}").classes('small')
                                            ui.label(candidate['reason']).classes('body-copy')
                                            ui.label('Action : '+candidate['next_action']).classes('note w-full')
                    audit_material.on_value_change(lambda:show_audit())
                    show_audit()
                with ui.column().classes('panel w-full mt-4 gap-3'):
                    ui.label('Entraînement sur corpus accepté').classes('section-title')
                    accepted_materials=[m for m in material_db.catalog() if m['accepted_observations']]
                    if not accepted_materials:
                        ui.label('Aucune observation acceptée. La revue scientifique doit précéder tout entraînement sur un matériau réel.').classes('note w-full')
                    for mat in accepted_materials:
                        with ui.column().classes('row-line w-full gap-2'):
                            ui.label(f"{mat['name']} · {mat['accepted_observations']} points / {mat['accepted_experiments']} expériences").classes('font-medium')
                            if mat['accepted_observations']<12 or mat['accepted_experiments']<3:
                                ui.label('Corpus accepté pour la consultation, mais entraînement bloqué : minimum 12 points et 3 expériences indépendantes.').classes('note w-full')
                                continue
                            training_area=ui.column().classes('w-full')
                            async def train_accepted(mat=mat,training_area=training_area):
                                training_area.clear()
                                try:
                                    report=await run.io_bound(evaluate_baselines,material_db.accepted_rows(mat['id']))
                                    store.save(own,'calibration','Modèle accepté · '+mat['name'],dict(material_id=mat['id'],report=report,corpus='accepted_only'))
                                    with training_area:
                                        ui.label(f"Meilleur modèle en validation interne : {report['best_model']}").classes('section-title')
                                        table_rows(report['metrics'],['model','r2_mean','rmse_mean','mae_mean','train_r2_mean','overfit_gap'])
                                        ui.label(report['limits']).classes('note w-full')
                                except ValueError as exc:
                                    with training_area: ui.label(str(exc)).classes('note')
                            ui.button('Évaluer uniquement le corpus accepté',icon='model_training',on_click=train_accepted).props('outline')
                with ui.column().classes('panel w-full mt-4 gap-4'):
                    ui.label('Un prototype fonctionnel, une science à valider').classes('section-title')
                    table_rows([
                        dict(capacite='Simulation synthétique et sensibilité',etat='Implémenté',preuve='Tests numériques ; aucune validation matérielle'),
                        dict(capacite='Dataset hygrothermique conforme',etat='Implémenté',preuve='Température, HR, temps, épaisseur, E, E₀ et calcul E/E₀'),
                        dict(capacite='Baselines Machine Learning',etat='Implémenté',preuve='Ridge, Random Forest et boosting ; validation GroupKFold'),
                        dict(capacite='Métriques et interprétabilité',etat='Implémenté',preuve='R², RMSE, MAE, écart de surapprentissage et importance des variables'),
                        dict(capacite='Calibration exponentielle',etat='Exploratoire',preuve='Ajustement et contrôle par expérience si possible'),
                        dict(capacite='Recherche bibliographique',etat='Implémenté',preuve='Métadonnées Crossref uniquement'),
                        dict(capacite='Durée de vie réelle',etat='Non validé',preuve='Aucun corpus expérimental de référence'),
                        dict(capacite='PDF et recherche de passages',etat='Implémenté',preuve='Extraction texte par page ; contrôle humain nécessaire'),
                        dict(capacite='Catalogue de matériaux réels',etat='Implémenté',preuve='75 fiches classées ; 21 profils mécaniques recoupés'),
                        dict(capacite='Courbes issues des observations',etat='Exploratoire',preuve='Interpolation à conditions exactes ; aucune extrapolation'),
                        dict(capacite='Diagnostic de maturité',etat='Implémenté',preuve='Seuils, blocages, incertitude disponible et prochaine campagne explicités'),
                        dict(capacite='File de sources candidates',etat='Implémenté',preuve='Publications incompatibles ou à numériser isolées du corpus de calcul'),
                        dict(capacite='File de revue des mesures',etat='Implémenté',preuve='Rattachement matériau/source, statut en attente et dédoublonnage'),
                        dict(capacite='Extraction documentaire par IA',etat='À développer',preuve='Aucun service IA configuré'),
                        dict(capacite='Comptes et rôles',etat='Pilote local',preuve='Comptes étudiant/enseignant, mots de passe hachés et droits applicatifs ; SSO institutionnel à connecter'),
                        dict(capacite='PINN Fick/Arrhenius et multi-matériaux',etat='À développer',preuve='Nécessitent données réelles et validation indépendante'),
                        dict(capacite='30 utilisateurs et tests étudiants',etat='Sonde automatisée',preuve='Parcours HTTP simultanés en lecture ; test navigateur en classe toujours recommandé'),
                        dict(capacite='Rapport institutionnel PDF',etat='Implémenté',preuve='Résultats, courbe vectorielle, validité, source et incertitudes'),
                        dict(capacite='Sauvegarde quotidienne',etat='Implémenté',preuve='Archive vérifiée au démarrage, rétention de 14 jours'),
                        dict(capacite='Déploiement PostgreSQL / SSO',etat='À connecter',preuve='Diagnostic explicite ; SQLite et comptes locaux limités au pilote mono-serveur'),
                    ])
                    ui.label('Modèle pédagogique').classes('section-title'); ui.code('E(t) = E₀ × exp(−k(T) × t)\nk(T) = k_ref × exp[−Ea/R × (1/T − 1/T_ref)]\nT_ref = 333,15 K ; temps en jours\nEnveloppe : quantiles 5–95 % de 1 000 vitesses fictives\nGraine = 42 ; aucune couverture expérimentale mesurée',language='text').classes('w-full')
                    ui.label('Aucun utilisateur de cette version ne peut publier un modèle comme scientifiquement validé. Les fiches réelles organisent la collecte ; les trois modèles de démonstration restent synthétiques.').classes('note w-full')

@ui.page('/documents')
def document_library():
    from materia.document_ui import render
    with shell('/documents','Mes documents'):
        intro('Bibliothèque documentaire','Des sources que vous pouvez retrouver','Importez, explorez et conservez les passages utiles à votre recherche.')
        render(owner(),download_json)

@app.get('/health')
def health(): return {'status':'ok','version':__version__,'scientific_validation':False,'review_protection':reviewer_configured(),'local_accounts':True}

@app.get('/health/readiness')
def readiness():
    try:
        with store.connect() as conn: conn.execute('SELECT 1').fetchone()
        items=material_db.catalog()
        return {'status':'ready','database':True,'materials':len(items),
                'verified_reference_profiles':sum(item['verified_reference_properties'] for item in items),
                'accepted_observations':sum(item['accepted_observations'] for item in items),
                'verified_published_evidence':sum(item['verified_evidence_observations'] for item in items),
                'deployment':deployment.readiness_report()}
    except Exception:
        logging.exception('Readiness check failed')
        return {'status':'not_ready','database':False}

@app.get('/api/materials')
def materials_api():
    return {'count':len(material_db.catalog()),'materials':material_db.catalog(),
            'warning':'Les fiches documentaires et corpus acceptés limités ne constituent pas des modèles de durée de vie validés.'}

@app.get('/api/materials/{material_id}')
def material_api(material_id: str):
    item=material_db.material(material_id.upper())
    if not item: raise HTTPException(status_code=404,detail={'error':'Matériau inconnu','material_id':material_id})
    return {'material':item,'domain':material_db.domain_decision(item['id']),
            'reference_properties':material_db.reference_properties(item['id']),
            'scientific_audit':material_db.corpus_audit(item['id']),
            'accepted_observations':material_db.accepted_rows(item['id'])}

@app.get('/api/validation/pp')
def pp_validation_api():
    rows=material_db.evidence_rows('PP','outdoor')
    return {
        'literature_only':pp_literature_only_benchmark(rows),
        'measurement_assisted':pp_temporal_holdout(rows),
    }

@app.get('/api/validation/iir')
def iir_validation_api():
    rows=material_db.evidence_rows('IIR','immersion')
    return {
        'temporal_interpolation':iir_temporal_holdout(rows),
        'temperature_transfer':iir_temperature_holdout(rows),
    }

@app.get('/api/validation/flax-epoxy')
def flax_validation_api():
    rows=material_db.observation_rows('FLAX_EPOXY',include_pending=True)
    return {'temperature_transfer':flax_temperature_transfer_benchmark(rows)}

if __name__ in {'__main__','__mp_main__'}:
    teacher_token,teacher_created=auth.ensure_server_token('MATERIA_TEACHER_TOKEN','.teacher_token','ENS')
    review_token,review_created=auth.ensure_server_token('MATERIA_REVIEW_TOKEN','.review_token','REV')
    if teacher_created:
        print(f'Code enseignant initial : {teacher_token}')
    if review_created:
        print(f'Code de revue scientifique initial : {review_token}')
    auth.migrate()
    material_db.migrate()
    try: maintenance.create_daily_backup()
    except Exception: logging.exception('Daily backup failed')
    secret_file=ROOT/'data'/'.secret'; secret_file.parent.mkdir(exist_ok=True)
    if not secret_file.exists():
        secret_file.write_text(secrets.token_hex(32)); secret_file.chmod(0o600)
    ui.run(host=os.environ.get('MATERIA_HOST','127.0.0.1'),
           port=int(os.environ.get('MATERIA_PORT','8087')),
           title='Materia · Explorer la matière',favicon='🔬',
           storage_secret=secret_file.read_text().strip(),reload=False,
           show=os.environ.get('MATERIA_SHOW_BROWSER','0').lower() in {'1','true','yes'},
           language='fr')
