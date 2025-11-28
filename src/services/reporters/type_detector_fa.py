from src.services.llm.llm import llm


class Type_detector_FA:
    """
    Farsi radiology test type detector.

    Uses: assets/prompts/type_detector_fa.txt (UTF-8)
    """

    def __init__(self):
        self.llm_instance = llm()

    @staticmethod
    def _read_text_utf8(path: str) -> str:
        import os
        if not os.path.exists(path):
            raise FileNotFoundError(f"Farsi type_detector prompt not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def get_prompt(self) -> str:
        file_addr = "assets/prompts/type_detector_fa.txt"
        content = self._read_text_utf8(file_addr)
        if not content:
            raise Exception("Empty Farsi type_detector prompt")
        return content

    def detect(self, raw_text: str) -> str | None:
        try:
            prompt = self.get_prompt()
            out = self.llm_instance.get_answer(raw_text, prompt)
            if out is None:
                return None
            return str(out).strip()
        except Exception as e:
            print(f"[FA] Error detecting Farsi report type: {e}")
            return None
