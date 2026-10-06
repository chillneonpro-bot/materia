import plotly.graph_objects as go
COLORS=['#2156bc','#13958b','#8b64b6','#dc8535']
def base():
    fig=go.Figure()
    fig.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial, sans-serif',color='#526079',size=13),margin=dict(l=55,r=24,t=24,b=50),height=350,hovermode='x unified',legend=dict(orientation='h',y=1.15,x=0),xaxis=dict(title='Temps de vieillissement (jours)',gridcolor='#eef1f6',zeroline=False),yaxis=dict(title='Module de Young (MPa)',gridcolor='#eef1f6',zeroline=False),transition=dict(duration=0))
    return fig

def curve(result, threshold=None, band_mode='central'):
    f=base(); t=result['time']
    model=result.get('manifest',{}).get('model','')
    observed=model in {'piecewise-linear-observed-v1','piecewise-linear-published-v1'}
    published=model=='piecewise-linear-published-v1'
    datasheet=model.startswith('datasheet-screening-')
    calibrated=datasheet and result.get('manifest',{}).get('assumptions',{}).get('evidence_calibrated')
    uncertainty_label=result.get('manifest',{}).get('uncertainty',{}).get('label')
    if datasheet:
        display_unit=result.get('manifest',{}).get('inputs',{}).get('horizon_display',{}).get('unit','years')
        factor={'days':365.25,'months':12.,'years':1.}.get(display_unit,1.)
        unit_label={'days':'jours','months':'mois','years':'années'}.get(display_unit,'années')
        t=[value*factor for value in t]
        f.update_xaxes(title=f'Temps de vieillissement estimé ({unit_label})')
        window_days=result.get('manifest',{}).get('assumptions',{}).get('evidence_window_days')
        if calibrated and window_days:
            display_window=float(window_days)/{'days':1.,'months':365.25/12,'years':365.25}.get(display_unit,365.25)
            if display_window<max(t):
                f.add_vrect(x0=display_window,x1=max(t),fillcolor='rgba(245,165,36,.07)',line_width=0,layer='below')
            f.add_vline(x=display_window,line_dash='dot',line_color='#b9782d',
                        annotation_text='Fin des observations comparables',annotation_position='top right')
    if band_mode not in {'central','outer'}:
        raise ValueError('Mode de bande inconnu.')
    outer_available=bool(result.get('outer_lower') and result.get('outer_upper'))
    use_outer=band_mode=='outer' and outer_available
    band_lower=result['outer_lower'] if use_outer else result['lower']
    band_upper=result['outer_upper'] if use_outer else result['upper']
    band_name='Enveloppe complète min–max observée' if use_outer else uncertainty_label
    show_band=result.get('manifest',{}).get('uncertainty',{}).get('display_band',True)
    if show_band:
        f.add_trace(go.Scatter(x=t,y=band_upper,mode='lines',line=dict(width=0),showlegend=False,hoverinfo='skip',connectgaps=False))
        f.add_trace(go.Scatter(x=t,y=band_lower,mode='lines',line=dict(width=0),fill='tonexty',fillcolor='rgba(33,86,188,.12)',name=band_name or ('Écart-type publié' if published else 'Incertitude de numérisation' if observed else 'Dispersion inter-formulations' if calibrated else 'Sensibilité 5–95 % (synthétique)'),hoverinfo='skip',connectgaps=False))
    extrapolated=bool(calibrated and result.get('manifest',{}).get('assumptions',{}).get('extrapolation_multiple',0)>1)
    f.add_trace(go.Scatter(x=t,y=result['modulus'],mode='lines',name='Interpolation des mesures publiées' if published else 'Interpolation des observations' if observed else 'Profil documentaire central puis extrapolation' if extrapolated else 'Profil documentaire central' if calibrated else 'Estimation centrale de présélection' if datasheet else 'Scénario synthétique',line=dict(color=COLORS[0],width=3),hovertemplate='%{y:.0f} MPa'))
    if observed and result.get('observed_points'):
        f.add_trace(go.Scatter(x=[p['time_days'] for p in result['observed_points']],y=[p.get('modulus_MPa',p.get('modulus_mpa')) for p in result['observed_points']],mode='markers',name='Points publiés',marker=dict(size=8,color='#13958b')))
    if threshold is not None: f.add_hline(y=threshold,line_dash='dash',line_color='#b9782d',annotation_text='Seuil choisi',annotation_position='bottom right')
    visible_upper=[float(value) for value in band_upper if value is not None]
    f.update_yaxes(range=[0,max(visible_upper or result['upper'])*1.12])
    return f

def _comparison_time_days(result):
    """Return every supported result on one physical time axis."""
    model=str(result.get('manifest',{}).get('model',''))
    factor=365.25 if model.startswith('datasheet-screening-') else 1.
    return [float(value)*factor for value in result['time']]


def comparison(results, display_unit=None, threshold_percent=None):
    """Compare normalized curves on one shared and explicit time unit."""
    f=base()
    prepared=[(name,r,_comparison_time_days(r)) for name,r in results]
    max_days=max((max(days) for _,_,days in prepared if days),default=0.)
    if display_unit not in {None,'days','months','years'}:
        raise ValueError('Unité de comparaison inconnue.')
    if display_unit is None:
        display_unit='years' if max_days>=730 else 'months' if max_days>=120 else 'days'
    divisor={'days':1.,'months':365.25/12,'years':365.25}[display_unit]
    axis_unit={'days':'jours','months':'mois','years':'années'}[display_unit]
    for i,(name,r,days) in enumerate(prepared):
        times=[value/divisor for value in days]
        f.add_trace(go.Scatter(x=times,y=r['retention'],name=name,mode='lines',line=dict(color=COLORS[i%4],width=3,dash=['solid','dash','dot','dashdot'][i%4])))
    f.update_xaxes(title=f'Temps de vieillissement ({axis_unit})')
    f.update_yaxes(title='Module conservé (%)',rangemode='tozero')
    if threshold_percent is not None:
        threshold=float(threshold_percent)
        if not 0<threshold<=100:
            raise ValueError('Seuil de comparaison invalide.')
        f.add_hline(y=threshold,line_dash='dash',line_color='#b9782d',
                    annotation_text=f'Seuil commun · {threshold:g} %',annotation_position='bottom right')
    return f
