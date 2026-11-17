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
median ratio for that hour. The spread around the median is the house baseline's
widening spread, `0.15 * sqrt(h - 1)` in log space, so the five quantiles are
`median * exp(z_tau * 0.15 * sqrt(h - 1))`.

Rolling-midnight launches share one shape — a dip in the small hours, a rise as
the Americas unlock, an evening peak, an overnight decay. Launches that unlocked
simultaneously worldwide, or with early access, follow different shapes and are
left out of the pool.

## Local check

On 37 past launches treated as pseudo-cases (each scored against its own
release day, the pool built leave-one-out), the rolling-midnight subset — the
kind of launch this contest's final is — scores a mean pinball loss of 0.285
against the house baseline's 0.406 on the same cases, a median of 0.194 against
0.255. The kit reports the house baseline's practice loss as 0.387, which the
pseudo-evaluation reproduces closely on the rolling subset (0.406), so the
improvement should carry to the practice set. The final is one case, so the
practice margin is an estimate, not a guarantee.

## Run it

    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py

Deterministic: no randomness, no clock, no network; two runs on the same case
write the same bytes. Runs in well under a second per case (limit: 8 s).

Entry for make.fun `gta6-twitch-ccu-forecast-01`: forecast GTA VI's launch-day
Twitch viewers hour by hour. $250 total, top 20 paid, 1st place $50.
Deadline 2026-11-19T01:00:00Z.
