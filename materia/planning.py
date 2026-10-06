"""Prospective experiment planning from a frozen Materia result."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import math

import numpy as np
import xlsxwriter


def _curve_days(result: dict) -> np.ndarray:
    manifest=result.get('manifest') or {}; model=str(manifest.get('model',''))
    factor=365.25 if model.startswith('datasheet-screening-') else 1.
    times=np.asarray(result.get('time') or [],dtype=float)*factor
    if len(times)<2 or abs(float(times[0]))>1e-9 or np.any(np.diff(times)<=0):
        raise ValueError('La projection doit contenir une courbe temporelle croissante partant de zéro.')
    return times


def _validated_series(result: dict, times: np.ndarray) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    try:
        center=np.asarray(result['modulus'],dtype=float)
        lower=np.asarray(result['lower'],dtype=float)
        upper=np.asarray(result['upper'],dtype=float)
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError('La projection ne contient pas les trois courbes nécessaires au plan.') from exc
    if not (len(center)==len(lower)==len(upper)==len(times)):
        raise ValueError('Les courbes de la projection n’ont pas la même longueur.')
    if not all(np.all(np.isfinite(values)) for values in (center,lower,upper)):
        raise ValueError('La projection contient une valeur non finie.')
    if np.any(center<=0) or np.any(lower<0) or np.any(upper<=0) or np.any(lower>center) or np.any(center>upper):
        raise ValueError('Les bornes de la projection sont incohérentes.')
    return center,lower,upper


def _crossing_day(result: dict) -> float | None:
    manifest=result.get('manifest') or {}; model=str(manifest.get('model',''))
    value=result.get('crossing_estimate_years') if model.startswith('datasheet-screening-') else result.get('crossing')
    if value is None:
        return None
    return float(value)*(365.25 if model.startswith('datasheet-screening-') else 1.)


def _unique_times(values: list[float], horizon: float) -> list[float]:
    cleaned=[]
    for value in values:
        value=float(np.clip(value,0,horizon))
        if not any(abs(value-existing)<=max(1e-6,horizon*1e-4) for existing in cleaned):
            cleaned.append(value)
    return cleaned


def experiment_plan(result: dict, timepoints: int=5, replicates: int=5, lots: int=3) -> dict:
    """Select informative prospective measurement times without claiming a precision gain."""
    if not 5<=int(timepoints)<=10:
        raise ValueError('Le plan doit comporter entre 5 et 10 temps distincts.')
    if not 3<=int(replicates)<=20:
        raise ValueError('Prévoyez entre 3 et 20 éprouvettes par lot et par temps.')
    if not 1<=int(lots)<=8:
        raise ValueError('Prévoyez entre 1 et 8 lots indépendants.')
    timepoints=int(timepoints); replicates=int(replicates); lots=int(lots)
    times=_curve_days(result); center,lower,upper=_validated_series(result,times)
    horizon=float(times[-1]); manifest=result.get('manifest') or {}; assumptions=manifest.get('assumptions') or {}
    evidence_window=float(assumptions.get('evidence_window_days') or 0)
    evidence_window=min(evidence_window,horizon) if evidence_window>0 else 0.
    crossing=_crossing_day(result)
    if crossing is not None and not 0<crossing<=horizon:
        crossing=None

    grid=np.linspace(0,horizon,241)
    grid_center=np.interp(grid,times,center); grid_lower=np.interp(grid,times,lower); grid_upper=np.interp(grid,times,upper)
    relative_width=(grid_upper-grid_lower)/np.maximum(grid_center,1e-12)
    slope=np.abs(np.gradient(grid_center,grid))/max(float(center[0]),1e-12)
    width_norm=relative_width/max(float(np.max(relative_width)),1e-12)
    slope_norm=slope/max(float(np.max(slope)),1e-12)
    coverage=np.sqrt(np.divide(grid,horizon,out=np.zeros_like(grid),where=horizon>0))
    information=.5*width_norm+.3*slope_norm+.2*coverage

    first_window=evidence_window or horizon
    if not evidence_window or horizon<=evidence_window+1e-9:
        # Inside a documented window, evenly spaced points avoid a cluster at
        # the widest end of the band and make changes of slope visible.
        anchors=list(np.linspace(0,horizon,timepoints))
    else:
        anchors=[0.,min(first_window*.25,horizon*.25),evidence_window]
        if crossing is not None:
            anchors.append(crossing)
        anchors.append(horizon)
    selected=_unique_times(anchors,horizon)

    minimum_spacing=max(horizon/max(timepoints-1,1)*.55,1.)
    candidates=sorted(zip(information,grid),reverse=True)
    for _,candidate in candidates:
        if len(selected)>=timepoints:
            break
        if candidate<=0 or any(abs(candidate-existing)<minimum_spacing for existing in selected):
            continue
        selected.append(float(candidate))
    if len(selected)<timepoints:
        for candidate in np.linspace(0,horizon,timepoints):
            if len(selected)>=timepoints:
                break
            if not any(abs(candidate-existing)<=1e-6 for existing in selected):
                selected.append(float(candidate))
    # A very small requested plan may contain more scientific anchors than its
    # nominal size. Keep baseline, final horizon, evidence boundary and threshold
    # before ranking the remaining candidates.
    if len(selected)>timepoints:
        protected={0.,horizon}
        if evidence_window: protected.add(evidence_window)
        if crossing is not None: protected.add(crossing)
        kept=[value for value in selected if any(abs(value-item)<=1e-6 for item in protected)]
        others=sorted((value for value in selected if value not in kept),
                      key=lambda value:float(np.interp(value,grid,information)),reverse=True)
        selected=(kept+others)[:timepoints]
    selected=sorted(selected)

    rows=[]
    for day in selected:
        is_zero=abs(day)<1e-8; is_final=abs(day-horizon)<max(1e-6,horizon*1e-4)
        is_boundary=bool(evidence_window and abs(day-evidence_window)<max(1e-6,horizon*1e-4))
        is_crossing=bool(crossing is not None and abs(day-crossing)<max(1e-6,horizon*1e-4))
        if is_zero:
            role='Référence initiale'; priority='Obligatoire'
        elif is_final:
            role='Vérifier la valeur à l’horizon cible'; priority='Obligatoire'
        elif is_crossing:
            role='Vérifier le franchissement du seuil'; priority='Obligatoire'
        elif is_boundary:
            role='Ancrer la fin de la fenêtre documentaire'; priority='Haute'
        elif day<=first_window:
            role='Mesurer l’évolution précoce'; priority='Haute'
        else:
            role='Réduire l’incertitude d’extrapolation'; priority='Haute'
        phase=('Phase 1 · ancrage court terme' if not evidence_window or day<=evidence_window+1e-9
               else 'Phase 2 · validation prolongée')
        if is_final and horizon>evidence_window>0:
            phase='Phase 3 · horizon cible'
        score=0 if is_zero else int(round(float(np.interp(day,grid,information))*100))
        day_label=(f'{day:.1f}'.rstrip('0').rstrip('.')+' jours') if day<365.25 else f'{day/365.25:.2f} ans'
        rows.append({
            'phase':phase,'time_days':round(day,2),'time_label':day_label,
            'priority':priority,'role':role,'information_score':score,
            'predicted_mpa':round(float(np.interp(day,times,center)),2),
            'lower_mpa':round(float(np.interp(day,times,lower)),2),
            'upper_mpa':round(float(np.interp(day,times,upper)),2),
            'replicates_per_lot':replicates,'lots':lots,
        })
    material=manifest.get('material_name') or manifest.get('material_id') or manifest.get('experiment_id') or 'Matériau à préciser'
    protocol=(manifest.get('validity') or {}).get('protocol') or 'Conserver le même protocole de traction pour tous les temps.'
    return {
        'format':'materia-experiment-plan-v1','created_at':datetime.now(timezone.utc).isoformat(),
        'material':material,'target_property':manifest.get('target_property') or 'Module de Young',
        'model':manifest.get('model'),'result_fingerprint':result.get('fingerprint'),
        'timepoints':len(rows),'replicates_per_lot':replicates,'lots':lots,
        'total_specimens':len(rows)*replicates*lots,'reserved_validation_lots':1 if lots>=2 else 0,
        'horizon_days':horizon,'evidence_window_days':evidence_window or None,
        'rows':rows,
        'method':('Les temps obligatoires couvrent t=0, la fin du domaine documentaire, le franchissement central du seuil lorsqu’il est dans l’horizon et le terme final. '
                  'Les temps restants maximisent un score heuristique combinant largeur de bande, pente de la courbe et couverture temporelle.'),
        'score_warning':'Le score d’information classe les temps ; il ne prédit pas un pourcentage de réduction de l’incertitude.',
        'laboratory_rules':[
            f'Utiliser {replicates} éprouvettes indépendantes par lot et par temps.',
            f'Employer {lots} lot(s) ; conserver le dernier lot fermé jusqu’à l’analyse aveugle.' if lots>=2 else 'Ajouter au moins un second lot pour évaluer la généralisation.',
            'Randomiser l’ordre des éprouvettes et conserver chaque valeur brute avec son identifiant.',
            'Conserver formulation, procédé, géométrie, exposition et protocole identiques entre les temps.',
            'Figer la prédiction et son empreinte avant d’ouvrir les résultats du lot réservé.',
        ],
        'protocol':protocol,
    }


def experiment_plan_workbook(plan: dict, result: dict, title: str='Plan d’expérience Materia') -> bytes:
    """Create a laboratory-ready workbook and an import sheet for blind validation."""
    output=BytesIO(); workbook=xlsxwriter.Workbook(output,{'in_memory':True})
    workbook.set_properties({'title':title,'author':'Materia','comments':'Plan prospectif généré avant essais'})
    blue='#235ABE'; teal='#13958B'; ink='#172033'; pale='#F3F6FB'; amber='#FFF3D6'
    title_fmt=workbook.add_format({'bold':True,'font_size':16,'font_color':ink})
    subtitle=workbook.add_format({'font_size':9,'font_color':'#5F6B7A','italic':True})
    section=workbook.add_format({'bold':True,'font_color':'#FFFFFF','bg_color':blue})
    header=workbook.add_format({'bold':True,'font_color':'#FFFFFF','bg_color':teal,'text_wrap':True,'align':'center','valign':'vcenter','border':1,'border_color':'#FFFFFF'})
    label=workbook.add_format({'bold':True,'font_color':ink,'bg_color':pale,'text_wrap':True,'valign':'top'})
    value=workbook.add_format({'font_color':ink,'text_wrap':True,'valign':'top'})
    number=workbook.add_format({'font_color':ink,'num_format':'0.00'})
    warning=workbook.add_format({'font_color':'#7A4E00','bg_color':amber,'text_wrap':True})
    blank_input=workbook.add_format({'bg_color':'#FFFBEA','border':1,'border_color':'#E2C66D','num_format':'0.00'})

    summary=workbook.add_worksheet('Plan de campagne'); schedule=workbook.add_worksheet('Éprouvettes')
    validation=workbook.add_worksheet('Import validation'); method=workbook.add_worksheet('Méthode et traçabilité')
    for sheet in (summary,schedule,validation,method):
        sheet.hide_gridlines(2); sheet.freeze_panes(4,0); sheet.set_margins(.4,.4,.5,.5)
    summary.set_column('A:A',25); summary.set_column('B:G',22)
    summary.write('A1',title,title_fmt); summary.write('A2','Plan généré avant essais ; les valeurs prédites ne doivent pas être ajustées après ouverture du lot réservé.',subtitle)
    summary.write_row('A4',['Matériau','Propriété','Temps','Lots','Éprouvettes / lot / temps','Total éprouvettes'],header)
    summary.write_row('A5',[plan['material'],plan['target_property'],plan['timepoints'],plan['lots'],plan['replicates_per_lot'],plan['total_specimens']],value)
    summary.write('A7','Temps de mesure proposés',section)
    headers=['Phase','Temps (jours)','Priorité','Rôle','Score informatif / 100','Prévision (MPa)','Borne basse (MPa)','Borne haute (MPa)']
    summary.write_row(7,0,headers,header)
    for index,row in enumerate(plan['rows'],8):
        summary.write_row(index,0,[row['phase'],row['time_days'],row['priority'],row['role'],row['information_score'],row['predicted_mpa'],row['lower_mpa'],row['upper_mpa']],value)
        for col in (1,4,5,6,7): summary.write_number(index,col,float([row['time_days'],row['information_score'],row['predicted_mpa'],row['lower_mpa'],row['upper_mpa']][(1,4,5,6,7).index(col)]),number)
    summary.add_table(7,0,7+len(plan['rows']),7,{'name':'PlanMateria','style':'Table Style Medium 4','columns':[{'header':h} for h in headers]})
    chart=workbook.add_chart({'type':'scatter','subtype':'straight_with_markers'})
    for name,col,color,dash in [('Prévision',5,blue,'solid'),('Borne basse',6,'#91A3BF','dash'),('Borne haute',7,teal,'dash')]:
        chart.add_series({'name':name,'categories':['Plan de campagne',8,1,7+len(plan['rows']),1],
                          'values':['Plan de campagne',8,col,7+len(plan['rows']),col],
                          'line':{'color':color,'width':2 if col==5 else 1.25,'dash_type':dash},
                          'marker':{'type':'circle','size':5,'border':{'color':color},'fill':{'color':color}}})
    chart.set_title({'name':'Mesures proposées sur la projection figée'}); chart.set_x_axis({'name':'Temps (jours)'})
    chart.set_y_axis({'name':'Module de Young (MPa)','min':0}); chart.set_legend({'position':'top'}); chart.set_size({'width':760,'height':380})
    summary.insert_chart(15+len(plan['rows']),0,chart)

    schedule.set_column('A:A',24); schedule.set_column('B:C',20); schedule.set_column('D:F',16); schedule.set_column('G:J',22)
    schedule.write('A1','Éprouvettes et saisie laboratoire',title_fmt)
    schedule.write('A2','Une ligne par éprouvette. Les cellules jaunes sont à remplir après la mesure.',subtitle)
    schedule_headers=['Identifiant éprouvette','Rôle du lot','Phase','Temps (jours)','Lot','Répétition','Module mesuré (MPa)','Date de mesure','Opérateur','Observation']
    schedule.write_row(3,0,schedule_headers,header); specimen_row=4
    validation_rows=[]
    for plan_row in plan['rows']:
        day=float(plan_row['time_days']); day_id=(f'{day:g}').replace('.','p')
        for lot in range(1,plan['lots']+1):
            lot_role='Validation aveugle réservée' if plan['reserved_validation_lots'] and lot==plan['lots'] else 'Répétabilité / calibration'
            for replicate in range(1,plan['replicates_per_lot']+1):
                specimen=f'L{lot}-J{day_id}-E{replicate}'
                schedule.write_row(specimen_row,0,[specimen,lot_role,plan_row['phase'],day,lot,replicate],value)
                for col in range(6,10): schedule.write_blank(specimen_row,col,None,blank_input)
                validation_rows.append((day,specimen)); specimen_row+=1
    schedule.add_table(3,0,specimen_row-1,9,{'name':'EprouvettesMateria','style':'Table Style Medium 2','columns':[{'header':h} for h in schedule_headers]})

    validation.set_column('A:E',22); validation.write('A1','Import direct dans Validation aveugle',title_fmt)
    validation.write('A2','Renseignez uniquement la colonne modulus_mpa, puis importez cette feuille enregistrée en .xlsx.',subtitle)
    validation.write_row(3,0,['time_days','modulus_mpa','replicate_id','lot_id','specimen_id'],header)
    for row_index,(day,specimen) in enumerate(validation_rows,4):
        lot=specimen.split('-',1)[0]
        validation.write_number(row_index,0,day,number); validation.write_blank(row_index,1,None,blank_input)
        validation.write_row(row_index,2,[specimen,lot,specimen],value)
    validation.add_table(3,0,3+len(validation_rows),4,{'name':'ValidationMateria','style':'Table Style Medium 4','columns':[{'header':h} for h in ['time_days','modulus_mpa','replicate_id','lot_id','specimen_id']]})

    method.set_column('A:A',30); method.set_column('B:F',25); method.write('A1','Méthode et traçabilité',title_fmt)
    method.write('A3','Élément',header); method.write('B3','Valeur',header)
    method_rows=[('Méthode de sélection',plan['method']),('Limite du score',plan['score_warning']),('Protocole',plan['protocol']),
                 ('Empreinte du résultat',plan.get('result_fingerprint') or 'Non renseignée'),('Modèle',plan.get('model') or 'Non renseigné'),
                 ('Date UTC',plan['created_at'])]
    method_rows += [(f'Règle laboratoire {index}',rule) for index,rule in enumerate(plan['laboratory_rules'],1)]
    for index,(key,text) in enumerate(method_rows,4):
        method.write(index,0,key,label); method.merge_range(index,1,index,5,text,warning if 'Limite' in key else value); method.set_row(index,35)
    workbook.close(); return output.getvalue()
