from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from src.services.llm.llm import llm
from src.utils.normalize_and_mapping import normalize_persian_text

try:
    from src.services.llm.refine_transcription import FarsiTranscriptionRefiner
except Exception:
    FarsiTranscriptionRefiner = None  


class ReporterFA:
    def __init__(self) -> None:
        self._prompt_cache: Optional[str] = None
        self._template_cache: Dict[str, str] = {}

        self.medical_dict: Dict[str, Any] = self._load_medical_dict()

        if FarsiTranscriptionRefiner is not None:
            self.refiner = FarsiTranscriptionRefiner(llm())
        else:
            self.refiner = None
            print("[FA][WARN] FarsiTranscriptionRefiner is not available.")


    @staticmethod
    def _read_text_utf8(path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _load_medical_dict() -> Dict[str, Any]:
        try:
            with open("configs/medical_terms.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[FA][WARN] Could not load configs/medical_terms.json: {e}")
            return {}

    def get_prompt(self) -> str:
        if self._prompt_cache is not None:
            return self._prompt_cache

        path = "assets/prompts/general_prompt_persian.txt"
        content = self._read_text_utf8(path).strip()
        if not content:
            raise ValueError(f"Empty prompt file: {path}")

        self._prompt_cache = content
        return self._prompt_cache

    def get_template(self, report_type: str) -> str:
        rt = (report_type or "").strip()
        if rt in self._template_cache:
            return self._template_cache[rt]

        parts = [p.strip() for p in rt.split(":") if p.strip()]
        if len(parts) == 1:
            modality = parts[0]
            file_addr = (
                f"assets/templates_fa/{modality}/contrast/abdomen_and_pelvis.txt"
            )
        elif len(parts) == 2:
            modality, contrast = parts
            file_addr = (
                f"assets/templates_fa/{modality}/{contrast}/abdomen_and_pelvis.txt"
            )
        elif len(parts) == 3:
            modality, contrast, study = parts
            file_addr = f"assets/templates_fa/{modality}/{contrast}/{study}.txt"
        else:
            raise ValueError(f"Invalid report_type format for Farsi: {report_type}")

        content = self._read_text_utf8(file_addr)
        self._template_cache[rt] = content
        return content

    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> str:
        raw_text = normalize_persian_text(raw_text or "")

        return f"""
شما باید گزارش نهایی را بر اساس «متن دیکته‌شده» تولید کنید، نه بر اساس جملات نرمالِ داخل تمپلیت.

قوانین بسیار مهم (الزامی):
1) تمپلیت فقط «ساختار/فرمت» است. متن Findings و Impression را از صفر و بر اساس متن خام بازنویسی کن.
2) اگر تمپلیت شامل یافته‌های نرمال/پیش‌فرض است، فقط در صورتی نگه دار که با متن خام هم‌خوان باشد. اگر متن خام غیرنرمال بود، همان بخش‌ها را تغییر بده.
3) هیچ یافته یا نتیجه‌ای را بدون پشتوانه‌ی متن خام اضافه نکن (Hallucination ممنوع).
4) اگر در متن خام مواردی مثل «ضایعه»، «کیست»، «توده»، «ترومبوز»، «DVT»، «تنگی»، «پلاک»، «هیدرونفروز»، «افزایش حجم»، «افزایش اکوژنیسیته»، «دایلاتاسیون»، «کلسیفیه» بود، Impression نمی‌تواند "Normal" باشد.
5) اگر در متن خام عبارت‌های نفی مثل «دیده نشد/مشاهده نشد/وجود ندارد» آمده، دقیقاً رعایت کن.
6) هر بخش RTL/HTML موجود در تمپلیت (مثل dir="rtl" یا styleهای راست‌چین) باید دقیقاً حفظ شود و حذف/خراب نشود.

قانون placeholderها (خیلی مهم):
- هر جای تمپلیت که placeholder مثل "... mm" یا "... cc" دارد:
  اگر مقدار در متن خام وجود دارد، آن را با مقدار واقعی جایگزین کن.
  اگر مقدار وجود ندارد، جمله/عبارتِ شامل placeholder را کامل حذف کن و متن نرمال باقی بماند.
- هرگز placeholder را دست‌نخورده باقی نگذار.

قانون زبان:
- اصطلاحات پزشکی لاتین/انگلیسی موجود در متن خام (مثل DVT, CBD, IHD, HU, mm, cm, cc) باید حفظ شوند.

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

  

    def generate_report(self, raw_text: str, report_type: str) -> Optional[str]:
        if not self.refiner:
            print("[FA][ERROR] Refiner is not available, cannot generate report.")
            return None

        try:
            template = self.get_template(report_type)
        except Exception as e:
            print(f"[FA] Error loading template (type={report_type}): {e}")
            return None

        try:
            system_prompt = self.get_prompt()
        except Exception as e:
            print(f"[FA] Error loading general Farsi prompt: {e}")
            return None

        materials = self.prepare_inputs(raw_text, template, report_type)

        try:
            report = self.refiner.generate_structured_report_from_materials(
                materials=materials,
                system_prompt=system_prompt,
                medical_terms_dict=self.medical_dict,
                source_numbers_text=raw_text,
            )
            return report
        except Exception as e:
            print(f"[FA] Error generating Farsi structured report: {e}")
            return None
