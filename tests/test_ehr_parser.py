"""
tests/test_ehr_parser.py
------------------------
Unit tests for the ehr_parser package.
Run with:  pytest tests/ -v
"""

import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_EHR = textwrap.dedent("""\
    Patient ID: PT-20250101-0042
    IRB Protocol: IRB-2025-003
    Record Date: 2025-01-15

    DEMOGRAPHICS
    Age: 49
    Sex: Male

    ACTIVE CONDITIONS
    - Hypertension Stage 2
    - Type 2 Diabetes Mellitus
    - Chronic kidney disease, stage 3a

    CURRENT MEDICATIONS
    * Lisinopril 20 mg daily
    * Metformin 1000 mg twice daily
    * Atorvastatin 40 mg daily

    VITALS
    Blood Pressure: 165/67 mmHg
    Heart Rate: 75 bpm
    Weight: 77.8 kg

    NOTES
    Patient presents for routine follow-up.
    Blood pressure remains elevated despite current regimen.
    Consider adding amlodipine 5 mg.
""")

MINIMAL_EHR = textwrap.dedent("""\
    Patient ID: PT-MINIMAL-001
    Some unrelated text here.
""")

EMPTY_EHR = ""


@pytest.fixture
def sample_text():
    return SAMPLE_EHR


@pytest.fixture
def sample_lines():
    """Return the EHR as a list of lines (mimicking f.readlines())."""
    return SAMPLE_EHR.splitlines(keepends=True)


@pytest.fixture
def minimal_text():
    return MINIMAL_EHR


@pytest.fixture
def tmp_ehr_tree(tmp_path):
    """
    Build a small on-disk directory tree:
        tmp_path/irb_2025_003/
            ehr/
                PT-001.txt
                PT-002.txt
            mri/
                PT-001_mri.nii.gz
            ct/
                PT-002_ct.dcm
    """
    irb = tmp_path / "irb_2025_003"
    (irb / "ehr").mkdir(parents=True)
    (irb / "mri").mkdir()
    (irb / "ct").mkdir()

    ehr1 = irb / "ehr" / "PT-001.txt"
    ehr1.write_text(textwrap.dedent("""\
        Patient ID: PT-001
        IRB Protocol: IRB-2025-003
        Record Date: 2025-03-01
    """))

    ehr2 = irb / "ehr" / "PT-002.txt"
    ehr2.write_text(textwrap.dedent("""\
        Patient ID: PT-002
        IRB Protocol: IRB-2025-003
        Record Date: 2025-03-02
    """))

    (irb / "mri" / "PT-001_mri.nii.gz").write_bytes(b"")
    (irb / "ct" / "PT-002_ct.dcm").write_bytes(b"")

    return irb


# ── helpers ───────────────────────────────────────────────────────────────────


class TestGetSection:
    def test_returns_section_body(self, sample_text):
        from ehr_parser.helpers import get_section

        demo = get_section(sample_text, "DEMOGRAPHICS")
        assert "Age: 49" in demo
        assert "Sex: Male" in demo

    def test_returns_empty_for_missing_section(self, sample_text):
        from ehr_parser.helpers import get_section

        assert get_section(sample_text, "NONEXISTENT") == ""

    def test_does_not_bleed_into_next_section(self, sample_text):
        from ehr_parser.helpers import get_section

        demo = get_section(sample_text, "DEMOGRAPHICS")
        assert "Hypertension" not in demo


class TestExtractBullets:
    def test_parses_dash_bullets(self):
        from ehr_parser.helpers import extract_bullets

        text = "- Alpha\n- Beta\n- Gamma"
        assert extract_bullets(text) == ["Alpha", "Beta", "Gamma"]

    def test_parses_asterisk_bullets(self):
        from ehr_parser.helpers import extract_bullets

        text = "* Foo\n* Bar"
        assert extract_bullets(text) == ["Foo", "Bar"]

    def test_skips_non_bullet_lines(self):
        from ehr_parser.helpers import extract_bullets

        text = "header\n- item\nplain line"
        assert extract_bullets(text) == ["item"]

    def test_empty_input(self):
        from ehr_parser.helpers import extract_bullets

        assert extract_bullets("") == []


