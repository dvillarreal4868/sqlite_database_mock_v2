"""
ehr_parser.transform
--------------------
DataFrame reshaping / enrichment helpers.
"""

import numpy as np
import pandas as pd


def melt_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot a wide-form patient DataFrame (one row per patient with
    path_ehr / path_mri / path_ct columns) into long-form with one
    row per modality, plus a 'status' indicator.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["patient_id", "irb_protocol", "record_date",
                     "modality", "asset_uri", "status"]
        )
    df = df.melt(
        id_vars=["patient_id", "irb_protocol", "record_date"],
        value_vars=["path_ehr", "path_mri", "path_ct"],
        var_name="modality",
        value_name="asset_uri",
    )

    df["modality"] = df["modality"].str.replace("path_", "", regex=False)
    df["status"] = np.where(df["asset_uri"].notna(), "complete", "pending")

    return df
