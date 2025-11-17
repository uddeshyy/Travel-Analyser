import os
import json
import requests
from datetime import datetime
import pytz

API_KEY = os.getenv("GOOGLE_MAPS_KEY")

# Correct coordinates (not URLs)
LOC = {
    "Kharadi": "18.5376206,73.936613",
    "Keshav Nagar": "18.5306004,73.9454019",
    "Office": "18.5502336,73.8942478"
}

DATA_FILE = "data.json"

# Identify which cron ran (GitHub may delay, so use ranges)
MORNING_RANGE = range(9, 13)     # Cron scheduled 10:15–10:35 (buffer allowed)
EVENING_RANGE = range(16, 20)     # Cron scheduled 17:00–18:00 (buffer allowed)


# ----------------------------- FILE HANDLING ----------------------------- #

def load_data():
    # If file missing, create blank
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f, indent=2)

    # Load file content
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    # Ensure "global" is initialized
    if "global" not in data:
        data["global"] = {
            "Kharadi_to_office": {"count": 0, "total": 0, "avg": None, "min": None, "max": None},
            "office_to_Kharadi": {"count": 0, "total": 0, "avg": None, "min": None, "max": None},
            "Keshav Nagar_to_office": {"count": 0, "total": 0, "avg": None, "min": None, "max": None},
            "office_to_Keshav Nagar": {"count": 0, "total": 0, "avg": None, "min": None, "max": None}
        }

    return data


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ----------------------------- API CALL ----------------------------- #

def get_travel_time(origin, destination):
    url = (
        "https://maps.googleapis.com/maps/api/directions/json"
        f"?origin={origin}&destination={destination}"
        "&departure_time=now"
        f"&key={API_KEY}"
    )

    resp = requests.get(url).json()

    try:
        secs = resp["routes"][0]["legs"][0]["duration_in_traffic"]["value"]
        return round(secs / 60)
    except:
        print("⚠️ API error:", resp)
        return None


# ----------------------------- UPDATE DAILY DATA ----------------------------- #

def record_sample(day_data, entry_key, value, global_stats):
    if entry_key not in day_data:
        day_data[entry_key] = {
            "samples": [],
            "min": None,
            "max": None,
            "avg": None
        }

    entry = day_data[entry_key]

    if value is not None:
        entry["samples"].append(value)

    if len(entry["samples"]) == 3:
        s = entry["samples"]
        entry["min"] = min(s)
        entry["max"] = max(s)
        entry["avg"] = round(sum(s) / 3)
        entry["samples"] = []

        # --- UPDATE GLOBAL STATS ---
        g = global_stats[entry_key]

        # Global min
        if g["min"] is None or entry["avg"] < g["min"]:
            g["min"] = entry["avg"]

        # Global max
        if g["max"] is None or entry["avg"] > g["max"]:
            g["max"] = entry["avg"]

        # Global avg
        g["count"] += 1
        g["total"] += entry["avg"]
        g["avg"] = round(g["total"] / g["count"])



# ----------------------------- MAIN LOGIC ----------------------------- #

def main():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    hour = now.hour

    # Determine which window this run belongs to
    is_morning = hour in MORNING_RANGE
    is_evening = hour in EVENING_RANGE

    if not (is_morning or is_evening):
        print("⏭ Not a relevant cron window. Skipping.")
        return

    # Load DB
    db = load_data()
    date_str = now.strftime("%Y-%m-%d")

    if date_str not in db:
        db[date_str] = {}

    today = db[date_str]

    # ---------------- MORNING RUN ---------------- #
    if is_morning:
        print("🌅 Morning sample")

        for home in ["Kharadi", "Keshav Nagar"]:
            t = get_travel_time(LOC[home], LOC["Office"])
            record_sample(today, f"{home}_to_office", t, db["global"])

    # ---------------- EVENING RUN ---------------- #
    if is_evening:
        print("🌇 Evening sample")

        for home in ["Kharadi", "Keshav Nagar"]:
            t = get_travel_time(LOC["Office"], LOC[home])
            record_sample(today, f"office_to_{home}", t, db["global"])

    save_data(db)
    print("✔ Data updated for", date_str)


if __name__ == "__main__":
    main()
