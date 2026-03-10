"""
ehr_parser.py
-------------
Functions to extract structured data from Electronic Health Record (EHR) text files.
Each function accepts the raw EHR text string and returns the extracted value(s).
Use `parse_ehr()` to extract all fields at once into a dict, ready for a DataFrame row.
"""

# Imports
from pathlib import Path
import pandas as pd
import numpy as np


# ── Header / metadata ──────────────────────────────────────────────────────────

# Function: Extract Patient IDs
def extract_patient_id(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip().lower().startswith("patient id"):
            return line.split(":")[-1].strip()
    return None


# Function: Extract IRB Protocol
def extract_irb_protocol(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip().lower().startswith("irb protocol"):
            return line.split(":")[-1].strip()
    return None


# Function: Extract Record Date
def extract_record_date(text: str) -> str | None:
    for line in text.splitlines():
        if line.strip().lower().startswith("record date"):
            return line.split(":")[-1].strip()
    return None


# ── Look for scans ──────────────────────────────────────────────────────────────

def find_scan_paths(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each row, check the sibling 'mri' and 'ct' directories
    for a file matching the patient_id prefix. Adds 'path_mri'
    and 'path_ct' columns to the dataframe.
    """
    mri_paths = []
    ct_paths = []

    for _, row in df.iterrows():
        irb_dir = Path(row["path_ehr"]).parent.parent  # up from /ehr/ to /irb_2025_003/

        mri_match = None
        for f in (irb_dir / "mri").iterdir() if (irb_dir / "mri").exists() else []:
            if f.name.startswith(row["patient_id"]):
                mri_match = str(f)
                break

        ct_match = None
        for f in (irb_dir / "ct").iterdir() if (irb_dir / "ct").exists() else []:
            if f.name.startswith(row["patient_id"]):
                ct_match = str(f)
                break

        mri_paths.append(mri_match)
        ct_paths.append(ct_match)

    df["path_mri"] = mri_paths
    df["path_ct"] = ct_paths

    return df

# ── Dataframe adjustments ──────────────────────────────────────────────────────

def melt_df(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Convert dataframe to melted dataframe.

    '''

    # Melt dataframe into long-form
    df = df.melt(
        id_vars=['patient_id', 'irb_protocol', 'record_date'],
        value_vars=['path_ehr', 'path_mri', 'path_ct'],
        var_name='modality',
        value_name='assert_uri'
    )

    # 2. Clean up the 'modality' column (optional: removes the 'path_' prefix)
    df['modality'] = df['modality'].str.replace('path_', '', regex=False)

    # 3. Add the 'status' column based on whether assert_uri has a value
    df['status'] = np.where(df['assert_uri'].notna(), 'complete', 'pending')

    return df


# ── Master parser ──────────────────────────────────────────────────────────────

def parse_ehr(texts: list[str]) -> dict:

    """
    Try each extractor against a list of EHR text strings.
    Once a field gets a non-None value, it is considered complete
    and skipped for all remaining texts.
    """

    # Initialize
    extractors = {
        "patient_id":   extract_patient_id,
        "irb_protocol": extract_irb_protocol,
        "record_date":  extract_record_date,
    }

    results = {field: None for field in extractors}

    # Iterate through lines within the txt
    for text in texts:

        # Only run extractors for fields still missing
        pending = {
            field: fn for field, fn in extractors.items() if fn is not None
        }

        # When empty
        if not pending:
            break  # everything is filled, no need to keep going

        # Otherwise attempt to extract
        for field, fn in pending.items():
            value = fn(text)
            if value is not None:
                results[field] = value

    return results

# ── DataFrame builder ──────────────────────────────────────────────────────────

def build_dataframe(file_paths: list[str | Path]) -> pd.DataFrame:
    """
    Given a list of EHR file paths, read each file and return a
    DataFrame with one row per patient.

    Example
    -------
    >>> from pathlib import Path
    >>> files = Path("records/").glob("*.txt")
    >>> df = build_dataframe(files)
    """
    # Initialize
    rows = []
    # Iterate through files
    for path in file_paths:

        # Open
        with open(path, 'r') as f:

            # Read
            text = f.readlines()

        # Parse
        row = parse_ehr(text)

        # Define path
        row["path_ehr"] = str(path)   # keep provenance

        # Append
        rows.append(row)

    return melt_df(find_scan_paths(pd.DataFrame(rows)))
