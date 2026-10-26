"""Four ways to turn scheduled probe results into alerts. Each returns [(slot, flow, slice name or None)]."""
from collections import defaultdict, deque

import numpy as np

from .sim import ENVS, NETS, SLICES

REFRACTORY = 12          # slots (6 h) before the same flow can alert again


def _episodes(raw):
    last, out = {}, []
    for t, f, s in raw:
        if f not in last or t - last[f] >= REFRACTORY:
            out.append((t, f, s))
        last[f] = t
    return out


def first_failure(w):
    return _episodes([(t, f, None) for t, f, e, y in w["probes"] if y and t >= w["hist"]])


def same_env_twice(w):
    last, raw = {}, []
    for t, f, e, y in w["probes"]:
        if t >= w["hist"] and y and last.get((f, e)):
            raw.append((t, f, None))
        last[(f, e)] = y
    return _episodes(raw)


def k_of_n(w, k=3, n=8):
    win, raw = defaultdict(lambda: deque(maxlen=n)), []
    for t, f, e, y in w["probes"]:
        win[f].append(y)
        if t >= w["hist"] and sum(win[f]) >= k:
            raw.append((t, f, None))
    return _episodes(raw)


def baseline(w):
    """Failure rate per (flow, network) over the history period, smoothed toward 1%."""
    n, k = defaultdict(int), defaultdict(int)
    for t, f, e, y in w["probes"]:
        if t < w["hist"]:
            key = (f, NETS.index(ENVS[e][2]))
            n[key] += 1
            k[key] += y
    return {key: (k[key] + 0.1) / (n[key] + 10) for key in n}


def slice_scan(w, h=9.0, window=12, alt=0.9):
    base = baseline(w)
    names = list(SLICES)
    member = np.zeros((len(names), len(ENVS)), bool)
    for i, nm in enumerate(names):
        member[i, list(SLICES[nm])] = True
    by_slot = defaultdict(list)
    for t, f, e, y in w["probes"]:
        by_slot[t].append((f, e, y))
    recent = defaultdict(lambda: deque(maxlen=window))        # per flow: list of per-slot LLR vectors over slices
    raw = []
    for t in range(w["n_slots"]):
        per_flow = defaultdict(lambda: np.zeros(len(names)))
        for f, e, y in by_slot[t]:
            p = base[(f, NETS.index(ENVS[e][2]))]
            llr = np.log(alt / p) if y else np.log((1 - alt) / (1 - p))
            per_flow[f] += member[:, e] * llr
        for f in range(w["n_flows"]):
            recent[f].append(per_flow[f])
            if t >= w["hist"]:
                tot = np.sum(recent[f], axis=0)
                j = int(np.argmax(tot))
                if tot[j] > h:
                    raw.append((t, f, names[j]))
    return _episodes(raw)


METHODS = {"alert on first failure": first_failure, "same environment fails twice": same_env_twice, "3 of last 8 probes failed": k_of_n,
           "slice scan (per-network baseline + slice likelihood)": slice_scan}
