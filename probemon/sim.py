"""Scheduled user-flow probes on many browser x OS x network environments, with known truth.

Each probe is one flow run on one environment. Flows flake a little (3G much more than Ethernet), and incidents make a flow fail on a slice of environments.
All rates are invented."""
import numpy as np

CELLS = [("chrome", "macos"), ("chrome", "windows"), ("chrome", "android"), ("safari", "macos"), ("safari", "ios"), ("firefox", "macos"), ("firefox", "windows"), ("firefox", "android")]
NETS = ["ethernet", "fast_wifi", "5g", "slow_wifi", "4g", "3g"]
SLOW = {"slow_wifi", "4g", "3g"}
FLAKE = {"ethernet": 0.005, "fast_wifi": 0.008, "5g": 0.015, "slow_wifi": 0.025, "4g": 0.03, "3g": 0.06}
ENVS = [(b, o, n) for b, o in CELLS for n in NETS]
SLOT_H = 0.5


def slices():
    out = {"all": set(range(len(ENVS)))}
    for b in sorted({c[0] for c in CELLS}):
        out[f"browser={b}"] = {i for i, e in enumerate(ENVS) if e[0] == b}
    for o in sorted({c[1] for c in CELLS}):
        out[f"os={o}"] = {i for i, e in enumerate(ENVS) if e[1] == o}
    out["slow networks"] = {i for i, e in enumerate(ENVS) if e[2] in SLOW}
    for b, o in CELLS:
        out[f"{b} on {o}"] = {i for i, e in enumerate(ENVS) if e[:2] == (b, o)}
    return out


SLICES = slices()
INCIDENT_SLICES = [k for k in SLICES]


def make_world(seed, flake_scale=1.0, probes_per_slot=8, days=14, history_days=7, n_flows=5):
    rng = np.random.default_rng(seed)
    n_slots = days * 48
    hist = history_days * 48
    base = np.array([FLAKE[e[2]] for e in ENVS]) * flake_scale
    flow_extra = rng.uniform(0, 0.012, n_flows) * flake_scale
    incidents, weather = [], []
    for f in range(n_flows):                                       # one incident per flow in the test period, at different times
        start = int(rng.integers(hist + 20, n_slots - 40))
        dur = int(rng.integers(6, 28))
        name = INCIDENT_SLICES[int(rng.integers(len(INCIDENT_SLICES)))]
        incidents.append({"flow": f, "start": start, "end": start + dur, "slice": name, "fail_p": 0.95})
    for _ in range(3):                                             # network weather: benign flake bump on slow networks, not an incident
        s = int(rng.integers(hist + 10, n_slots - 30))
        weather.append({"start": s, "end": s + int(rng.integers(8, 14)), "mult": 3.0})
    probes = []                                                    # (slot, flow, env, failed)
    order = {f: rng.permutation(len(ENVS)) for f in range(n_flows)}
    ptr = {f: 0 for f in range(n_flows)}
    for t in range(n_slots):
        for f in range(n_flows):
            for _ in range(probes_per_slot):
                e = int(order[f][ptr[f] % len(ENVS)])
                ptr[f] += 1
                p = base[e] + flow_extra[f]
                for w in weather:
                    if w["start"] <= t < w["end"] and ENVS[e][2] in SLOW:
                        p *= w["mult"]
                for inc in incidents:
                    if inc["flow"] == f and inc["start"] <= t < inc["end"] and e in SLICES[inc["slice"]]:
                        p = inc["fail_p"]
                probes.append((t, f, e, bool(rng.random() < p)))
    return {"probes": probes, "incidents": incidents, "hist": hist, "n_slots": n_slots, "n_flows": n_flows}
