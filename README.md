# probemon: when should a scheduled user-flow probe page someone?

Simulithic runs user flows "on the devices your visitors use, as often as every 30 minutes" and alerts in Slack when one breaks (https://simulithic.com). Two things decide whether those alerts are trusted: flaky failures on slow networks must not page anyone, and a real break on one browser, OS or network class must be named ("know what broke, on which device"). This prototype is a simulator with known truth for that. It is not Simulithic's system.

## The setup
`probemon/sim.py`: 5 flows, 48 environments (8 browser x OS cells x 6 networks: Ethernet, fast and slow Wi-Fi, 5G, 4G, 3G), a probe every 30 minutes on 8 environments per flow in rotation, 7 days of history then 7 test days. Each probe flakes (0.5% on Ethernet up to 6% on 3G, plus a per-flow extra). One planted incident per flow in the test week: from 3 to 14 hours the flow fails 95% of the time on a slice (all environments, one browser, one OS, slow networks only, or one browser x OS cell). Three "network weather" bumps triple the flake rate on slow networks for 4-7 hours; those are not incidents.
`probemon/alert.py`: four alerters. Alert on first failure; the same flow and environment fails twice in a row; 3 of the flow's last 8 probes failed; slice scan: a baseline failure rate per flow and network from the history week, then a rolling 6-hour log-likelihood ratio over every candidate slice (alternative: 90% failure), alert at 9 and name the best slice. An alert already open (alerts less than 6 hours apart) counts as one episode.

## Results (held-out: 30 worlds with 1.6x flake rates and 6 probes per slot, 150 incidents; fixed in git before the first run)
| | incidents found | median hours to alert | false alerts per flow-week | slice named right (of all incidents) |
|---|---|---|---|---|
| alert on first failure | 3% | 0.0 | 3.68 | n/a |
| same environment fails twice | 82% | 3.0 | 5.27 | n/a |
| 3 of last 8 probes failed | 82% | 0.5 | 3.73 | n/a |
| slice scan | **99%** | 3.0 | **0.06** | 85% |
Dev (12 worlds, 60 incidents): 3% / 88% / 92% / 97% found; false alerts per flow-week 5.18 / 3.38 / 2.03 / 0.02; slice scan slice right 87%.
- Alerting on the first failure is useless here: a flow fires almost constantly, and an alert that is already open hides the real one (so its 3% "found" says little about speed).
- The simple k-of-n rule reacts fastest (half an hour) but pages 3.7 times per flow-week; the slice scan is slower (3 hours median, the price of waiting for evidence) and almost silent.
- Naming the slice is right 85% of the time; the misses are slices that differ by few probes (one cell inside a browser) at alert time.

## Two things I found wrong in my own harness after the first held-out run
The first run scored slice names by label, but "os=ios" and "safari on ios" are the same six environments (slice right 79%, 87% when scored by environment set), and set iteration order made the incident mix change between Python processes. I fixed both and reran; the rerun changed the numbers slightly (slice scan 98% -> 99% found), the held-out configuration was not touched.

## Read this before believing the table
All rates are invented; real flakiness is correlated (a CDN blip hits every flow), incidents are rarely clean 95% failures, and the history week contains no incidents here. The threshold (9) was set on the dev worlds. No claim about Simulithic's alerting.

## Run it (3 commands)
```
pip install numpy pytest
python -m pytest -q tests
python -m probemon.run
```
numpy only. 5 tests; the run takes about a minute.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Simulithic.
