"""Regenerate records-data.json for the records page from the Irish Lights
public ERDDAP archive (hourly since Feb 2014; 2015 excluded — unreliable
sensor all year). Cleaning: plausibility bounds then the median-of-
neighbours spike filter. Run weekly by records.yml."""
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone

import requests

IL_ERDDAP = "https://erddap.irishlights.ie/erddap/tabledap/AllMetOcean.csv"
IL_STATION = "%22Dublin%20Bay%20Buoy%20AIS%22"
TEMP_MIN, TEMP_MAX = 2.0, 25.0
EXCLUDE_YEARS = {2015}


def main():
    year_now = datetime.now(timezone.utc).year
    rows = []
    for year in range(2014, year_now + 1):
        if year in EXCLUDE_YEARS:
            continue
        r = requests.get(
            f"{IL_ERDDAP}?time,WaterTemperature&LatonName={IL_STATION}"
            f"&time%3E={year}-01-01T00:00:00Z&time%3C{year+1}-01-01T00:00:00Z",
            timeout=180)
        if r.status_code == 404:
            continue
        r.raise_for_status()
        for line in r.text.strip().split("\n")[2:]:
            t, v = line.split(",")
            try:
                temp = float(v)
            except ValueError:
                continue
            if temp != temp or not (TEMP_MIN <= temp <= TEMP_MAX):
                continue
            rows.append((t, temp))
    rows.sort()

    temps = [t for _, t in rows]
    verified = []
    for i in range(len(rows)):
        lo, hi = max(0, i - 2), min(len(rows), i + 3)
        neigh = [temps[j] for j in range(lo, hi) if j != i]
        if neigh and abs(temps[i] - statistics.median(neigh)) <= 1.5:
            verified.append(rows[i])

    def entry(ts, t):
        return {"temp": round(t, 2), "date": ts[:10]}

    month_max, month_min = {}, {}
    band = defaultdict(lambda: [99.0, -99.0])
    this_year = defaultdict(list)
    for ts, t in verified:
        m, md, y = ts[5:7], ts[5:10], int(ts[:4])
        if m not in month_max or t > month_max[m]["temp"]:
            month_max[m] = entry(ts, t)
        if m not in month_min or t < month_min[m]["temp"]:
            month_min[m] = entry(ts, t)
        if y < year_now:
            band[md][0] = min(band[md][0], t)
            band[md][1] = max(band[md][1], t)
        else:
            this_year[md].append(t)

    out = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive_start": verified[0][0][:10],
        "readings": len(verified),
        "all_time_max": entry(*max(verified, key=lambda x: x[1])),
        "all_time_min": entry(*min(verified, key=lambda x: x[1])),
        "month_max": {m: month_max[m] for m in sorted(month_max)},
        "month_min": {m: month_min[m] for m in sorted(month_min)},
        "year": year_now,
        "band": {md: [round(v[0], 2), round(v[1], 2)]
                 for md, v in sorted(band.items()) if v[0] < 99},
        "year_daily": {md: round(statistics.mean(v), 2)
                       for md, v in sorted(this_year.items())},
    }
    with open("records-data.json", "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
