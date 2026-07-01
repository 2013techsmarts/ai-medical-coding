import os
import glob
from typing import List, Dict

def parse_icd10_cm_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parses ICD-10-CM description files.
    Supports both fixed-width (official order files) and simple space/tab-separated files.
    """
    codes = []
    if not os.path.exists(file_path):
        return codes

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Split line to handle standard or custom spacing
            parts = line.split(None, 3)
            
            # Case 1: Official order file (OrderNum[5 chars] Code[7 chars] HeaderFlag[1 char] Description)
            if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) == 5:
                code = parts[1].strip()
                desc = parts[3].strip()
            # Case 2: Custom space-separated (Code Description)
            else:
                parts_two = line.split(None, 1)
                if len(parts_two) == 2:
                    code = parts_two[0].strip()
                    desc = parts_two[1].strip()
                else:
                    continue
            
            # Normalize CM code (insert decimal if missing, e.g., E119 -> E11.9)
            if len(code) > 3 and "." not in code:
                # ICD-10-CM codes have decimal point after the 3rd character
                formatted_code = f"{code[:3]}.{code[3:]}"
            else:
                formatted_code = code
                
            codes.append({
                "code": formatted_code,
                "description": desc,
                "type": "cm"
            })
    return codes

def parse_icd10_pcs_file(file_path: str) -> List[Dict[str, str]]:
    """
    Parses ICD-10-PCS description files.
    Supports both official order files and custom files.
    """
    codes = []
    if not os.path.exists(file_path):
        return codes

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(None, 3)
            
            # Case 1: Official order file (OrderNum[5 chars] Code[7 chars] HeaderFlag[1 char] Description)
            if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) == 5:
                code = parts[1].strip()
                desc = parts[3].strip()
            # Case 2: Custom space-separated (Code Description)
            else:
                parts_two = line.split(None, 1)
                if len(parts_two) == 2:
                    code = parts_two[0].strip()
                    desc = parts_two[1].strip()
                else:
                    continue

            codes.append({
                "code": code,
                "description": desc,
                "type": "pcs"
            })
    return codes

def load_all_codes(directory: str, type_str: str) -> List[Dict[str, str]]:
    """
    Scans directory for .txt files and parses them.
    """
    all_codes = []
    search_path = os.path.join(directory, "*.txt")
    files = glob.glob(search_path)
    
    for f in files:
        if type_str == "cm":
            all_codes.extend(parse_icd10_cm_file(f))
        else:
            all_codes.extend(parse_icd10_pcs_file(f))
            
    return all_codes
