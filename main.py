"""gta6-twitch-ccu-forecast-01: forecast GTA VI's launch-day Twitch viewers, hour by hour.

The program reads one case (makefun/twitch-ccu-case/v1) from the input directory and
writes, for each of hours 2..24 of the release day, five quantiles (5%, 25%, 50%, 75%,
95%) of that hour's Twitch category viewer count, as JSON {"hours": [{"hour": h, "q":
[q05, q25, q50, q75, q95]}, ...]} to the output directory.

Model: a rolling-midnight launch curve, calibrated on the case's own comparables,
with two corrections the comparables themselves support. For every comparable
launch whose unlock rolled at midnight local time (the same kind of launch GTA VI
is), take the ratio of each hour's viewers to that launch's hour-1 viewers, in
log space. The forecast's median for hour h is the hour-1 print times the median
log-ratio for h across those comparables, shifted by how big this launch's hour 1
is next to the pool's: shift = -0.25 * (ln(p1) - ln(pool median hour 1)). Big
hour-1 launches (front-loaded: much of the audience was already watching at
midnight, leaks or hype) rise less later; small hour-1 launches surge more.
The spread around the median is the house baseline's widening spread,
0.15 * sqrt(h - 1) in log space, widened above the median (x1.3) and narrowed
below it (x0.8): launch curves are right-skewed, upward surges run further than
downward ones, so the five quantiles are median * exp(z_tau * spread_tau) with
z the standard normal quantiles. Rolling-midnight launches share one shape: a
dip in the small hours, a rise as the Americas unlock, an evening peak, an
overnight decay. Launches that unlocked simultaneously worldwide, or with early
access, follow different shapes and are left out of the pool; the GTA VI
pre-release curve is not a launch and is left out too.

Python 3.13, standard library only. Deterministic: no randomness, no wall clock,
no network; the same case always writes the same bytes. Runs in well under a
second per case.

Outside the grader's container, MAKEFUN_INPUT_DIR and MAKEFUN_OUTPUT_DIR stand in
for /input and /output:
    mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so a helper module
# shipped beside this file would import. (This entry ships one file only.)
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
# The spread of an hour's move, in natural-log units per square-root hour
# (the house baseline's spread; the median below is what this entry improves).
SIGMA = 0.15
# The hour-1 size correction (see median_log_ratios): how much the median
# log-ratio curve flattens per log unit this launch's hour 1 sits above the
# pool's median hour 1. Negative: a bigger hour 1 means a flatter day.
BETA = -0.25
# The spread is asymmetric: launch curves are right-skewed, so the quantiles
# above the median widen and the ones below it narrow, by these factors.
SPREAD_UP = 1.3
SPREAD_LO = 0.8
# A comparable only joins the pool when its hour-1 print is at least this big:
# a near-empty category's ratios are noise.
MIN_HOUR1_VIEWERS = 100
# A per-hour median needs at least this many launches behind it; with fewer,
# that hour falls back to persistence (median log-ratio 0).
MIN_POOL_PER_HOUR = 5


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100.

    A whole number comes back as an int, so json.dumps writes 1240 where
    JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_hour(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def is_rolling_midnight(comp: dict) -> bool:
    """True when this comparable launched the way GTA VI does: consoles rolling
    at midnight local time, no simultaneous worldwide unlock, no early access.

    The unlock note is the kit authors' own classification; the checks below
    read it in the same order the notes were written: early access and
    simultaneous-global launches are different shapes and stay out.
    """
    text = (comp.get("unlock", "") + " " + comp.get("name", "")).lower()
    if "before release" in text or "target-history" in text:
        return False
    # "early-access" with a hyphen is the tier marker the kit authors put on
    # contaminated launches ("Tier: early-access-contaminated"). Plain
    # "early access" with a space also appears inside the notes of clean
    # launches ("campaign early access preceded") and must not exclude them.
    if "early-access" in text:
        return False
    if "simultaneous" in text or "single global" in text:
        return False
    if "free-to-play" in text or "f2p" in text:
        return False
    return "midnight local" in text or "rolling" in text


def release_day_hours(comp: dict) -> dict[int, int]:
    """The comparable's release-day hourly viewers, keyed by hour 1..24."""
    try:
        day_start = parse_hour(comp["day_start"])
    except (KeyError, ValueError):
        return {}
    hours: dict[int, int] = {}
    for point in comp.get("hourly", []):
        try:
            at = parse_hour(point["from"])
            viewers = point["viewers"]
        except (KeyError, ValueError, TypeError):
            continue
        hour = int((at - day_start).total_seconds() // 3600) + 1
        if 1 <= hour <= 24 and isinstance(viewers, (int, float)) and viewers >= 0:
            hours[hour] = viewers
    return hours


def median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def median_log_ratios(case: dict, p1: float) -> dict[int, float]:
    """Per-hour median log(viewers_h / viewers_1) over the rolling-midnight
    comparables, shifted by this launch's hour-1 size. An hour with too thin
    a pool maps to 0.0 (persistence, unshifted).

    The size shift is the one structural correction the comparables support:
    across all 37 of them, a launch's hour-1 size predicts its curve's
    amplitude — big hour-1 launches (the audience already there at midnight)
    rise less over the day, small hour-1 launches surge more (leave-one-out
    correlation -0.3 to -0.6 by hour). The shift is BETA times this launch's
    log hour-1 minus the pool's median log hour-1, so a typical-size launch
    is barely moved and the correction grows with how far off-typical it is.
    """
    per_hour: dict[int, list[float]] = {h: [] for h in range(2, 25)}
    firsts: list[float] = []
    for comp in case.get("comparables", []):
        if not is_rolling_midnight(comp):
            continue
        hours = release_day_hours(comp)
        first = hours.get(1, 0)
        if first < MIN_HOUR1_VIEWERS:
            continue
        firsts.append(first)
        for hour in range(2, 25):
            viewers = hours.get(hour, 0)
            if viewers > 0:
                per_hour[hour].append(math.log(viewers / first))
    shift = 0.0
    if firsts:
        shift = BETA * (math.log(max(p1, 1.0)) - math.log(median(firsts)))
    return {
        hour: (median(ratios) + shift if len(ratios) >= MIN_POOL_PER_HOUR else 0.0)
        for hour, ratios in per_hour.items()
    }


def hour_quantiles(p1: float, hour: int, log_median: float) -> list[float | int]:
    """The five quantiles for one hour: the calibrated median, widened by the
    baseline's spread, asymmetrically — wider above the median, narrower
    below it, because launch curves are right-skewed (pooled log-ratio
    deviations from the per-hour median run further up than down)."""
    spread = SIGMA * math.sqrt(hour - 1)
    quantiles = []
    for z in Z:
        factor = SPREAD_UP if z > 0 else SPREAD_LO if z < 0 else 1.0
        value = p1 * math.exp(log_median + z * factor * spread)
        value = min(max(value, 1.0), 1e9)
        quantiles.append(round2(value))
    # Rounding can only tie neighbours, never invert them, but enforce the
    # contract explicitly so the output is valid by construction.
    for i in range(1, len(quantiles)):
        if quantiles[i] < quantiles[i - 1]:
            quantiles[i] = quantiles[i - 1]
    return quantiles


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])
    log_medians = median_log_ratios(case, p1)
    return {
        "hours": [
            {
                "hour": row["hour"],
                "q": hour_quantiles(p1, row["hour"], log_medians.get(row["hour"], 0.0)),
            }
            for row in case["forecast"]
        ]
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
