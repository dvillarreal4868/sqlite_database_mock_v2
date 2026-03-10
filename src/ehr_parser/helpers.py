"""
ehr_parser.helpers
------------------
Low-level text-extraction utilities used by the higher-level extractors.
"""

import re


def get_section(text: str, section_name: str) -> str:
    """Return the raw text block under a given section header."""
    pattern = rf"{re.escape(section_name)}\s*\n(.*?)(?=\n[A-Z ]{{2,}}\n|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_bullets(section_text: str) -> list[str]:
    """Return a list of bullet-point items from a section block."""
    return [
        re.sub(r"^[-•*]\s*", "", line).strip()
        for line in section_text.splitlines()
        if re.match(r"\s*[-•*]\s+\S", line)
    ]


def extract_field(text: str, label: str) -> str | None:
    """Extract a single inline field value by label (e.g. 'Age: 49' → '49')."""
    match = re.search(rf"{re.escape(label)}\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None
