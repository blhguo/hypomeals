"""
This file defines some constants (e.g., units) used throughout the project
"""
from datetime import time

MASS_BASED_UNITS = {
    "kg": {
        "verbose_name": "Kilogram",
        "is_base": True,
        "scale_factor": 1.0,
    },
    "g": {
        "verbose_name": "Gram",
        "is_base": False,
        "scale_factor": 0.001,
    },
    "lb.": {
        "verbose_name": "Pound",
        "is_base": False,
        "scale_factor": 0.453592,
    },
    "oz.": {
        "verbose_name": "Ounce",
        "is_base": False,
        "scale_factor": 0.0283495,
    },
    "ton": {
        "verbose_name": "Imperial Ton",
        "is_base": False,
        "scale_factor": 1016.04608,
    }
}

VOLUME_BASED_UNITS = {
    "fl. oz.": {
        "verbose_name": "Fluid Ounce",
        "is_base": False,
        "scale_factor": 2.95735e-5,
    },
    "pt.": {
        "verbose_name": "Pint",
        "is_base": False,
        "scale_factor": 0.000473176,
    },
    "qt.": {
        "verbose_name": "Quart",
        "is_base": False,
        "scale_factor": 0.000946352,
    },
    "gal.": {
        "verbose_name": "U.S. Liquid Gallon",
        "is_base": False,
        "scale_factor": 0.003785408,
    },
    "mL": {
        "verbose_name": "Milliliter",
        "is_base": False,
        "scale_factor": 1e-6,
    },
    "L": {
        "verbose_name": "Liter",
        "is_base": False,
        "scale_factor": 1e-3,
    },
    "m3": {
        "verbose_name": "Cubic meter",
        "is_base": True,
        "scale_factor": 1,
    }
}

COUNT_BASED_UNITS = {
    "ct": {
        "verbose_name": "Count",
        "is_base": True,
        "scale_factor": 1,
    }
}

UNITS = {
    "mass": MASS_BASED_UNITS,
    "volume": VOLUME_BASED_UNITS,
    "count": COUNT_BASED_UNITS,
}

WORK_HOURS_START = time(hour=8)
WORK_HOURS_END = time(hour=18)
WORK_HOURS_PER_DAY = 10  # Per req. 4.4.4, factories run 10 hours per day
HOURS_PER_DAY = 24
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = SECONDS_PER_HOUR * 24
