

import os
import json
import re

from src.services.llm.llm import llm


class ReporterFA:


    def __init__(self):
        self.llm_instance = llm()

    @staticmethod
    def _read_text_utf8(path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> str:
     
        return f"""


-----------------------------
نوع گزارش (Report Type):
{report_type}
-----------------------------
تمپلیت فارسی گزارش:
{template}
-----------------------------
گزارش خام (متن دیکته‌شده، خروجی STT):
{raw_text}
-----------------------------
لطفاً فقط همان JSON را برگردانید و هیچ چیز دیگری اضافه نکنید.
"""

   
    def post_process(self, out: str) -> str:
       
        if not out:
            return ""

        try:
            data = json.loads(out)
            if isinstance(data, dict) and "final_report" in data:
                return str(data["final_report"]).strip()
        except Exception:
            pass

        m = re.search(
            r'"\s*final_report\s*"\s*:\s*"((?:[^"\\]|\\.)*)"', out,
            re.DOTALL,
        )
        if m:
            raw_val = m.group(1)
            try:
                small_json = '{"final_report": "' + raw_val + '"}'
                data = json.loads(small_json)
                return str(data["final_report"]).strip()
            except Exception:
                return raw_val.strip()

        return out.strip()

    def get_template(self, report_type: str) -> str:
       
        clean_type = (report_type or "").strip()
        type_parts = [p.strip() for p in clean_type.split(":") if p.strip()]

        if len(type_parts) == 1:
            modality = type_parts[0]
            file_addr = f"assets/templates_fa/{modality}/contrast/abdomen_and_pelvis.txt"

        elif len(type_parts) == 2:
            modality, contrast = type_parts
            file_addr = f"assets/templates_fa/{modality}/{contrast}/abdomen_and_pelvis.txt"

        elif len(type_parts) == 3:
            modality, contrast, study = type_parts
            file_addr = f"assets/templates_fa/{modality}/{contrast}/{study}.txt"

        else:
            raise ValueError(f"Invalid report_type format for Farsi: {report_type}")

        content = self._read_text_utf8(file_addr)
        return content

    def get_prompt(self) -> str:
        """
        Read Farsi system prompt (UTF-8).
        """
        file_addr = "assets/prompts/general_prompt_persian.txt"
        return self._read_text_utf8(file_addr)


    def generate_report(self, raw_text: str, report_type: str) -> str | None:
     
        try:
            template = self.get_template(report_type)
            prompt = self.get_prompt()
            materials = self.prepare_inputs(raw_text, template, report_type)
            out = self.llm_instance.get_answer(materials, prompt)
            out = self.post_process(out)
            return out
        except Exception as e:
            print(f"[FA] Error generating Farsi report (type={report_type}): {e}")
            return None
