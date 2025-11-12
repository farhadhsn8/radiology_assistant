
import os
from src.services.llm.llm import llm
from src.utils.file_processing import read_text_file, extract_field_from_json

class Reporter:
    def __init__(self):
        self.llm_instance = llm()
    
    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> str:
        """Prepare input text for LLM."""
        return f"""
        Report Type: {report_type}
        -------------------------
        Template report: {template}
        -------------------------
        Patient raw report (voice-transcribed): {raw_text}
        """

    def post_process(self, out: str) -> str:
        """Extract final report from LLM output."""
        return extract_field_from_json(out, "final_report") or out

    def get_template(self, report_type: str) -> str:
        """Get template based on report type with default handling."""
        type_parts = report_type.split(":")
        
        # Handle different report_type formats
        if len(type_parts) == 1:  # e.g., "CT"
            modality = type_parts[0]
            file_addr = f"assets/templates/{modality}/contrast/abdomen_and_pelvis.txt"
        elif len(type_parts) == 2:  # e.g., "CT:contrast"
            file_addr = f"assets/templates/{type_parts[0]}/{type_parts[1]}/abdomen_and_pelvis.txt"
        elif len(type_parts) == 3:  # e.g., "CT:contrast:abdomen_and_pelvis"
            file_addr = f"assets/templates/{type_parts[0]}/{type_parts[1]}/{type_parts[2]}.txt"
        else:
            raise ValueError(f"Invalid report_type format: {report_type}")
        
        if not os.path.exists(file_addr):
            raise FileNotFoundError(f"Template file for {report_type} not found: {file_addr}")
        
        content = read_text_file(file_addr)
        if "error" in content.lower():
            raise Exception(f"Error reading template file for {report_type}: {content}")
        return content

    def get_prompt(self, report_type: str) -> str:
        """Get prompt based on report type with default handling."""
        # type_parts = report_type.split(":")
        
        # if len(type_parts) == 1:  # e.g., "CT"
        #     modality = type_parts[0]
        #     file_addr = f"assets/prompts/{modality}/contrast/abdomen_and_pelvis.txt"
        # elif len(type_parts) == 2:  # e.g., "CT:contrast"
        #     file_addr = f"assets/prompts/{type_parts[0]}/{type_parts[1]}/abdomen_and_pelvis.txt"
        # elif len(type_parts) == 3:  # e.g., "CT:contrast:abdomen_and_pelvis"
        #     file_addr = f"assets/prompts/{type_parts[0]}/{type_parts[1]}/{type_parts[2]}.txt"
        # else:
        #     raise ValueError(f"Invalid report_type format: {report_type}")
        
        # if not os.path.exists(file_addr):
        #     raise FileNotFoundError(f"Prompt file for {report_type} not found: {file_addr}")
        file_addr = f"assets/prompts/general_prompt.txt"
        content = read_text_file(file_addr)
        if "error" in content.lower():
            raise Exception(f"Error reading prompt file for {report_type}: {content}")
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
            print(f"Error generating report: {e}")
            return None
