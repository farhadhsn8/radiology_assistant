import os
import json
import re

from src.config import asset_path
from src.services.llm import LLM
from src.utils.file_processing import read_text_file, extract_field_from_json


class Reporter:
    def __init__(self):
        self.llm_instance = LLM()

    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> str:
        return f"""
        You are a radiologist assistant. Rewrite the Patient raw report into the given Template report structure (same headings and line breaks), fixing only grammar and terminology without adding/removing findings or changing numbers/locations.
        Return only this JSON object and nothing else:
        {{"final_report": "<final plain-text report>"}}

        --------------------------------------------------
        Report Type: {report_type}
        --------------------------------------------------
        Template report:
        {template}
        --------------------------------------------------
        Patient raw report (voice-transcribed):
        {raw_text}
        --------------------------------------------------
        """

    def post_process(self, out: str) -> str:
        try:
            extracted = extract_field_from_json(out, "final_report")
        except Exception:
            extracted = None

        if extracted:
            return str(extracted).strip()

        try:
            data = json.loads(out)
            if isinstance(data, dict) and "final_report" in data:
                return str(data["final_report"]).strip()
        except Exception:
            pass

        match = re.search(r'"final_report"\s*:\s*"(.+?)"', out, re.DOTALL)
        if match:
            return match.group(1).strip()

        return out.strip()

    def get_template(self, report_type: str) -> str:
        clean_type = (report_type or "").strip()
        type_parts = [part.strip() for part in clean_type.split(":") if part.strip()]

        if len(type_parts) == 1:
            modality = type_parts[0]
            relative_path = f"templates/{modality}/contrast/abdomen_and_pelvis.txt"
        elif len(type_parts) == 2:
            relative_path = f"templates/{type_parts[0]}/{type_parts[1]}/abdomen_and_pelvis.txt"
        elif len(type_parts) == 3:
            modality, contrast, study = type_parts
            relative_path = f"templates/{modality}/{contrast}/{study}.txt"
        else:
            raise ValueError(f"Invalid report_type format: {report_type}")

        file_addr = asset_path(relative_path)
        if not os.path.exists(file_addr):
            raise FileNotFoundError(f"Template file for {report_type} not found: {file_addr}")

        return read_text_file(str(file_addr))

    def get_prompt(self) -> str:
        return read_text_file(str(asset_path("prompts/general_prompt.txt")))

    def generate_report(self, raw_text: str, report_type: str) -> str:
        try:
            template = self.get_template(report_type)
            prompt = self.get_prompt()
            materials = self.prepare_inputs(raw_text, template, report_type)
            out = self.llm_instance.get_answer(materials, prompt)
            return self.post_process(out)
        except Exception as e:
            print(f"Error generating report (type={report_type}): {e}")
            return None
