from src.config import asset_path
from src.services.llm import LLM
from src.utils.file_processing import read_text_file


class TypeDetector:
    def __init__(self):
        self.llm_instance = LLM()

    def get_prompt(self) -> str:
        return read_text_file(str(asset_path("prompts/type_detector.txt")))

    def detect(self, raw_text: str) -> str:
        try:
            prompt = self.get_prompt()
            return self.llm_instance.get_answer(raw_text, prompt)
        except Exception as e:
            print(f"Error detecting report type: {e}")
            return None
