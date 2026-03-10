"""
ehr_parser
==========
Extract structured data from Electronic Health Record (EHR) text files.

Quick start
-----------
>>> from ehr_parser import build_dataframe
>>> df = build_dataframe(["patient_001.txt", "patient_002.txt"])
"""

from .extractors import (
    extract_age,
    extract_blood_pressure,
    extract_conditions,
    extract_heart_rate,
    extract_irb_protocol,
    extract_medications,
    extract_notes,
    extract_patient_id,
    extract_record_date,
    extract_sex,
    extract_weight,
)
from .parser import build_dataframe, parse_ehr
from .scan import find_scan_paths
from .transform import melt_df

__all__ = [
    # extractors
    "extract_patient_id",
    "extract_irb_protocol",
    "extract_record_date",
    "extract_age",
    "extract_sex",
    "extract_conditions",
    "extract_medications",
    "extract_blood_pressure",
    "extract_heart_rate",
    "extract_weight",
    "extract_notes",
    # scan
    "find_scan_paths",
    # transform
    "melt_df",
    # parser
    "parse_ehr",
    "build_dataframe",
]
