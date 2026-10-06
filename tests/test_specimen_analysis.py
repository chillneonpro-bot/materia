from materia.specimen_analysis import analyse_specimens


def rows(values, lot="L1", day=30):
    return [
        {
            "time_days": day,
            "modulus_mpa": value,
            "replicate_id": f"{lot}-J{day}-E{index}",
            "lot_id": lot,
            "specimen_id": f"{lot}-J{day}-E{index}",
        }
        for index, value in enumerate(values, 1)
    ]


def test_robust_outlier_is_flagged_but_never_removed():
    report = analyse_specimens(rows([99, 100, 100, 101, 140]))
    flagged = [row for row in report["observations"] if row["outlier_candidate"]]
    assert len(flagged) == 1
    assert flagged[0]["modulus_mpa"] == 140
    assert all(row["included_in_validation"] for row in report["observations"])
    assert report["groups"][0]["outlier_candidates"] == 1
    assert "MAD" in report["groups"][0]["outlier_method"]


def test_small_groups_are_explicitly_not_evaluated():
    report = analyse_specimens(rows([99, 100, 101, 140]))
    assert report["flagged_count"] == 0
    assert report["unevaluated_groups"] == 1
    assert report["groups"][0]["outlier_evaluable"] is False
    assert all(row["outlier_label"] == "Non évalué" for row in report["observations"])


def test_zero_robust_dispersion_fallback_avoids_rounding_false_positives():
    ordinary = analyse_specimens(rows([99, 100, 100, 100, 101]))
    assert ordinary["flagged_count"] == 0
    extreme = analyse_specimens(rows([100, 100, 100, 100, 140]))
    assert extreme["flagged_count"] == 1
    assert "5 %" in extreme["groups"][0]["outlier_method"]


def test_groups_are_separated_by_lot_and_time():
    report = analyse_specimens(rows([99, 100, 101, 100, 99], "L1", 0) + rows([90, 91, 90, 89, 90], "L2", 30))
    assert len(report["groups"]) == 2
    assert len(report["lots"]) == 2
    assert {group["lot_id"] for group in report["groups"]} == {"L1", "L2"}
