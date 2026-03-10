"""
ehr_parser.parser
-----------------
High-level functions that orchestrate extraction across one or more
EHR text files and assemble the results into a DataFrame.
"""

from pathlib import Path

import pandas as pd

from .extractors import extract_irb_protocol, extract_patient_id, extract_record_date
from .scan import find_scan_paths
from .transform import melt_df


# Registry of core extractors used by parse_ehr.
# Extend this dict to have parse_ehr pick up new fields automatically.
EXTRACTORS: dict[str, callable] = {
    "patient_id": extract_patient_id,
    "irb_protocol": extract_irb_protocol,
    "record_date": extract_record_date,
}


def parse_ehr(texts: list[str]) -> dict:
    """
    Run each registered extractor against a list of EHR text strings.
    Once a field gets a non-None value it is considered complete and
    skipped for remaining texts.
    """
    results = {field: None for field in EXTRACTORS}

    for text in texts:
        pending = {
            field: fn
            for field, fn in EXTRACTORS.items()
            if results[field] is None
        }
        if not pending:
            break

        for field, fn in pending.items():
            value = fn(text)
            if value is not None:
                results[field] = value

    return results


def build_dataframe(file_paths: list[str | Path]) -> pd.DataFrame:
    """
    Read every EHR file in *file_paths*, extract header fields, locate
    associated scans, and return a long-form DataFrame with one row per
    patient–modality combination.

    Example
    -------
    >>> from pathlib import Path
    >>> files = Path("records/").glob("*.txt")
    >>> df = build_dataframe(list(files))
    """
    rows: list[dict] = []

    for path in file_paths:
        with open(path, "r") as fh:
            text = fh.readlines()
        row = parse_ehr(text)
        row["path_ehr"] = str(path)
        rows.append(row)

    return melt_df(find_scan_paths(pd.DataFrame(rows)))
