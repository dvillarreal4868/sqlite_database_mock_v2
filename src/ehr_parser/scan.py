"""
ehr_parser.scan
---------------
Utilities for locating associated imaging files (MRI, CT) on disk.
"""

from pathlib import Path

import pandas as pd


def find_scan_paths(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each row, check the sibling 'mri' and 'ct' directories
    for a file matching the patient_id prefix.  Adds 'path_mri'
    and 'path_ct' columns to the dataframe.
    """
    mri_paths: list[str | None] = []
    ct_paths: list[str | None] = []

    for _, row in df.iterrows():
        irb_dir = Path(row["path_ehr"]).parent.parent  # up from /ehr/ to IRB root

        mri_match = _find_first_match(irb_dir / "mri", row["patient_id"])
        ct_match = _find_first_match(irb_dir / "ct", row["patient_id"])

        mri_paths.append(mri_match)
        ct_paths.append(ct_match)

    df["path_mri"] = mri_paths
    df["path_ct"] = ct_paths
    return df


def _find_first_match(scan_dir: Path, patient_id: str) -> str | None:
    """Return the first file in *scan_dir* whose name starts with *patient_id*."""
    if not scan_dir.exists():
        return None
    for f in scan_dir.iterdir():
        if f.name.startswith(patient_id):
            return str(f)
    return None
