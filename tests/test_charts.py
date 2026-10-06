import pytest

from materia.charts import comparison, curve


def result(model, times, retention, unit=None):
    inputs={'horizon_display':{'unit':unit}} if unit else {}
    return {'time':times,'retention':retention,'manifest':{'model':model,'inputs':inputs}}


def test_comparison_uses_one_physical_time_axis_for_mixed_models():
    datasheet=result('datasheet-screening-v4',[0,1],[100,80],'months')  # internal time remains years
    synthetic=result('synthetic-arrhenius-1.0',[0,365.25],[100,70])
    figure=comparison([('Fiche',datasheet),('Exercice',synthetic)],display_unit='years',threshold_percent=80)
    assert list(figure.data[0].x)==pytest.approx([0,1])
    assert list(figure.data[1].x)==pytest.approx([0,1])
    assert figure.layout.xaxis.title.text=='Temps de vieillissement (années)'
    assert any(shape.y0==80 and shape.y1==80 for shape in figure.layout.shapes)


def test_comparison_auto_selects_one_unit_and_rejects_invalid_inputs():
    short=result('synthetic-arrhenius-1.0',[0,30],[100,90])
    long=result('synthetic-arrhenius-1.0',[0,180],[100,75])
    figure=comparison([('Court',short),('Long',long)])
    assert figure.layout.xaxis.title.text=='Temps de vieillissement (mois)'
    assert list(figure.data[0].x)[-1]==pytest.approx(30/(365.25/12))
    with pytest.raises(ValueError,match='Unité'):
        comparison([('Court',short)],display_unit='weeks')
    with pytest.raises(ValueError,match='Seuil'):
        comparison([('Court',short)],threshold_percent=0)


def test_curve_can_show_observed_outer_envelope_without_connecting_extrapolation():
    data={
        'time':[0,.1,.2,.3], 'modulus':[100,90,80,70], 'lower':[100,85,72,60],
        'upper':[100,95,88,82], 'outer_lower':[100,80,65,None],
        'outer_upper':[100,98,92,None],
        'manifest':{'model':'datasheet-screening-v4','inputs':{'horizon_display':{'unit':'years'}},
                    'assumptions':{'evidence_calibrated':True,'evidence_window_days':73,'extrapolation_multiple':1.5},
                    'uncertainty':{'label':'Bande centrale','display_band':True}},
    }
    figure=curve(data,80,'outer')
    assert figure.data[1].name=='Enveloppe complète min–max observée'
    assert list(figure.data[0].y)[-1] is None
    assert figure.data[0].connectgaps is False
    with pytest.raises(ValueError,match='Mode de bande'):
        curve(data,80,'unknown')
