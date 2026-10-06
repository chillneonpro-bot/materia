"""Institutional PDF report with a vector result curve."""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import textwrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from materia.modeling import curve_value_origin
from materia.validation import validity_diagnostic


BLUE=colors.HexColor('#235ABE'); TEAL=colors.HexColor('#13958B'); INK=colors.HexColor('#172033')
MUTED=colors.HexColor('#5F6B7A'); PALE=colors.HexColor('#F3F6FB'); AMBER=colors.HexColor('#FFF3D6')


def _pdf_safe(value):
    return (str(value).replace('\u2011','-').replace('\u2013','-').replace('\u2014','-')
            .replace('\u2019',"'").replace('\u202f',' ').replace('\u00a0',' '))


def _text(pdf, text, x, y, width, *, size=9, color=INK, bold=False, leading=None):
    font='Helvetica-Bold' if bold else 'Helvetica'; leading=leading or size*1.35
    pdf.setFont(font,size); pdf.setFillColor(color)
    max_chars=max(12,int(width/(size*.52)))
    lines=[]
    for paragraph in _pdf_safe(text).splitlines() or ['']:
        lines.extend(textwrap.wrap(paragraph,width=max_chars,break_long_words=False) or [''])
    for line in lines:
        pdf.drawString(x,y,line[:300]); y-=leading
    return y


def _section(pdf, title, y):
    pdf.setFillColor(BLUE); pdf.roundRect(38,y-16,519,22,3,fill=1,stroke=0)
    pdf.setFillColor(colors.white); pdf.setFont('Helvetica-Bold',10); pdf.drawString(46,y-10,_pdf_safe(title))
    return y-30


def _footer(pdf, page, total=2):
    pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7)
    pdf.drawString(38,30,"Materia - rapport pédagogique, pas de qualification industrielle sans validation indépendante.")
    pdf.drawRightString(A4[0]-38,30,f'Page {page} / {total}')


def _chart(pdf, result, x, y, width, height):
    values=[float(v) for v in result['modulus']]; lower=[float(v) for v in result['lower']]; upper=[float(v) for v in result['upper']]
    times=[float(v) for v in result['time']]
    lo=0; hi=max(upper)*1.08; tmax=max(times) or 1
    pdf.setStrokeColor(colors.HexColor('#DCE3EF')); pdf.setLineWidth(.5)
    for step in range(5):
        yy=y+height*step/4; pdf.line(x,yy,x+width,yy)
        pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7); pdf.drawRightString(x-5,yy-2,f'{hi*step/4:.0f}')
    for series,color,line_width in ((lower,colors.HexColor('#91A3BF'),1),(upper,TEAL,1),(values,BLUE,2)):
        pdf.setStrokeColor(color); pdf.setLineWidth(line_width)
        path=pdf.beginPath()
        for index,(time,value) in enumerate(zip(times,series)):
            px=x+width*time/tmax; py=y+height*(value-lo)/(hi-lo)
            path.moveTo(px,py) if index==0 else path.lineTo(px,py)
        pdf.drawPath(path,stroke=1,fill=0)
    manifest=result.get('manifest',{})
    model=str(manifest.get('model',''))
    display_unit=(manifest.get('inputs',{}).get('horizon_display',{}) or {}).get('unit','years')
    unit_label={'days':'jours','months':'mois','years':'années'}.get(display_unit,'années') if model.startswith('datasheet') else 'jours'
    pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7)
    pdf.drawCentredString(x+width/2,y-14,f'Temps ({unit_label})')
    pdf.saveState(); pdf.translate(x-28,y+height/2); pdf.rotate(90); pdf.drawCentredString(0,0,'Module de Young (MPa)'); pdf.restoreState()


