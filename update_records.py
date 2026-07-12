"""Regenerate records-data.json for the records page: glitch-filtered
archive records, a historical min-max band per calendar day (previous
years), and this year's daily means. Run weekly by records.yml."""
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone

import requests

API = "https://api.dublinbaybuoy.com/rest/v1/readings"
KEY = "sb_publishable_R5KkIpbiwNajUyx3I4aewQ_S4NI8hl3"


def main():
    rows, offset = [], 0
    while True:
        r = requests.get(
            f"{API}?select=timestamp,water_temp&water_temp=not.is.null"
            f"&order=timestamp.asc&limit=1000&offset={offset}",
            headers={"apikey": KEY}, timeout=60)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000

    temps = [x["water_temp"] for x in rows]
    verified = []
    for i in range(len(rows)):
        lo, hi = max(0, i - 2), min(len(rows), i + 3)
        neigh = [temps[j] for j in range(lo, hi) if j != i]
        if neigh and abs(temps[i] - statistics.median(neigh)) <= 1.5:
            verified.append((rows[i]["timestamp"], temps[i]))

    year_now = datetime.now(timezone.utc).year

    def entry(ts, t):
        return {"temp": round(t, 2), "date": ts[:10]}

    month_max, month_min = {}, {}
    band = defaultdict(lambda: [99.0, -99.0])   # md -> [min, max], prior years
    this_year = defaultdict(list)               # md -> temps, current year
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
