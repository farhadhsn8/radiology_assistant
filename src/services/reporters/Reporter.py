import os
import json
import re

from src.services.llm.llm import llm
from src.utils.file_processing import read_text_file, extract_field_from_json


class Reporter:
    def __init__(self):
        self.llm_instance = llm()
    
    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> str:
            """
            Short prompt, no Markdown, JSON example with escaped braces.
            """
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
        """Get template based on report type with default handling."""
     
        clean_type = (report_type or "").strip()
        type_parts = [p.strip() for p in clean_type.split(":") if p.strip()]

        # Handle different report_type formats
        if len(type_parts) == 1:  # e.g., "CT"
            modality = type_parts[0]
            file_addr = f"assets/templates/{modality}/contrast/abdomen_and_pelvis.txt"
        elif len(type_parts) == 2:  # e.g., "CT:contrast"
            file_addr = f"assets/templates/{type_parts[0]}/{type_parts[1]}/abdomen_and_pelvis.txt"
        elif len(type_parts) == 3:  # e.g., "CT:contrast:abdomen_and_pelvis"
          
            modality, contrast, study = type_parts
            file_addr = f"assets/templates/{modality}/{contrast}/{study}.txt"
        else:
            raise ValueError(f"Invalid report_type format: {report_type}")

        if not os.path.exists(file_addr):
            raise FileNotFoundError(f"Template file for {report_type} not found: {file_addr}")
        
        content = read_text_file(file_addr)
        
        return content

    def get_prompt(self, report_type: str) -> str:
        """Get prompt based on report type with default handling."""
       
        file_addr = "assets/prompts/general_prompt.txt"
        content = read_text_file(file_addr)
        
        return content

    def generate_report(self, raw_text: str, report_type: str) -> str:
        """Generate report from input text using template and LLM."""
        try:
            template = self.get_template(report_type)
            prompt = self.get_prompt(report_type)
            materials = self.prepare_inputs(raw_text, template, report_type)
            out = self.llm_instance.get_answer(materials, prompt)
            out = self.post_process(out)
            return out
        except Exception as e:
            print(f"Error generating report (type={report_type}): {e}")
            return None
