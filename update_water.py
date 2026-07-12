"""Refresh water.json from the EPA Bathing Water API (which has no CORS,
so the page can't fetch it directly). Run by the scheduled workflow."""
import json
from datetime import datetime, timezone

import requests

EPA = "https://data.epa.ie/bw/api/v1"
DLR = {
    "IEEABWC090_0000_0100": "Seapoint",
    "IEEABWC090_0000_0040": "Forty Foot",
    "IEEABWC090_0000_0050": "Sandycove",
    "IEEABWC090_0000_0060": "Dun Laoghaire Baths",
    "IEEABWC100_0000_0400": "Killiney",
    "IEEABWC100_0000_0450": "White Rock",
    "BPNBF100000060001": "Coliemore Harbour",
    "BPNBF100000070001": "Blackrock Baths",
    "BPNBF100000080001": "Corbawn Lane",
}


def main():
    per_page = 100
    count = requests.get(f"{EPA}/measurements?per_page=1", timeout=30).json()["count"]
    last_page = (count + per_page - 1) // per_page
    latest = {}
    for page in range(last_page, max(last_page - 6, 0), -1):
        r = requests.get(
            f"{EPA}/measurements?per_page={per_page}&page={page}", timeout=30)
        r.raise_for_status()
        for x in r.json()["list"]:
            b = x["beach_id"]
            if b in DLR and (b not in latest or x["result_date"] > latest[b]["result_date"]):
                latest[b] = x

    alerts = []
    r = requests.get(f"{EPA}/alerts?per_page=100", timeout=30)
    r.raise_for_status()
    for x in r.json()["list"]:
        if (x["beach_id"] in DLR
                and x.get("has_bathing_restriction_in_place") == "Yes"
                and not x.get("incident_end_date")):
            alerts.append({
                "beach": DLR[x["beach_id"]],
                "type": x.get("bathing_restriction_type") or "Bathing restriction",
            })

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tested": max(x["result_date"] for x in latest.values()) if latest else None,
        "beaches": [
            {"name": DLR[b], "status": x["sample_water_quality_status"],
             "tested": x["result_date"]}
            for b, x in sorted(latest.items(), key=lambda kv: DLR[kv[0]])
        ],
        "alerts": alerts,
    }
    with open("water.json", "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