class TestExtractField:
    def test_colon_separator(self):
        from ehr_parser.helpers import extract_field

        assert extract_field("Age: 49", "Age") == "49"

    def test_dash_separator(self):
        from ehr_parser.helpers import extract_field

        assert extract_field("Age - 49", "Age") == "49"

    def test_case_insensitive(self):
        from ehr_parser.helpers import extract_field

        assert extract_field("age: 49", "Age") == "49"

    def test_returns_none_when_absent(self):
        from ehr_parser.helpers import extract_field

        assert extract_field("nothing here", "Age") is None


# ── extractors ────────────────────────────────────────────────────────────────


class TestHeaderExtractors:
    def test_extract_patient_id(self, sample_text):
        from ehr_parser.extractors import extract_patient_id

        assert extract_patient_id(sample_text) == "PT-20250101-0042"

    def test_extract_irb_protocol(self, sample_text):
        from ehr_parser.extractors import extract_irb_protocol

        assert extract_irb_protocol(sample_text) == "IRB-2025-003"

    def test_extract_record_date(self, sample_text):
        from ehr_parser.extractors import extract_record_date

        assert extract_record_date(sample_text) == "2025-01-15"

    def test_patient_id_missing(self):
        from ehr_parser.extractors import extract_patient_id

        assert extract_patient_id("no id here") is None

    def test_irb_protocol_missing(self):
        from ehr_parser.extractors import extract_irb_protocol

        assert extract_irb_protocol("no protocol") is None

    def test_record_date_missing(self):
        from ehr_parser.extractors import extract_record_date

        assert extract_record_date("") is None


class TestDemographicExtractors:
    def test_extract_age(self, sample_text):
        from ehr_parser.extractors import extract_age

        assert extract_age(sample_text) == 49

    def test_extract_age_non_numeric(self):
        from ehr_parser.extractors import extract_age

        bad = "DEMOGRAPHICS\nAge: unknown\n\nVITALS\n"
        assert extract_age(bad) is None

    def test_extract_sex(self, sample_text):
        from ehr_parser.extractors import extract_sex

        assert extract_sex(sample_text) == "Male"


class TestConditionsExtractor:
    def test_extract_conditions(self, sample_text):
        from ehr_parser.extractors import extract_conditions

        conds = extract_conditions(sample_text)
        assert len(conds) == 3
        assert "Hypertension Stage 2" in conds

    def test_empty_when_section_missing(self, minimal_text):
        from ehr_parser.extractors import extract_conditions

        assert extract_conditions(minimal_text) == []


class TestMedicationsExtractor:
    def test_extract_medications(self, sample_text):
        from ehr_parser.extractors import extract_medications

        meds = extract_medications(sample_text)
        assert len(meds) == 3
        assert any("Metformin" in m for m in meds)


class TestVitalsExtractors:
    def test_blood_pressure(self, sample_text):
        from ehr_parser.extractors import extract_blood_pressure

        assert extract_blood_pressure(sample_text) == "165/67 mmHg"

    def test_heart_rate(self, sample_text):
        from ehr_parser.extractors import extract_heart_rate

        assert extract_heart_rate(sample_text) == "75 bpm"

    def test_weight(self, sample_text):
        from ehr_parser.extractors import extract_weight

        assert extract_weight(sample_text) == "77.8 kg"

    def test_returns_none_when_missing(self, minimal_text):
        from ehr_parser.extractors import extract_blood_pressure

        assert extract_blood_pressure(minimal_text) is None


class TestNotesExtractor:
    def test_extract_notes(self, sample_text):
        from ehr_parser.extractors import extract_notes

        notes = extract_notes(sample_text)
        assert notes is not None
        assert "routine follow-up" in notes
        # Should collapse whitespace into a single line
        assert "\n" not in notes

    def test_returns_none_when_missing(self, minimal_text):
        from ehr_parser.extractors import extract_notes

        assert extract_notes(minimal_text) is None


# ── scan ──────────────────────────────────────────────────────────────────────


