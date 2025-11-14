import os
import json
import requests
from datetime import datetime
import pytz

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_KEY")

LOCATIONS = {
    "Kharadi": "https://maps.app.goo.gl/Pi2D1gHqti2KnEHi7",
    "Keshav Nagar": "https://maps.app.goo.gl/ppPj8oV5NtmpYJCL8",
    "Office": "https://maps.app.goo.gl/AeSGAWAALwTvWETK6"
}

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "Kharadi": {
                "home_to_office": {"min": None, "max": None, "avg": None, "count": 0, "total": 0},
                "office_to_home": {"min": None, "max": None, "avg": None, "count": 0, "total": 0}
            },
            "Keshav Nagar": {
                "home_to_office": {"min": None, "max": None, "avg": None, "count": 0, "total": 0},
                "office_to_home": {"min": None, "max": None, "avg": None, "count": 0, "total": 0}
            }
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_travel_time(origin, destination):
    url = (
        f"https://maps.googleapis.com/maps/api/directions/json"
        f"?origin={origin}&destination={destination}&key={GOOGLE_API_KEY}"
    )
    response = requests.get(url).json()
    return response["routes"][0]["legs"][0]["duration"]["value"] / 60  # minutes


def compute_3_sample_avg(origin, destination):
    samples = [get_travel_time(origin, destination) for _ in range(3)]
    return sum(samples) / len(samples)


def update_stats(stats_dict, new_value):
    if stats_dict["min"] is None or new_value < stats_dict["min"]:
        stats_dict["min"] = new_value

    if stats_dict["max"] is None or new_value > stats_dict["max"]:
        stats_dict["max"] = new_value

    stats_dict["count"] += 1
    stats_dict["total"] += new_value
    stats_dict["avg"] = stats_dict["total"] / stats_dict["count"]


def main():
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    hour = now.hour
    minute = now.minute

    data = load_data()

    # Determine which job is running
    is_morning = (hour == 10 and minute in [15, 25, 35])
    is_evening = ((hour == 17 and minute == 0) or (hour == 17 and minute == 30) or (hour == 18 and minute == 0))

    if not (is_morning or is_evening):
        print("Not a scheduled sample time.")
        return

    for home in ["Kharadi", "Keshav Nagar"]:
        if is_morning:
            avg_val = compute_3_sample_avg(LOCATIONS[home], LOCATIONS["Office"])
            update_stats(data[home]["home_to_office"], avg_val)

        if is_evening:
            avg_val = compute_3_sample_avg(LOCATIONS["Office"], LOCATIONS[home])
            update_stats(data[home]["office_to_home"], avg_val)

    save_data(data)
    print("Updated data:", data)


if __name__ == "__main__":
    main()
