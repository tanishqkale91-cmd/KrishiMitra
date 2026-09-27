"""
File: weather_advisory_engine.py
Purpose: Evaluates explicit, rule-based agronomic alerts from weather forecast & crop growth stage.
Inputs:  mandi_id (int), crop_name (str), sowing_date (str/date)
Outputs: List of triggered alert dictionaries [{alert_type, message_text, severity, crop, valid_until}]
Usage:   from services.weather_advisory_engine import generate_weather_advisories
         advisories = generate_weather_advisories(mandi_id=1, crop_name="Cotton")
"""

import datetime
from models.mandi_model import MandiModel
from services.weather_fetch_service import get_weather_forecast
from services.crop_stage_calculator import calculate_crop_stage

def generate_weather_advisories(mandi_id=1, crop_name="Cotton", sowing_date=None):
    """
    Evaluates deterministic agronomic rules combining weather forecast data and crop growth stage.

    Parameters:
        mandi_id (int): Mandi location ID
        crop_name (str): Crop name
        sowing_date (str): Sowing date (optional)

    Returns:
        list: Triggered advisory dictionaries [{alert_type, message_text, severity, crop, valid_until}]
    """
    mandi = MandiModel.get_by_id(mandi_id)
    lat = mandi.get("latitude", 21.1458) if mandi else 21.1458
    lon = mandi.get("longitude", 79.0882) if mandi else 79.0882

    weather = get_weather_forecast(lat=lat, lon=lon, mandi_id=mandi_id)
    stage_info = calculate_crop_stage(crop_name, sowing_date=sowing_date)
    stage = stage_info["stage"]

    alerts = []
    today = datetime.date.today()
    valid_48h = (today + datetime.timedelta(days=2)).isoformat()
    valid_24h = (today + datetime.timedelta(days=1)).isoformat()

    # Rule 1: High Rainfall & Spraying Delay Rule
    if weather["rainfall_prob_48h"] >= 70.0 and stage in ["flowering", "pre-harvest", "vegetative"]:
        alerts.append({
            "alert_type": "Rainfall & Spraying Warning",
            "severity": "urgent", # red
            "message_text": f"Rain probability is {weather['rainfall_prob_48h']}% in 48 hours for your region. Delay pesticide or fertilizer spraying to prevent chemical runoff.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_48h
        })

    # Rule 2: Heatwave & Irrigation Management Rule
    if weather["max_temp"] >= 38.0 and weather["no_rainfall_last_5_days"] and stage in ["vegetative", "flowering", "seedling"]:
        alerts.append({
            "alert_type": "Heatwave & Irrigation Alert",
            "severity": "urgent", # red
            "message_text": f"High temperature alert ({weather['max_temp']}°C). Irrigate your crop during early morning or evening. Avoid midday irrigation to prevent crop thermal stress.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_48h
        })

    # Rule 3: Frost Risk Protection Rule
    if weather.get("frost_risk_flag", False) or (weather["min_temp"] <= 5.0 and stage in ["seedling", "sowing"]):
        alerts.append({
            "alert_type": "Frost Protection Warning",
            "severity": "urgent", # red
            "message_text": f"Low temperature alert ({weather['min_temp']}°C) with frost risk. Protect young seedlings using straw mulching or light evening soil moistening.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_24h
        })

    # Rule 4: High Humidity & Fungal Outbreak Advisory
    if weather["humidity"] >= 80.0 and 18.0 <= weather["max_temp"] <= 33.0 and stage in ["vegetative", "flowering"]:
        alerts.append({
            "alert_type": "Fungal Disease Advisory",
            "severity": "advisory", # yellow
            "message_text": f"High relative humidity ({weather['humidity']}%) detected. Warm and humid conditions favor fungal blight and leaf spot. Inspect crop foliage daily.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_48h
        })

    # Rule 5: Optimum Harvest Window Advisory
    if stage == "pre-harvest" and weather["rainfall_prob_48h"] < 30.0 and weather["max_temp"] < 38.0:
        alerts.append({
            "alert_type": "Optimal Harvest Window",
            "severity": "info", # blue/green
            "message_text": f"Weather forecast is favorable with low rain risk ({weather['rainfall_prob_48h']}%). Excellent window for crop harvesting and threshing.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_48h
        })

    # If no severe rules fired, add general weather condition summary
    if not alerts:
        alerts.append({
            "alert_type": "Weather Advisory Normal",
            "severity": "info",
            "message_text": f"Weather conditions normal (Temp: {weather['max_temp']}°C, Rain Chance: {weather['rainfall_prob_48h']}%). Regular agronomic operations can proceed.",
            "crop": crop_name,
            "crop_stage": stage,
            "valid_until": valid_48h
        })

    return alerts
