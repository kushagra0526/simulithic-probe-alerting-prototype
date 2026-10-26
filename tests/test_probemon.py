from probemon import alert, sim


def test_slices_cover_expected_environments():
    assert len(sim.ENVS) == 48
    assert len(sim.SLICES["browser=safari"]) == 12 and len(sim.SLICES["slow networks"]) == 24
    assert len(sim.SLICES["safari on ios"]) == 6


def test_world_is_reproducible():
    a, b = sim.make_world(1), sim.make_world(1)
    assert a["probes"] == b["probes"] and a["incidents"] == b["incidents"]


def test_scan_names_the_slice_of_a_planted_incident():
    w = sim.make_world(3)
    inc = w["incidents"][0]
    eps = [e for e in alert.slice_scan(w) if e[1] == inc["flow"] and inc["start"] <= e[0] < inc["end"] + 6]
    assert eps and eps[0][0] - inc["start"] < 12


def test_scan_stays_quiet_without_incidents():
    w = sim.make_world(4)
    w["incidents"] = []
    clean = sim.make_world(4)
    clean["probes"] = [p for p in clean["probes"] if True]
    # replace failures during incident windows with passes so the stream has no incident
    inc = clean["incidents"]
    clean["probes"] = [(t, f, e, y and not any(i["flow"] == f and i["start"] <= t < i["end"] and e in sim.SLICES[i["slice"]] for i in inc)) for t, f, e, y in clean["probes"]]
    assert len(alert.slice_scan(clean)) <= 1


def test_first_failure_alerts_constantly():
    w = sim.make_world(5)
    assert len(alert.first_failure(w)) > len(alert.slice_scan(w))
