import urllib.request
import json
import smtplib
import os
from datetime import datetime, timedelta
from email.message import EmailMessage

EMAIL_SENDER = "chr.roehrs2005@gmail.com"
EMAIL_PASSWORD = os.environ["GMAIL_PASSWORD"]  # kommt sicher aus GitHub Secrets
EMAIL_RECEIVER = "chr-roehrs@web.de"

SPOTS = {
    "Ribnitz-Damgarten": {
        "lat": 54.2422,
        "lon": 12.4567,
        "windfinder_url": "https://de.windfinder.com/forecast/saaler_bodden_saal"
    },
    "Kühlungsborn West": {
        "lat": 54.1492,
        "lon": 11.7232,
        "windfinder_url": "https://de.windfinder.com/forecast/marina_kuehlungsborn"
    },
    "Müritz / Boeker Mühle": {
        "lat": 53.4060,
        "lon": 12.7660,
        "windfinder_url": "https://de.windfinder.com/forecast/mueritz_boeker_muehle"
    }
}

MIN_WIND_KNOTS = 15
MIN_HOURS = 3
START_HOUR = 8
END_HOUR = 18

def get_tomorrow_forecast(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m&forecast_days=3&wind_speed_unit=kn"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Fehler beim Abrufen der Daten: {e}")
        return None

def check_surf_conditions():
    tomorrow = datetime.now().date() + timedelta(days=1)
    good_spots = {}

    for spot_name, details in SPOTS.items():
        print(f"Prüfe Spot: {spot_name}...")
        data = get_tomorrow_forecast(details["lat"], details["lon"])
        if not data:
            continue

        hourly_times = data["hourly"]["time"]
        hourly_wind = data["hourly"]["wind_speed_10m"]

        consecutive_hours = 0
        max_consecutive = 0
        spot_forecast = []

        for t_str, wind in zip(hourly_times, hourly_wind):
            time_obj_utc = datetime.fromisoformat(t_str)
            time_obj_local = time_obj_utc + timedelta(hours=2)

            if time_obj_local.date() == tomorrow and START_HOUR <= time_obj_local.hour <= END_HOUR:
                if wind >= MIN_WIND_KNOTS:
                    consecutive_hours += 1
                    if consecutive_hours > max_consecutive:
                        max_consecutive = consecutive_hours
                    spot_forecast.append(f"- {time_obj_local.strftime('%H:%M')} Uhr: {round(wind, 1)} kn")
                else:
                    consecutive_hours = 0

        if max_consecutive >= MIN_HOURS:
            good_spots[spot_name] = {
                "forecast": spot_forecast,
                "url": details["windfinder_url"]
            }

    return good_spots, tomorrow.strftime("%d.%m.%Y")

def send_email_alert(good_spots, date_str):
    if not good_spots:
        print(f"Morgen ({date_str}) leider nirgendwo ausreichend Wind gefunden.")
        return

    print("Wind gefunden! Sende E-Mail...")
    body = f"Gute Nachrichten! Morgen ({date_str}) sieht es gut aus zum Surfen:\n\n"
    for spot, info in good_spots.items():
        body += f"🏄 {spot}:\n"
        body += "\n".join(info["forecast"])
        body += f"\n👉 Direkt zu Windfinder: {info['url']}\n\n"
    body += "Hang loose!"

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = f"🌊 Surf-Alarm für morgen ({date_str})!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("E-Mail erfolgreich gesendet!")
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")

if __name__ == "__main__":
    spots_to_surf, forecast_date = check_surf_conditions()
    send_email_alert(spots_to_surf, forecast_date)