def result_pdf(result: dict, title: str='Rapport Materia') -> bytes:
    output=BytesIO(); pdf=canvas.Canvas(output,pagesize=A4,pageCompression=1)
    pdf.setTitle(title); pdf.setAuthor('Materia'); width,height=A4
    manifest=result.get('manifest',{}); inputs=manifest.get('inputs',{}); diagnostic=validity_diagnostic(result)
    pdf.setFillColor(INK); pdf.setFont('Helvetica-Bold',18); pdf.drawString(38,height-50,title[:80])
    pdf.setFillColor(MUTED); pdf.setFont('Helvetica',8); pdf.drawString(38,height-68,'Rapport généré le '+datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    pdf.setFillColor(PALE); pdf.roundRect(38,height-150,519,62,5,fill=1,stroke=0)
    cards=[('Module initial',f"{float(result['modulus'][0]):.1f} MPa"),("Module à l'horizon",f"{float(result['modulus'][-1]):.1f} MPa"),('Module conservé',f"{float(result['retention'][-1]):.1f} %"),('Origine',curve_value_origin(result))]
    for index,(label,value) in enumerate(cards):
        xx=50+index*128; pdf.setFillColor(MUTED); pdf.setFont('Helvetica',8); pdf.drawString(xx,height-112,label)
        pdf.setFillColor(INK); pdf.setFont('Helvetica-Bold',12); pdf.drawString(xx,height-134,_pdf_safe(value))
    y=height-175; y=_section(pdf,'Courbe de vieillissement',y); _chart(pdf,result,65,y-195,465,180); y-=220
    y=_section(pdf,'Validité du résultat',y)
    y=_text(pdf,diagnostic['level']+' - '+diagnostic['conclusion'],46,y,500,size=9,bold=True)
    for check in diagnostic['checks']:
        y=_text(pdf,f"{check['criterion']} : {check['finding']}",52,y,492,size=8)
    y=_text(pdf,'Expérience recommandée : '+diagnostic['recommended_experiment'],46,y-3,500,size=8,color=colors.HexColor('#7A4E00'))
    _footer(pdf,1); pdf.showPage(); y=height-45
    y=_section(pdf,'Paramètres d’origine',y)
    for key,value in inputs.items():
        y=_text(pdf,f'{key} : {value}',46,y,500,size=8)
    y-=8; y=_section(pdf,'Source et traçabilité',y)
    source=manifest.get('source') or {}
    for label,key in (('Référence','title'),('DOI','doi'),('URL','url'),('Emplacement','location')):
        if source.get(key): y=_text(pdf,f'{label} : {source[key]}',46,y,500,size=8)
    y=_text(pdf,'Modèle : '+str(manifest.get('model','Non renseigné')),46,y,500,size=8)
    y=_text(pdf,'Empreinte : '+str(result.get('fingerprint','Non renseigné')),46,y,500,size=7)
    y-=8; y=_section(pdf,'Incertitudes et limites',y)
    for item in diagnostic['uncertainty_budget']:
        y=_text(pdf,f"{item['component']} - {item['value']} : {item['meaning']}",46,y,500,size=8)
    for warning in manifest.get('warnings',[]):
        y=_text(pdf,'Limite : '+str(warning),46,y,500,size=8,color=colors.HexColor('#7A4E00'))
    _footer(pdf,2)
    pdf.save(); return output.getvalue()


def _short(value, limit=155):
    text=' '.join(_pdf_safe(value or 'Non renseigné').split())
    return text if len(text)<=limit else text[:limit-1].rstrip()+'…'


def _horizon_label(manifest: dict) -> str:
    inputs=manifest.get('inputs') or {}
    display=inputs.get('horizon_display') or {}
    if display.get('label'):
        return str(display['label'])
    if inputs.get('horizon_years') is not None:
        return f"{float(inputs['horizon_years']):g} ans"
    days=inputs.get('horizon_days',inputs.get('horizon'))
    return f"{float(days):g} jours" if days is not None else 'Non renseigné'


def _source_lines(source: dict) -> list[str]:
    sources=source.get('sources') or []
    if sources:
        lines=[]
        for item in sources[:3]:
            reference=item.get('title') or item.get('id') or 'Source documentaire'
            identifier=item.get('doi') or item.get('url') or item.get('location')
            lines.append(reference+(f' · {identifier}' if identifier else ''))
        if len(sources)>3:
            lines.append(f'+ {len(sources)-3} autre(s) source(s) dans le rapport complet')
        return lines
    reference=source.get('title') or source.get('id') or 'Aucune référence primaire attachée'
    identifier=source.get('doi') or source.get('url') or source.get('location')
    return [reference+(f' · {identifier}' if identifier else '')]


def evidence_card_pdf(result: dict, title: str='Résultat Materia') -> bytes:
    """Create a concise, one-page evidence card for a result."""
    output=BytesIO(); pdf=canvas.Canvas(output,pagesize=A4,pageCompression=1)
    pdf.setTitle('Carte de preuve · '+title); pdf.setAuthor('Materia'); width,height=A4
    manifest=result.get('manifest') or {}; inputs=manifest.get('inputs') or {}
    validity=manifest.get('validity') or {}; uncertainty=manifest.get('uncertainty') or {}
    diagnostic=validity_diagnostic(result); origin=curve_value_origin(result)

    pdf.setFillColor(BLUE); pdf.rect(0,height-92,width,92,fill=1,stroke=0)
    pdf.setFillColor(colors.white); pdf.setFont('Helvetica-Bold',20)
    pdf.drawString(38,height-45,'Carte de preuve')
    pdf.setFont('Helvetica',9); pdf.drawString(38,height-64,_short(title,88))
    pdf.drawRightString(width-38,height-64,datetime.now(timezone.utc).strftime('%Y-%m-%d'))

    card_y=height-158; card_w=166; card_h=51
    center=float(result['modulus'][-1]); retention=float(result['retention'][-1])
    cards=[('Valeur à l’horizon',f'{center:.1f} MPa'),('Module conservé',f'{retention:.1f} %'),('Origine',origin)]
    for index,(label,value) in enumerate(cards):
        x=38+index*(card_w+10); pdf.setFillColor(PALE); pdf.roundRect(x,card_y,card_w,card_h,5,fill=1,stroke=0)
        pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7.5); pdf.drawString(x+10,card_y+34,label)
        pdf.setFillColor(INK); pdf.setFont('Helvetica-Bold',11); pdf.drawString(x+10,card_y+14,_short(value,24))

    material=manifest.get('material_name') or manifest.get('material_id') or manifest.get('experiment_id') or title
    grade=inputs.get('grade_reference') or inputs.get('grade') or 'Non renseigné'
    process=inputs.get('process_state') or inputs.get('process') or 'Non renseigné'
    rows=[
        ('Matériau / formulation',_short(material,95)),
        ('Propriété',_short(manifest.get('target_property') or 'Module de Young',95)),
        ('Grade · procédé',_short(f'{grade} · {process}',95)),
        ('Horizon · modèle',_short(f"{_horizon_label(manifest)} · {manifest.get('model','Non renseigné')}",95)),
    ]
    y=card_y-20; y=_section(pdf,'Identification du calcul',y)
    for label,value in rows:
        pdf.setFillColor(MUTED); pdf.setFont('Helvetica-Bold',7.5); pdf.drawString(46,y,label)
        pdf.setFillColor(INK); pdf.setFont('Helvetica',8); pdf.drawString(157,y,value)
        y-=15

    y-=1; y=_section(pdf,'Domaine couvert',y)
    time_range=validity.get('time_days')
    time_text=(f'{time_range[0]:g} à {time_range[-1]:g} jours' if isinstance(time_range,(list,tuple)) and len(time_range)>=2 else 'Non documenté')
    conditions=[]
    if inputs.get('temperature') is not None: conditions.append(f"{float(inputs['temperature']):g} °C")
    if inputs.get('humidity_RH') is not None: conditions.append(f"{float(inputs['humidity_RH']):g} % HR")
    if inputs.get('thickness_mm') is not None: conditions.append(f"{float(inputs['thickness_mm']):g} mm")
    exposure=inputs.get('exposure') or validity.get('exposure_mode') or validity.get('exposure')
    if exposure: conditions.append(str(exposure))
    y=_text(pdf,f"Fenêtre de preuve : {time_text}. Conditions : {', '.join(conditions) or 'non documentées'}.",46,y,500,size=8)
    if validity.get('protocol'):
        y=_text(pdf,'Protocole : '+_short(validity['protocol'],235),46,y,500,size=7.5,color=MUTED)

    y-=2; y=_section(pdf,'Niveau de preuve et incertitude',y)
    y=_text(pdf,f"{diagnostic['level']} · {diagnostic['conclusion']}",46,y,500,size=8,bold=True)
    uncertainty_label=uncertainty.get('label') or 'Bande calculée, nature non renseignée'
    coverage=uncertainty.get('coverage') or ('statistique descriptive' if uncertainty.get('kind') else 'non documentée')
    y=_text(pdf,f'Bande : {uncertainty_label}. Couverture : {coverage}.',46,y,500,size=8)
    budget=diagnostic.get('uncertainty_budget') or []
    if budget:
        y=_text(pdf,_short(f"{budget[-1]['component']} : {budget[-1]['value']} — {budget[-1]['meaning']}",230),46,y,500,size=7.5,color=MUTED)

    y-=2; y=_section(pdf,'Preuves et traçabilité',y)
    for line in _source_lines(manifest.get('source') or {}):
        y=_text(pdf,'• '+_short(line,215),49,y,495,size=7.5)
    pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7)
    pdf.drawString(46,y,'Empreinte du calcul : '+_short(result.get('fingerprint'),74)); y-=14

    y-=1; y=_section(pdf,'Limites d’usage',y)
    limit=manifest.get('prohibited_use') or 'Ne pas utiliser pour dimensionner, garantir ou qualifier sans validation indépendante.'
    y=_text(pdf,_short(limit,220),46,y,500,size=8,bold=True,color=colors.HexColor('#7A4E00'))
    for warning in (manifest.get('warnings') or [])[:2]:
        y=_text(pdf,'• '+_short(warning,205),49,y,495,size=7.5,color=MUTED)

    pdf.setStrokeColor(colors.HexColor('#DCE3EF')); pdf.line(38,42,width-38,42)
    pdf.setFillColor(MUTED); pdf.setFont('Helvetica',7)
    pdf.drawString(38,28,'Materia · carte synthétique à joindre au rapport · le fichier complet conserve les paramètres et la courbe.')
    pdf.drawRightString(width-38,28,'Page 1 / 1')
    pdf.save(); return output.getvalue()
