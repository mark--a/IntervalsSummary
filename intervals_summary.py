#!/usr/bin/env python3
"""
intervals_summary.py  v3
------------------------
Pulls recent activities from Intervals.icu and outputs a compact,
token-efficient summary optimized for pasting into Claude.

Output per activity (~90 tokens each):
--- Tue Apr 21 | Race: Yumezi Grit C | 0:36 | 767ft | outdoor ---
Load 54 | TRIMP 52 | NP 230W | Avg 224W | VI 1.03 | IF 0.95
Avg HR 155 | Max HR 168 | EF 1.48 | HRRc 28 | Form +1 | 75.5kg
SS 11.6% | Cal 484 | eFTP 241W

HR:  Z1 0% | Z2 0% | Z3 22.7% | Z4 77.2% | Z5 0%
PWR: Z1 1% | Z2 12.6% | Z3 35.6% | Z4 29.2% | Z5 14.2% | Z6 7.3% | Z7 0%

SETUP
-----
  export INTERVALS_API_KEY="your_key"
  export INTERVALS_ATHLETE_ID="i438311"

USAGE
-----
  python3 intervals_summary.py              # last 7 days
  python3 intervals_summary.py --days 14   # last 14 days
  python3 intervals_summary.py --count 5   # last 5 activities
  python3 intervals_summary.py --copy      # copy to clipboard (macOS)
"""

import os, sys, argparse, csv, io, subprocess
from datetime import datetime, timedelta, timezone

# ── CONFIG ────────────────────────────────────────────────────────────
API_KEY    = os.environ.get("INTERVALS_API_KEY",    "YOUR_API_KEY_HERE")
ATHLETE_ID = os.environ.get("INTERVALS_ATHLETE_ID", "YOUR_ATHLETE_ID_HERE")
BASE_URL   = "https://intervals.icu/api/v1"
FTP        = 243   # fallback if not in CSV
LTHR       = 161
MAX_HR     = 173


def fetch_csv(path):
    """Fetch CSV via curl with shell=True — credentials inline in command string."""
    url = f"{BASE_URL}/{path}"
    cmd = f'/opt/homebrew/opt/curl/bin/curl --silent --http2 -u "API_KEY:{API_KEY}" "{url}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    content = result.stdout.lstrip('\ufeff')

    if result.returncode != 0 or content.startswith("{"):
        print(f"curl rc={result.returncode}", file=sys.stderr)
        print(f"stdout={result.stdout[:300]}", file=sys.stderr)
        sys.exit(1)

    return list(csv.DictReader(io.StringIO(content)))


def fv(row, key, default=0.0):
    """Safe float from CSV row."""
    try:
        v = (row.get(key) or "").strip()
        return float(v) if v else default
    except (ValueError, AttributeError):
        return default


def fmt_dur(seconds):
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m = rem // 60
    return f"{h}:{m:02d}" if h else f"0:{m:02d}"


def fmt_date(iso):
    try:
        return datetime.fromisoformat(iso[:19]).strftime("%a %b %-d")
    except Exception:
        return iso[:10]


def clean_name(name):
    # Strip only the "Zwift - " platform prefix — preserve everything else
    for prefix in ["Zwift - ", "Zwift – "]:
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def zone_pcts(row, keys):
    secs = [fv(row, k) for k in keys]
    total = sum(secs)
    if total == 0:
        return ["0%"] * len(keys)
    return [f"{s/total*100:.1f}%" for s in secs]


