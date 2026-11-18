# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Krwanz/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Krwanz/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecaster for GTA VI's launch-day Twitch viewers, hour by hour, in one Python
file, standard library only.

## The model

One hour into release day, all the program knows is hour 1's viewer count. The
forecast for each of hours 2–24 is that count times the shape of a typical
rolling-midnight console launch: for every comparable launch in the case that
unlocked at midnight local time (the same kind of launch GTA VI is), take the
ratio of each hour's viewers to its hour-1 viewers, in log space, and use the
size-weighted median ratio for that hour — a launch's weight falls with how
far its hour-1 size sits from this launch's (Gaussian kernel, width 1.5 in
log space), so a huge launch is priced off huge launches. The median is then
shifted by how big this launch's hour 1 is next to the pool's, in two parts:
a flat level shift (`-0.15 * (ln(p1) - ln(pool median))`) plus an amplitude
shift (`-0.20 * shape(h) * (ln(p1) - ln(pool median))`) that rides the
curve's own shape — zero at the morning dip, full at the evening peak:
big hour-1 launches rise less later and the compression concentrates at the
peak, small ones surge more across the whole day. The spread around the
median is the house baseline's widening spread, `0.15 * sqrt(h - 1)` in log
space, widened above the median (x1.3) and narrowed below it (x0.8), because
launch curves are right-skewed.

Rolling-midnight launches share one shape — a dip in the small hours, a rise as
the Americas unlock, an evening peak, an overnight decay. Launches that unlocked
simultaneously worldwide, or with early access, follow different shapes and are
left out of the pool.

## Local check

On 37 past launches treated as pseudo-cases (each scored against its own
release day, the pool built leave-one-out), the rolling-midnight subset — the
kind of launch this contest's final is — scores a mean pinball loss of 0.252
against v2's 0.259 and the house baseline's 0.406 on the same cases, a median
of 0.209 against 0.255, and 7 of 8 beat the baseline, with the worst case
improved to 0.609 from 0.628. Across all 37 the mean is 0.588 against v2's
0.690 and the baseline's 0.930. The kit reports the house baseline's practice
loss as 0.387, which the pseudo-evaluation reproduces closely on the rolling
subset (0.406), so the improvement should carry to the practice set. The
final is one case, so the practice margin is an estimate, not a guarantee.

## Run it

    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py

Deterministic: no randomness, no clock, no network; two runs on the same case
write the same bytes. Runs in well under a second per case (limit: 8 s).

Entry for make.fun `gta6-twitch-ccu-forecast-01`: forecast GTA VI's launch-day
Twitch viewers hour by hour. $250 total, top 20 paid, 1st place $50.
Deadline 2026-11-19T01:00:00Z.
