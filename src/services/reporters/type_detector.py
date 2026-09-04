import os
from src.services.llm.llm import llm
from src.utils.file_processing import read_text_file, extract_field_from_json

class Type_detector:
    def __init__(self):
        self.llm_instance = llm()
    


    def get_prompt(self) -> str:
        """Get prompt based on report type with default handling."""
        file_addr = f"assets/prompts/type_detector.txt"
        content = read_text_file(file_addr)
        if "error" in content.lower():
            raise Exception(f"Error reading prompt")
        return content

    def detect(self, raw_text: str) -> str:
        """Generate report from input text using template and LLM."""
        try:
            prompt = self.get_prompt()
            out = self.llm_instance.get_answer(raw_text, prompt)
            return out
        except Exception as e:
            print(f"Error generating report: {e}")
            return None