def format_activity(row):
    # ── Identity ──────────────────────────────────────────────────────
    date_str  = fmt_date(row.get("start_date_local", ""))
    name      = clean_name(row.get("name", "Unknown"))
    dur       = fmt_dur(fv(row, "moving_time"))
    climb_m   = fv(row, "total_elevation_gain")
    climb_ft  = int(climb_m * 3.28084)
    activity_type = row.get("type", "")
    is_virtual = activity_type == "VirtualRide"
    venue     = "Zwift" if is_virtual else "outdoor"

    # ── Power ─────────────────────────────────────────────────────────
    ftp       = fv(row, "icu_ftp") or FTP
    np_w      = int(fv(row, "icu_normalized_watts"))
    avg_w     = int(fv(row, "icu_average_watts"))
    vi        = round(fv(row, "icu_variability"), 2)
    if_val    = round(fv(row, "icu_intensity") / 100, 2)  # stored as pct
    eftp      = int(fv(row, "icu_eftp"))
    ss_secs   = fv(row, "sweet_spot_secs")

    # ── HR ────────────────────────────────────────────────────────────
    avg_hr    = int(fv(row, "average_heartrate"))
    max_hr    = int(fv(row, "max_heartrate"))
    ef        = round(fv(row, "icu_efficiency"), 2)
    hrrc      = int(fv(row, "icu_hrrc")) if row.get("icu_hrrc", "").strip() else 0

    # ── Load / fitness ────────────────────────────────────────────────
    load      = int(fv(row, "icu_training_load"))
    trimp     = int(fv(row, "hr_load"))
    ctl       = fv(row, "icu_fitness")
    atl       = fv(row, "icu_fatigue")
    form      = int(round(ctl - atl))
    weight    = fv(row, "icu_weight")
    cal       = int(fv(row, "calories"))

    # ── Zone distributions ────────────────────────────────────────────
    hr_keys  = ["hr_z1_secs","hr_z2_secs","hr_z3_secs","hr_z4_secs","hr_z5_secs"]
    pw_keys  = ["z1_secs","z2_secs","z3_secs","z4_secs","z5_secs","z6_secs","z7_secs"]
    hr_pcts  = zone_pcts(row, hr_keys)
    pw_pcts  = zone_pcts(row, pw_keys)

    # SS% of total power time
    pw_total = sum(fv(row, k) for k in pw_keys)
    ss_pct   = f"{ss_secs/pw_total*100:.1f}%" if pw_total > 0 else "0%"

    hr_str   = " | ".join(f"Z{i+1} {p}" for i, p in enumerate(hr_pcts))
    pwr_str  = " | ".join(f"Z{i+1} {p}" for i, p in enumerate(pw_pcts))

    # ── HRRc note ─────────────────────────────────────────────────────
    hrrc_str = f" | HRRc {hrrc}" if hrrc > 0 else ""

    # ── eFTP note — only show if meaningfully different from FTP ──────
    eftp_str = f" | eFTP {eftp}W" if eftp and abs(eftp - ftp) > 2 else ""

    # ── Assemble ──────────────────────────────────────────────────────
    lines = [
        f"--- {date_str} | {name} | {dur} | {climb_ft}ft | {venue} ---",
        f"Load {load} | TRIMP {trimp} | NP {np_w}W | Avg {avg_w}W | VI {vi} | IF {if_val}",
        f"Avg HR {avg_hr} | Max HR {max_hr} | EF {ef}{hrrc_str} | Form {form:+d} | {weight}kg",
        f"SS {ss_pct} | Cal {cal}{eftp_str}",
        "",
        f"HR:  {hr_str}",
        f"PWR: {pwr_str}",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compact Intervals.icu summary for Claude.")
    parser.add_argument("--days",  type=int, default=7)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--copy",  action="store_true", help="Copy to clipboard (macOS)")
    args = parser.parse_args()

    if API_KEY == "YOUR_API_KEY_HERE" or ATHLETE_ID == "YOUR_ATHLETE_ID_HERE":
        print("ERROR: Set INTERVALS_API_KEY and INTERVALS_ATHLETE_ID env vars.")
        sys.exit(1)

    now    = datetime.now(timezone.utc)
    oldest = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")
    newest = now.strftime("%Y-%m-%d")

    print(f"Fetching {args.days} days ({oldest} → {newest})...", file=sys.stderr)

    rows = fetch_csv(
        f"athlete/{ATHLETE_ID}/activities.csv?oldest={oldest}&newest={newest}"
    )

    if not rows:
        print("No activities found.", file=sys.stderr)
        sys.exit(0)

    # Filter to date range and non-empty activities
    rows = [r for r in rows
            if oldest <= r.get("start_date_local","")[:10] <= newest
            and fv(r, "moving_time") > 0]

    # Sort oldest → newest
    rows.sort(key=lambda r: r.get("start_date_local", ""))

    if args.count:
        rows = rows[-args.count:]

    print(f"Found {len(rows)} activities.", file=sys.stderr)

    if not rows:
        print("No activities in date range.", file=sys.stderr)
        sys.exit(0)

    last = rows[-1]
    header = (
        f"=== Intervals.icu | {ATHLETE_ID} | "
        f"FTP {int(fv(last,'icu_ftp'))}W | LTHR {LTHR} | MaxHR {MAX_HR} | "
        f"{now.strftime('%a %b %-d %Y')} ===\n"
        f"{'─' * 62}"
    )

    blocks  = [format_activity(r) for r in rows]
    output  = header + "\n\n" + "\n\n".join(blocks)

    print(output)

    if args.copy:
        try:
            subprocess.run(["pbcopy"], input=output.encode(), check=True)
            print("\n✓ Copied to clipboard.", file=sys.stderr)
        except Exception as e:
            print(f"Could not copy: {e}", file=sys.stderr)

    est_tokens = len(output) // 4
    print(f"\n≈ {est_tokens} tokens | {len(rows)} activities", file=sys.stderr)


if __name__ == "__main__":
    main()
