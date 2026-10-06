"""Document library UI, composed into the shared Python shell."""
import logging
from nicegui import ui,run
from materia import documents,store

def render(owner,download_json):
    documents.migrate_embedded_documents(owner)
    ui.label('Les PDF restent sur ce serveur. Les pages indiquent leur ordre dans le PDF, parfois différent de la pagination imprimée. Tableaux, figures et scans nécessitent une vérification manuelle.').classes('subtitle mb-5')
    with ui.tabs().classes('w-full min-w-0') as tabs:
        library_tab=ui.tab('Ma bibliothèque'); search_tab=ui.tab('Trouver un passage'); evidence_tab=ui.tab('Mes preuves et notes')
    with ui.tab_panels(tabs,value=library_tab).classes('w-full bg-transparent'):
        with ui.tab_panel(library_tab).classes('p-0'):
            with ui.column().classes('panel w-full mt-4 gap-4'):
                ui.label('Ajouter une publication').classes('section-title')
                reference=ui.input('Référence, titre ou DOI · obligatoire',placeholder='Auteur, année, titre…').props('outlined maxlength=500').classes('w-full')
                status=ui.column().classes('w-full')
                busy={'value':False}
                async def upload(e):
                    if busy['value']: ui.notify('Un document est déjà en cours de traitement.'); return
                    busy['value']=True; uploader.disable(); status.clear()
                    with status: ui.spinner(size='24px'); ui.label('Lecture du PDF et extraction des pages…').classes('small')
                    try:
                        raw=await e.file.read()
                        await run.io_bound(documents.import_pdf,owner,e.file.name,raw,reference.value or '')
                        status.clear()
                        with status: ui.label('Document enregistré. Vérifiez le texte extrait ci-dessous.').classes('pill pill-teal')
                        library.refresh()
                    except ValueError as exc:
                        status.clear()
                        with status: ui.label(str(exc)).classes('note')
                    except Exception:
                        logging.exception('PDF import failed'); status.clear()
                        with status: ui.label('Le document n’a pas pu être importé. Réessayez avec un autre PDF.').classes('note')
                    finally: busy['value']=False; uploader.enable()
                uploader=ui.upload(label='Importer un PDF · 8 Mo / 100 pages maximum',auto_upload=True,max_file_size=documents.MAX_BYTES,on_upload=upload,on_rejected=lambda:ui.notify('PDF de 8 Mo maximum.',type='negative')).props('accept=.pdf').classes('w-full')
                with ui.expansion('Ajouter un passage par copier-coller',icon='content_paste').classes('w-full'):
                    ui.label('Indiquez la référence ci-dessus et le numéro de page dans la source. Un passage collé reste une transcription déclarée.').classes('small p-3')
                    page=ui.number('Page dans la source',value=1,min=1,max=100000,precision=0).props('outlined').classes('w-full px-3')
                    content=ui.textarea('Passage original',placeholder='Collez ici le texte du document…').props('outlined maxlength=100000').classes('w-full p-3')
                    def paste():
                        try:
                            payload=documents.pasted_document(reference.value or '',content.value or '',int(page.value or 0))
                            store.save(owner,'document',reference.value,payload); library.refresh(); ui.notify('Passage enregistré, provenance à vérifier.',type='positive')
                        except ValueError as exc: ui.notify(str(exc),type='negative')
                    ui.button('Enregistrer ce passage',icon='add',on_click=paste).props('outline').classes('m-3')
            @ui.refreshable
            def library():
                docs=store.records(owner,'document')
                if not docs:
                    with ui.column().classes('panel w-full mt-4 gap-3'):
                        ui.icon('menu_book',color='primary',size='32px'); ui.label('Votre bibliothèque est prête à recevoir ses premières sources.').classes('section-title'); ui.label('Importez un PDF texte ou ajoutez un passage avec sa référence.').classes('small')
                for doc in docs:
                    p=doc['payload']
                    with ui.column().classes('panel w-full mt-4 gap-3'):
                        ui.label(doc['name']).classes('section-title')
                        ui.label('Texte extrait · à vérifier' if p['method']=='pypdf-text-v1' else 'Transcription déclarée · à vérifier').classes('pill pill-amber')
                        characters=f"{p['characters']:,}".replace(',', '\u202f')
                        ui.label(f"{p['page_count']} page(s) importée(s) · {characters} caractères · empreinte {p['sha256'][:12]}").classes('small')
                        if p['empty_pages']: ui.label('Pages sans texte extractible : '+', '.join(map(str,p['empty_pages']))+'. Un OCR ou une transcription est nécessaire ; aucune valeur n’a été inventée.').classes('note w-full')
                        with ui.expansion('Examiner le texte page par page',icon='description').classes('w-full'):
                            page_options={v['page']:f"Page {v['page']}" for v in p['pages']}
                            select=ui.select(page_options,value=p['pages'][0]['page'],label='Page de la source').props('outlined').classes('w-full p-3')
                            text=ui.textarea('Texte extrait, non corrigé',value=p['pages'][0]['text'] or '[Aucun texte extractible]').props('outlined readonly autogrow').classes('w-full p-3')
                            select.on_value_change(lambda e,p=p,text=text:text.set_value(next(v['text'] for v in p['pages'] if v['page']==e.value) or '[Aucun texte extractible]'))
                        with ui.row():
                            ui.button('Exporter le texte et les pages',icon='download',on_click=lambda p=p:download_json({k:v for k,v in p.items() if k!='original_base64'},'document-extrait.json')).props('outline')
                            if p.get('original_path') or p.get('original_base64'):
                                def download_original(p=p):
                                    try:
                                        raw=documents.original_pdf(owner,p)
                                        if raw: ui.download(raw,p['filename'],'application/pdf')
                                    except ValueError as exc: ui.notify(str(exc),type='negative')
                                ui.button('PDF original',on_click=download_original).props('flat')
                            def ask_delete(doc=doc):
                                with ui.dialog() as dialog, ui.card().classes('gap-4'):
                                    ui.label('Supprimer ce document ?').classes('section-title'); ui.label(doc['name']).classes('body-copy')
                                    with ui.row().classes('justify-end w-full'):
                                        ui.button('Annuler',on_click=dialog.close).props('flat')
                                        def remove(): documents.delete_document(owner,doc['id']); dialog.close(); library.refresh()
                                        ui.button('Supprimer',icon='delete',on_click=remove).props('unelevated color=negative')
                                dialog.open()
                            ui.button('Supprimer',icon='delete_outline',on_click=ask_delete).props('flat color=negative')
            library()
        with ui.tab_panel(search_tab).classes('p-0'):
            with ui.column().classes('panel w-full mt-4 gap-4'):
                ui.label('Retrouver une information, avec sa source').classes('section-title')
                ui.label('Recherche locale par mots-clés dans vos documents. Les résultats sont des extraits exacts du texte enregistré, pas des réponses générées par une IA.').classes('body-copy')
                query=ui.input('Termes à rechercher',placeholder='module température vieillissement').props('outlined maxlength=300').classes('w-full')
                hits_area=ui.column().classes('w-full')
                def search():
                    hits_area.clear()
                    try:
                        hits=documents.search_passages(store.records(owner,'document'),query.value or '')
                        with hits_area:
                            if not hits: ui.label('Aucun passage correspondant. Essayez un terme présent dans vos sources ou importez un document.').classes('note')
                            for hit in hits:
                                with ui.column().classes('panel w-full gap-3'):
                                    ui.label(f"{hit['reference']} · page {hit['page']}").classes('section-title')
                                    ui.label(hit['text']).classes('body-copy whitespace-pre-wrap')
                                    ui.label('Extrait du texte enregistré · provenance et contexte à vérifier').classes('small')
                                    note=ui.textarea('Votre note de lecture',placeholder='Ce que ce passage apporte à mon étude…').props('outlined maxlength=4000').classes('w-full')
                                    def keep(hit=hit,note=note):
                                        try:
                                            documents.keep_evidence(owner,hit,note.value or ''); evidence.refresh(); ui.notify('Passage et note conservés.',type='positive')
                                        except ValueError as exc: ui.notify(str(exc),type='negative')
                                    ui.button('Conserver comme preuve documentaire',icon='bookmark_border',on_click=keep).props('outline')
                    except ValueError as exc:
                        with hits_area: ui.label(str(exc)).classes('note')
                ui.button('Rechercher dans mes documents',icon='search',on_click=search).props('unelevated')
        with ui.tab_panel(evidence_tab).classes('p-0'):
            @ui.refreshable
            def evidence():
                records=store.records(owner,'evidence')
                ui.label('Une note de lecture ne constitue pas une validation scientifique des mesures. Les extraits conservent leur document, leur page et leur empreinte.').classes('note w-full mt-4')
                if not records: ui.label('Aucune preuve conservée. Recherchez un passage, puis ajoutez-le à vos notes.').classes('body-copy mt-4')
                for record in records:
                    p=record['payload']
                    with ui.column().classes('panel w-full mt-4 gap-3'):
                        ui.label(record['name']).classes('section-title'); ui.label(p['text']).classes('body-copy whitespace-pre-wrap')
                        if p['note']: ui.label('Ma note : '+p['note']).classes('text-base')
                        ui.label('Empreinte source : '+p['sha256'][:16]).classes('small')
                if records: ui.button('Exporter mes preuves et notes',icon='download',on_click=lambda:download_json([r['payload'] for r in records],'preuves-documentaires.json')).props('outline').classes('mt-4')
            evidence()