class TestFindScanPaths:
    def test_finds_existing_scans(self, tmp_ehr_tree):
        from ehr_parser.scan import find_scan_paths

        df = pd.DataFrame(
            [
                {"patient_id": "PT-001", "path_ehr": str(tmp_ehr_tree / "ehr" / "PT-001.txt")},
                {"patient_id": "PT-002", "path_ehr": str(tmp_ehr_tree / "ehr" / "PT-002.txt")},
            ]
        )
        result = find_scan_paths(df)

        # PT-001 has an MRI but no CT
        assert pd.notna(result.loc[0, "path_mri"])
        assert "PT-001_mri" in result.loc[0, "path_mri"]
        assert pd.isna(result.loc[0, "path_ct"])

        # PT-002 has a CT but no MRI
        assert pd.isna(result.loc[1, "path_mri"])
        assert pd.notna(result.loc[1, "path_ct"])
        assert "PT-002_ct" in result.loc[1, "path_ct"]

    def test_handles_missing_scan_dirs(self, tmp_path):
        from ehr_parser.scan import find_scan_paths

        # No mri/ or ct/ directories at all
        ehr_dir = tmp_path / "study" / "ehr"
        ehr_dir.mkdir(parents=True)
        ehr_file = ehr_dir / "PT-X.txt"
        ehr_file.write_text("Patient ID: PT-X\n")

        df = pd.DataFrame(
            [{"patient_id": "PT-X", "path_ehr": str(ehr_file)}]
        )
        result = find_scan_paths(df)
        assert result.loc[0, "path_mri"] is None
        assert result.loc[0, "path_ct"] is None


# ── transform ─────────────────────────────────────────────────────────────────


class TestMeltDf:
    def test_produces_long_form(self):
        from ehr_parser.transform import melt_df

        wide = pd.DataFrame(
            [
                {
                    "patient_id": "PT-001",
                    "irb_protocol": "IRB-1",
                    "record_date": "2025-01-01",
                    "path_ehr": "/a/ehr/PT-001.txt",
                    "path_mri": "/a/mri/PT-001.nii",
                    "path_ct": None,
                }
            ]
        )
        long = melt_df(wide)

        assert len(long) == 3  # ehr, mri, ct
        assert set(long["modality"]) == {"ehr", "mri", "ct"}

    def test_status_column(self):
        from ehr_parser.transform import melt_df

        wide = pd.DataFrame(
            [
                {
                    "patient_id": "PT-001",
                    "irb_protocol": "IRB-1",
                    "record_date": "2025-01-01",
                    "path_ehr": "/a/ehr/PT-001.txt",
                    "path_mri": None,
                    "path_ct": None,
                }
            ]
        )
        long = melt_df(wide)

        ehr_row = long[long["modality"] == "ehr"].iloc[0]
        mri_row = long[long["modality"] == "mri"].iloc[0]

        assert ehr_row["status"] == "complete"
        assert mri_row["status"] == "pending"


# ── parser ────────────────────────────────────────────────────────────────────


class TestParseEhr:
    def test_extracts_all_fields(self, sample_lines):
        from ehr_parser.parser import parse_ehr

        result = parse_ehr(sample_lines)
        assert result["patient_id"] == "PT-20250101-0042"
        assert result["irb_protocol"] == "IRB-2025-003"
        assert result["record_date"] == "2025-01-15"

    def test_partial_data(self):
        from ehr_parser.parser import parse_ehr

        lines = ["Patient ID: PT-ONLY\n", "nothing else\n"]
        result = parse_ehr(lines)
        assert result["patient_id"] == "PT-ONLY"
        assert result["irb_protocol"] is None
        assert result["record_date"] is None

    def test_empty_input(self):
        from ehr_parser.parser import parse_ehr

        result = parse_ehr([])
        assert all(v is None for v in result.values())

    def test_first_match_wins(self):
        """If the same field appears across multiple texts, the first value sticks."""
        from ehr_parser.parser import parse_ehr

        lines = [
            "Patient ID: FIRST\n",
            "Patient ID: SECOND\n",
        ]
        result = parse_ehr(lines)
        assert result["patient_id"] == "FIRST"


class TestBuildDataframe:
    def test_end_to_end(self, tmp_ehr_tree):
        from ehr_parser.parser import build_dataframe

        files = sorted((tmp_ehr_tree / "ehr").glob("*.txt"))
        df = build_dataframe(files)

        # Two patients × three modalities = 6 rows
        assert len(df) == 6
        assert "modality" in df.columns
        assert "status" in df.columns
        assert set(df["modality"]) == {"ehr", "mri", "ct"}

    def test_empty_file_list(self):
        from ehr_parser.parser import build_dataframe

        df = build_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
