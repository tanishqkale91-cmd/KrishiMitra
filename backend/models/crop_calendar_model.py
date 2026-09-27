"""
File: crop_calendar_model.py
Purpose: Crop growth calendar data lookup table defining duration of stages for crops.
Inputs:  crop_name (str)
Outputs: Dict of growth stages with day ranges from sowing date
Usage:   from models.crop_calendar_model import CropCalendarModel
         stages = CropCalendarModel.get_stages_for_crop("Cotton")
"""

CROP_STAGE_CALENDARS = {
    "cotton": {
        "sowing": (0, 15),
        "seedling": (16, 35),
        "vegetative": (36, 60),
        "flowering": (61, 100),
        "pre-harvest": (101, 150),
        "post-harvest": (151, 999)
    },
    "soybean": {
        "sowing": (0, 10),
        "seedling": (11, 25),
        "vegetative": (26, 45),
        "flowering": (46, 75),
        "pre-harvest": (76, 105),
        "post-harvest": (106, 999)
    },
    "wheat": {
        "sowing": (0, 12),
        "seedling": (13, 30),
        "vegetative": (31, 60),
        "flowering": (61, 90),
        "pre-harvest": (91, 120),
        "post-harvest": (121, 999)
    },
    "onion": {
        "sowing": (0, 15),
        "seedling": (16, 40),
        "vegetative": (41, 80),
        "flowering": (81, 110),
        "pre-harvest": (111, 140),
        "post-harvest": (141, 999)
    },
    "tur": {
        "sowing": (0, 15),
        "seedling": (16, 35),
        "vegetative": (36, 75),
        "flowering": (76, 130),
        "pre-harvest": (131, 180),
        "post-harvest": (181, 999)
    },
    "gram": {
        "sowing": (0, 10),
        "seedling": (11, 25),
        "vegetative": (26, 55),
        "flowering": (56, 85),
        "pre-harvest": (86, 115),
        "post-harvest": (116, 999)
    },
    "default": {
        "sowing": (0, 14),
        "seedling": (15, 30),
        "vegetative": (31, 60),
        "flowering": (61, 90),
        "pre-harvest": (91, 120),
        "post-harvest": (121, 999)
    }
}

class CropCalendarModel:
    """Crop Growth Calendar Lookup Model"""

    @staticmethod
    def get_stages_for_crop(crop_name):
        """
        Retrieves growth stage day ranges for a given crop.
        Normalizes names like 'Cotton (कपास / कापूस)' to key 'cotton'.
        """
        if not crop_name:
            return CROP_STAGE_CALENDARS["default"]

        normalized = crop_name.lower()
        for key in CROP_STAGE_CALENDARS:
            if key != "default" and key in normalized:
                return CROP_STAGE_CALENDARS[key]

        return CROP_STAGE_CALENDARS["default"]
