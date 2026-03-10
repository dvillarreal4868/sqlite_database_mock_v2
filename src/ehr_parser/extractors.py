"""
ehr_parser.extractors
---------------------
Each public function accepts a raw EHR text string and returns the
extracted value(s) for a single field.
"""

from .helpers import extract_bullets, extract_field, get_section


# ── Header / metadata ─────────────────────────────────────────────────────────


def extract_patient_id(text: str) -> str | None:
    """Extract the Patient ID from the header block."""
    for line in text.splitlines():
        if line.strip().lower().startswith("patient id"):
            return line.split(":")[-1].strip()
    return None


def extract_irb_protocol(text: str) -> str | None:
    """Extract the IRB Protocol identifier."""
    for line in text.splitlines():
        if line.strip().lower().startswith("irb protocol"):
            return line.split(":")[-1].strip()
    return None


def extract_record_date(text: str) -> str | None:
    """Extract the Record Date string."""
    for line in text.splitlines():
        if line.strip().lower().startswith("record date"):
            return line.split(":")[-1].strip()
    return None


# ── Demographics ──────────────────────────────────────────────────────────────


def extract_age(text: str) -> int | None:
    """Extract patient age as an integer."""
    value = extract_field(get_section(text, "DEMOGRAPHICS"), "Age")
    return int(value) if value and value.isdigit() else None


def extract_sex(text: str) -> str | None:
    """Extract patient sex (e.g. 'Male', 'Female')."""
    return extract_field(get_section(text, "DEMOGRAPHICS"), "Sex")


# ── Active Conditions ─────────────────────────────────────────────────────────


def extract_conditions(text: str) -> list[str]:
    """Extract list of active conditions."""
    return extract_bullets(get_section(text, "ACTIVE CONDITIONS"))


# ── Medications ───────────────────────────────────────────────────────────────


def extract_medications(text: str) -> list[str]:
    """Extract list of current medications (name + dose)."""
    return extract_bullets(get_section(text, "CURRENT MEDICATIONS"))


# ── Vitals ────────────────────────────────────────────────────────────────────


def extract_blood_pressure(text: str) -> str | None:
    """Extract blood pressure string (e.g. '165/67 mmHg')."""
    return extract_field(get_section(text, "VITALS"), "Blood Pressure")


def extract_heart_rate(text: str) -> str | None:
    """Extract heart rate string (e.g. '75 bpm')."""
    return extract_field(get_section(text, "VITALS"), "Heart Rate")


def extract_weight(text: str) -> str | None:
    """Extract weight string (e.g. '77.8 kg')."""
    return extract_field(get_section(text, "VITALS"), "Weight")


# ── Notes ─────────────────────────────────────────────────────────────────────


def extract_notes(text: str) -> str | None:
    """Extract free-text clinical notes as a single string."""
    section = get_section(text, "NOTES")
    return " ".join(section.split()) if section else None
