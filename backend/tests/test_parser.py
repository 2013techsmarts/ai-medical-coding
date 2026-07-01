import os
import pytest
from backend.ingestion.parser import parse_icd10_cm_file, parse_icd10_pcs_file

@pytest.fixture
def temp_cm_file(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    f = d / "cm_test.txt"
    # Write mock CM data in official format (fixed width) and custom format
    content = (
        "00001 A000   1 Cholera due to Vibrio cholerae 01, biovar cholerae\n"
        "00002 E119   1 Type 2 diabetes mellitus without complications\n"
        "I10 Essential (primary) hypertension\n"
    )
    f.write_text(content)
    return str(f)

@pytest.fixture
def temp_pcs_file(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    f = d / "pcs_test.txt"
    # Write mock PCS data
    content = (
        "00001 0016070 1 Bypass Cerebral Ventricle to Nasopharynx...\n"
        "02100A9 Bypass Coronary Artery, One Site from Coronary Artery with Autologous Venous Graft\n"
    )
    f.write_text(content)
    return str(f)

def test_parse_icd10_cm(temp_cm_file):
    codes = parse_icd10_cm_file(temp_cm_file)
    assert len(codes) == 3
    # Check fixed width parsing and formatted dot inserter
    assert codes[0]["code"] == "A00.0"
    assert codes[0]["description"] == "Cholera due to Vibrio cholerae 01, biovar cholerae"
    assert codes[1]["code"] == "E11.9"
    # Check simple space splitting fallback
    assert codes[2]["code"] == "I10"
    assert codes[2]["description"] == "Essential (primary) hypertension"

def test_parse_icd10_pcs(temp_pcs_file):
    codes = parse_icd10_pcs_file(temp_pcs_file)
    assert len(codes) == 2
    assert codes[0]["code"] == "0016070"
    assert codes[1]["code"] == "02100A9"
