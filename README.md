# intervals-claude-summary

A Python script that pulls your recent [Intervals.icu](https://intervals.icu) activities and formats them into a compact, token-efficient summary for pasting into Claude (or any AI) for training analysis.

**One command. Clipboard ready. ~100 tokens per activity.**

---

## Example output

```
=== Intervals.icu | i12345 | FTP 123W | LTHR 123 | MaxHR 123 | Fri Apr 24 2026 ===
──────────────────────────────────────────────────────────────

--- Tue Apr 21 | Race: Stage 3: Pas Racing: Yumezi Grit (C) | 0:36 | 767ft | Zwift ---
Load 54 | TRIMP 52 | NP 230W | Avg 224W | VI 1.03 | IF 0.95
Avg HR 155 | Max HR 168 | EF 1.48 | HRRc 28 | Form +1 | 75.5kg
SS 31.7% | Cal 484

HR:  Z1 0.0% | Z2 0.0% | Z3 22.7% | Z4 77.2% | Z5 0.0%
PWR: Z1 1.1% | Z2 12.6% | Z3 35.6% | Z4 29.2% | Z5 14.2% | Z6 7.3% | Z7 0.0%

--- Wed Apr 22 | Pacer Group Ride with Coco | 1:07 | 239ft | Zwift ---
Load 55 | TRIMP 42 | NP 170W | Avg 165W | VI 1.03 | IF 0.70
Avg HR 123 | Max HR 135 | EF 1.38 | Form +2 | 75.45kg
SS 4.9% | Cal 642 | eFTP 240W

HR:  Z1 3.8% | Z2 94.1% | Z3 2.1% | Z4 0.0% | Z5 0.0%
PWR: Z1 5.9% | Z2 72.4% | Z3 20.0% | Z4 1.7% | Z5 0.0% | Z6 0.0% | Z7 0.0%
```

A full week of ~8 activities comes in at ~725 tokens — compared to 15,000+ tokens when manually pasting summary data and FIT files.

---

## Requirements

- macOS (tested on macOS 14+)
- Python 3.8+
- [Homebrew](https://brew.sh) curl — macOS system curl has HTTP/2 issues in subprocess contexts
- Intervals.icu account with API access

---

## Installation

### 1. Install Homebrew curl

```bash
brew install curl
```

### 2. Get your API key and athlete ID

1. Go to **intervals.icu → Settings → Developer Settings** (bottom of page)
2. Generate an API key and copy it
3. Your athlete ID is in your profile URL: `intervals.icu/athlete/i123456/` → your ID is `i123456`

### 3. Download the script

Create a permanent home for the script:

```bash
mkdir -p ~/Library/intervals.icu
```

Download `intervals_summary.py` and save it to `~/Library/intervals.icu/intervals_summary.py`

### 4. Configure ~/.zshrc

Open `~/.zshrc` in a text editor and add these lines — **copy/paste your API key, don't retype it:**

```bash
export INTERVALS_API_KEY="your_actual_api_key_here"
export INTERVALS_ATHLETE_ID="your_actual_athlete_id_here"
alias icu='python3 ~/Library/intervals.icu/intervals_summary.py --days 7 --copy'
```

Reload your shell:

```bash
source ~/.zshrc
```

### 5. Run it

```bash
icu
```

Output is printed to terminal and automatically copied to your clipboard. Paste into Claude with **Cmd+V**.

---

## Usage

```bash
# Default — last 7 days, copy to clipboard
icu

# Last 14 days
python3 ~/Library/intervals.icu/intervals_summary.py --days 14 --copy

# Last 5 activities regardless of date
python3 ~/Library/intervals.icu/intervals_summary.py --count 5 --copy

# Print only, no clipboard copy
python3 ~/Library/intervals.icu/intervals_summary.py --days 7
```

---

## Fields included

| Field | Description |
|---|---|
| Load | Training load (TSS equivalent) |
| TRIMP | HR-based training load |
| NP | Normalized power |
| Avg | Average power |
| VI | Variability index |
| IF | Intensity factor (NP / FTP) |
| Avg HR / Max HR | Heart rate |
| EF | Efficiency factor (power/HR ratio) |
| HRRc | Heart rate recovery — shown on hard days only |
| Form | CTL − ATL (fitness minus fatigue) |
| Weight | Body weight in kg |
| SS% | Sweet spot time as % of ride |
| Cal | Calories burned |
| eFTP | Estimated FTP from activity — shown when meaningfully different from set FTP |
| HR Z1–Z5 | Time in each HR zone as % |
| PWR Z1–Z7 | Time in each power zone as % |

> **Note:** W'bal drop is not available in the Intervals.icu CSV export. It is calculated dynamically in the UI only.

---

## Troubleshooting

### 403 Access Denied

Your API key is wrong or not being passed to the script. Verify:

```bash
python3 -c "import os; print(os.environ.get('INTERVALS_API_KEY', 'NOT SET'))"
```

Common cause: typo in `~/.zshrc`. **Always copy/paste the API key directly from Intervals.icu settings** — do not retype it. One wrong character (`x` vs nothing, `l` vs `1`) will cause a silent 403.

### Activities not showing / 403 for Strava-sourced activities

Strava's API terms prohibit Intervals.icu from forwarding Strava activity data through their own API. If your activities were imported via Strava:

1. Go to **Intervals.icu → Settings → Download Old Data**
2. This imports your data directly into Intervals.icu storage, making it API-accessible

### Wrong activity count

The API sometimes ignores date range parameters and returns full history. The script filters client-side so only activities within your requested date range are shown.

### Script not found after setting alias

Check that the path in your alias matches exactly where you saved the file — macOS paths are case-sensitive (`Library` not `library`).

### rc=56 errors with system curl

This is a known macOS system curl HTTP/2 issue in subprocess contexts. The fix is Homebrew curl:

```bash
brew install curl
```

The script uses `/opt/homebrew/opt/curl/bin/curl` explicitly for this reason.

---

## Notes

- **EF comparability:** Efficiency Factor is most meaningful when comparing the same activity type. Outdoor and Zwift EF numbers are not directly comparable due to coasting, drafting, and terrain effects.
- **Zone accuracy:** HR and power zones reflect whatever boundaries you have configured in Intervals.icu. Make sure your FTP and LTHR are set correctly for meaningful zone distributions.
- **Zwift detection:** Activities are classified as `Zwift` if the activity type is `VirtualRide`, regardless of the trainer flag (which Zwift sets inconsistently for race events).

---

## License

MIT — use freely, share widely.
