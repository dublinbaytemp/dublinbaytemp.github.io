"""Refresh water.json from the EPA Bathing Water API (which has no CORS,
so the page can't fetch it directly). Run by the scheduled workflow.
Beaches listed north-to-south around Dublin Bay, grouped by shore."""
import json
from datetime import datetime, timezone

import requests

EPA = "https://data.epa.ie/bw/api/v1"
# (beach_id, display name, shore zone) — order is the coastline, N to S.
BAY = [
    ("IEEABWC020_0000_0600", "Balbriggan Front Strand", "North County"),
    ("IEEABWC020_0000_0500", "Skerries South Beach", "North County"),
    ("IEEABWC020_0000_0400", "Loughshinny", "North County"),
    ("IEEABWC020_0000_0350", "Rush North Beach", "North County"),
    ("IEEABWC020_0000_0300", "Rush South Beach", "North County"),
    ("IEEABWC020_0000_0200", "Portrane, the Brook", "North County"),
    ("IEEABWC020_0000_0100", "Donabate, Balcarrick", "North County"),
    ("IEEABWC070_0000_0200", "Portmarnock Velvet Strand", "North County"),
    ("IEEABWC070_0000_0100", "Sutton, Burrow Beach", "Howth"),
    ("IEEABWC070_0000_0500", "Claremont Beach", "Howth"),
    ("IEEABWC090_0000_0400", "Dollymount Strand", "North Bay"),
    ("BPNBF070000040003", "North Bull Wall", "North Bay"),
    ("IEEABWC090_0000_0350", "Half Moon", "South Wall & Strands"),
    ("BPNBF070000060001", "Shelley Banks", "South Wall & Strands"),
    ("IEEABWC090_0000_0300", "Sandymount Strand", "South Wall & Strands"),
    ("BPNBF070000020002", "Merrion Strand", "South Wall & Strands"),
    ("BPNBF100000070001", "Blackrock Baths", "South Bay"),
    ("IEEABWC090_0000_0100", "Seapoint", "South Bay"),
    ("IEEABWC090_0000_0060", "Dun Laoghaire Baths", "South Bay"),
    ("IEEABWC090_0000_0050", "Sandycove", "South Bay"),
    ("IEEABWC090_0000_0040", "Forty Foot", "South Bay"),
    ("BPNBF100000060001", "Coliemore Harbour", "South Bay"),
    ("IEEABWC100_0000_0450", "White Rock", "Killiney Bay"),
    ("IEEABWC100_0000_0400", "Killiney", "Killiney Bay"),
    ("BPNBF100000080001", "Corbawn Lane", "Killiney Bay"),
]
IDS = {b[0] for b in BAY}


def main():
    per_page = 100
    count = requests.get(f"{EPA}/measurements?per_page=1", timeout=30).json()["count"]
    last_page = (count + per_page - 1) // per_page
    latest = {}
    for page in range(last_page, max(last_page - 8, 0), -1):
        r = requests.get(
            f"{EPA}/measurements?per_page={per_page}&page={page}", timeout=30)
        r.raise_for_status()
        for x in r.json()["list"]:
            b = x["beach_id"]
            if b in IDS and (b not in latest or x["result_date"] > latest[b]["result_date"]):
                latest[b] = x

    alerts = []
    r = requests.get(f"{EPA}/alerts?per_page=100", timeout=30)
    r.raise_for_status()
    names = {b[0]: b[1] for b in BAY}
    for x in r.json()["list"]:
        if (x["beach_id"] in IDS
                and x.get("has_bathing_restriction_in_place") == "Yes"
                and not x.get("incident_end_date")):
            alerts.append({
                "beach": names[x["beach_id"]],
                "type": x.get("bathing_restriction_type") or "Bathing restriction",
            })

    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tested": max(x["result_date"] for x in latest.values()) if latest else None,
        "beaches": [
            {"name": name, "shore": shore,
             "status": latest[b]["sample_water_quality_status"] if b in latest else None,
             "tested": latest[b]["result_date"] if b in latest else None}
            for b, name, shore in BAY
        ],
        "alerts": alerts,
    }
    # Hourly runs: skip the write when only the timestamp would change, so
    # the workflow's commit step stays quiet (no page reads "updated").
    try:
        with open("water.json") as f:
            prev = json.load(f)
    except Exception:
        prev = None
    if prev is not None and all(
        prev.get(k) == out[k] for k in out if k != "updated"
    ):
        print("water.json unchanged — not rewriting.")
        return
    with open("water.json", "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
