import json

import numpy as np

from . import alert, sim


def score(seeds, held):
    kw = {"flake_scale": 1.6, "probes_per_slot": 6} if held else {}
    acc = {m: {"found": 0, "inc": 0, "ttd": [], "false": 0, "attr": 0, "weeks": 0.0} for m in alert.METHODS}
    for s in seeds:
        w = sim.make_world(s, **kw)
        weeks = (w["n_slots"] - w["hist"]) / 48 / 7 * w["n_flows"]
        for m, fn in alert.METHODS.items():
            eps = fn(w)
            a = acc[m]
            a["weeks"] += weeks
            used = set()
            for inc in w["incidents"]:
                a["inc"] += 1
                hit = [e for e in eps if e[1] == inc["flow"] and inc["start"] <= e[0] < inc["end"] + 6 and id(e) not in used]
                if hit:
                    e = hit[0]
                    used.add(id(e))
                    a["found"] += 1
                    a["ttd"].append((e[0] - inc["start"]) * sim.SLOT_H)
                    a["attr"] += e[2] == inc["slice"]
            a["false"] += sum(1 for e in eps if not any(i["flow"] == e[1] and i["start"] <= e[0] < i["end"] + 6 for i in w["incidents"]))
    out = {}
    for m, a in acc.items():
        out[m] = {"incidents_found_pct": round(100 * a["found"] / a["inc"]), "median_hours_to_alert": round(float(np.median(a["ttd"])), 1) if a["ttd"] else None,
                  "false_alerts_per_flow_week": round(a["false"] / a["weeks"], 2), "slice_named_right_pct": round(100 * a["attr"] / a["inc"]) if m.startswith("slice") else None}
    return out


def main():
    res = {"dev": score(range(0, 12), False), "held_out": score(range(1000, 1030), True)}
    json.dump(res, open("out/result.json", "w"), indent=1)
    for k, v in res.items():
        print(k)
        for m, d in v.items():
            print("  ", m, d)


if __name__ == "__main__":
    main()
