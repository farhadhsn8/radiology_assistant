import random
import string,time

import re, json

def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        return "The specified file was not found."
    except Exception as e:
        return f"An error occurred: {e}"
    

    
def extract_field_from_json(text, field_name):
    pattern = rf'"{field_name}"\s*:\s*"((?:[^"\\]|\\.)*)"'

    match = re.search(pattern, text, re.DOTALL)
    if match:
        final_report = match.group(1)
        final_report = final_report.encode().decode('unicode_escape').replace('â¢', '•')
        return final_report
    else:
        return text


def parse_report_for_filename(report: str) -> tuple[str, str, str]:
    """Parse report to extract modality, contrast, and anatomy."""
    report_lower = report.lower()
    
    if "ct" in report_lower:
        modality = "ct"
    elif "mri" in report_lower:
        modality = "mri"
    elif "ultrasound" in report_lower or "sono" in report_lower:
        modality = "ultrasound"
    else:
        modality = "unknown"
    
    contrast = "contrast" if "contrast" in report_lower else "no_contrast"
    
    anatomy = "unknown"
    if "brain" in report_lower:
        anatomy = "brain"
    elif "abdomen" in report_lower or "pelvis" in report_lower:
        anatomy = "abdomen_and_pelvis"
    elif "chest" in report_lower:
        anatomy = "chest"
    
    return modality, contrast, anatomy



def generate_meaningful_filename(report_type: str = None, report: str = None, extension: str = "mp3") -> str:
    """Generate a meaningful filename based on report_type or report content."""
    if report:
        modality, contrast, anatomy = parse_report_for_filename(report)
        base_name = f"{modality}_{contrast}_{anatomy}"
    else:
        parts = report_type.split(":") if report_type else ["unknown"]
        safe_parts = [part.lower().replace(" ", "_") for part in parts]
        base_name = "_".join(safe_parts)

    timestamp = int(time.time())
    return f"{base_name}_{timestamp}.{extension}"
