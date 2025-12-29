

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
        شما باید گزارش نهایی را بر اساس «متن دیکته‌شده» تولید کنید، نه بر اساس جملات نرمالِ داخل تمپلیت.

        قوانین بسیار مهم (الزامی):
        1) تمپلیت فقط «ساختار/فرمت» است. متن Findings و Impression را از صفر و بر اساس متن خام بازنویسی کن.
        2) اگر تمپلیت شامل یافته‌های نرمال/پیش‌فرض است، فقط در صورتی نگه دار که با متن خام هم‌خوان باشد. اگر متن خام غیرنرمال بود، همان بخش‌ها را تغییر بده.
        3) هیچ یافته یا نتیجه‌ای را بدون پشتوانه‌ی متن خام اضافه نکن (Hallucination ممنوع).
        4) اگر متن خام شامل مواردی مثل «ضایعه»، «کیست»، «توده»، «ترومبوز/Thrombosis»، «DVT»، «تنگی/Stenosis»، «پلاک»، «هیدرونفروز»، «افزایش حجم»، «افزایش اکوژنیسیته/Echogenic»، «دایلاتاسیون»، «کلسیفیه» بود، Impression نمی‌تواند "Normal" باشد.
        5) اگر در متن خام عبارت‌های نفی مثل «دیده نشد/مشاهده نشد/وجود ندارد» آمده، دقیقاً رعایت کن.
        6) هر بخش RTL/HTML موجود در تمپلیت (مثل dir="rtl" یا styleهای راست‌چین) باید دقیقاً حفظ شود و حذف/خراب نشود.

        خروجی:
        - فقط یک JSON معتبر با کلید final_report برگردان.
        - هیچ متن اضافی، هیچ توضیحی، هیچ بک‌تیک و هیچ کلید دیگری اضافه نکن.

        -----------------------------
        Report Type:
        {report_type}
        -----------------------------
        Template (فارسی):
        {template}
        -----------------------------
        Dictated Text (ASR/Refined Input):
        {raw_text}
        -----------------------------
        """.strip()


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
