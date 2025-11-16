import os
import json
import requests
from datetime import datetime
import pytz

API_KEY = os.getenv("GOOGLE_MAPS_KEY")

# Correct coordinates (not URLs)
LOC = {
    "Kharadi": "18.555623,73.935181",
    "Keshav Nagar": "18.542030,73.955960",
    "Office": "18.567139,73.914689"
}

DATA_FILE = "data.json"

# Identify which cron ran (GitHub may delay, so use ranges)
MORNING_RANGE = range(9, 13)     # Cron scheduled 10:15–10:35 (buffer allowed)
EVENING_RANGE = range(16, 20)     # Cron scheduled 17:00–18:00 (buffer allowed)


# ----------------------------- FILE HANDLING ----------------------------- #

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f, indent=2)

    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}


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

def record_sample(day_data, entry_key, value):
    """
    Accumulate samples until 3 are collected, then compute min/max/avg.
    """

    if entry_key not in day_data:
        day_data[entry_key] = {
            "samples": [],
            "min": None,
            "max": None,
            "avg": None
        }

    entry = day_data[entry_key]

    # Save sample only if valid
    if value is not None:
        entry["samples"].append(value)

    # Compute stats when 3 samples are ready
    if len(entry["samples"]) == 3:
        s = entry["samples"]
        entry["min"] = min(s)
        entry["max"] = max(s)
        entry["avg"] = round(sum(s) / 3)
        entry["samples"] = []   # Clear samples after computing


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
            record_sample(today, f"{home}_to_office", t)

    # ---------------- EVENING RUN ---------------- #
    if is_evening:
        print("🌇 Evening sample")

        for home in ["Kharadi", "Keshav Nagar"]:
            t = get_travel_time(LOC["Office"], LOC[home])
            record_sample(today, f"office_to_{home}", t)

    save_data(db)
    print("✔ Data updated for", date_str)


if __name__ == "__main__":
    main()
