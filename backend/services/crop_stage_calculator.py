"""
File: crop_stage_calculator.py
Purpose: Calculates current growth stage of a crop based on sowing date and crop calendar.
Inputs:  crop_name (str), sowing_date (str 'YYYY-MM-DD' or datetime object)
Outputs: Dict containing stage (str), days_since_sowing (int), stage_description (str)
Usage:   from services.crop_stage_calculator import calculate_crop_stage
         stage_info = calculate_crop_stage("Cotton", sowing_date="2026-07-01")
"""

import datetime
from models.crop_calendar_model import CropCalendarModel

def calculate_crop_stage(crop_name, sowing_date=None):
    """
    Calculates crop growth stage given crop and sowing date.

    Parameters:
        crop_name (str): Name of crop
        sowing_date (str | date | datetime): Date when crop was sown. Defaults to 45 days ago.

    Returns:
        dict: {crop, stage, days_since_sowing, valid_until}
    """
    today = datetime.date.today()

    if isinstance(sowing_date, str):
        try:
            sow_dt = datetime.datetime.strptime(sowing_date.split("T")[0], "%Y-%m-%d").date()
        except ValueError:
            sow_dt = today - datetime.timedelta(days=50) # Fallback ~50 days ago (vegetative/flowering)
    elif isinstance(sowing_date, (datetime.date, datetime.datetime)):
        sow_dt = sowing_date if isinstance(sowing_date, datetime.date) else sowing_date.date()
    else:
        # Default assumption: Sown 50 days ago (mid vegetative/flowering stage)
        sow_dt = today - datetime.timedelta(days=50)

    days_since_sowing = max(0, (today - sow_dt).days)
    stages = CropCalendarModel.get_stages_for_crop(crop_name)

    current_stage = "vegetative"
    for stage_name, (start_day, end_day) in stages.items():
        if start_day <= days_since_sowing <= end_day:
            current_stage = stage_name
            break

    return {
        "crop": crop_name,
        "stage": current_stage,
        "days_since_sowing": days_since_sowing,
        "sowing_date": sow_dt.isoformat()
    }
