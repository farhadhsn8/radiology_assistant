# src/services/llm/llm.py
from langchain_openai import ChatOpenAI
import json
import re

class llm:
    def __init__(self) -> None:
        with open('env.json', 'r', encoding="utf-8") as config_file:
            self.configs = json.load(config_file)["models"]["llm"]

        self.client = ChatOpenAI(
            model=self.configs["model_name"],
            base_url=self.configs["base_url"],
            temperature=self.configs.get("temperature", 0.0),
            api_key=self.configs["api_key"]
        )

    def get_answer(self, inp_text: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": inp_text}
        ]
        out = self.client.invoke(messages).content
        return out.strip() if isinstance(out, str) else str(out)

    @staticmethod
    def normalize_persian_text(text: str) -> str:
        if not text:
            return text
        # Arabic -> Persian char normalization
        text = text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
        # remove Arabic diacritics
        diacritics = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]")
        return re.sub(diacritics, "", text).strip()

    @staticmethod
    def build_fa_to_en_map(medical_terms_dict: dict) -> dict:
     
        fa_to_en = dict(medical_terms_dict.get("fa_to_en", {}))
        variants = dict(medical_terms_dict.get("variants_fa", {}))

        # Allow variants to point to a canonical Persian term
        # If variant maps to a key in fa_to_en -> use that English.
        # If variant maps directly to English (e.g. "DVT") -> use it.
        resolved = {}

        # Normalize keys
        def norm(s: str) -> str:
            return llm.normalize_persian_text(s)

        fa_to_en_norm = {norm(k): v for k, v in fa_to_en.items() if isinstance(k, str)}
        for k_norm, v in fa_to_en_norm.items():
            resolved[k_norm] = v

        for var, target in variants.items():
            if not isinstance(var, str) or not isinstance(target, str):
                continue
            var_n = norm(var)
            tgt_n = norm(target)

            if tgt_n in fa_to_en_norm:         # variant -> canonical Persian
                resolved[var_n] = fa_to_en_norm[tgt_n]
            else:                               # variant -> English directly
                resolved[var_n] = target.strip()

        return resolved

    @staticmethod
    def replace_medical_terms_fa_with_en(text: str, fa_to_en: dict) -> str:
        """
        Replace ONLY matched Persian medical terms with English equivalents.
        Uses longest-first to avoid partial replacements.
        """
        if not text or not fa_to_en:
            return text

        text_n = llm.normalize_persian_text(text)

        # Sort by length desc so longer phrases match first
        items = sorted(fa_to_en.items(), key=lambda kv: len(kv[0]), reverse=True)

        # Persian/Arabic letters range + ZWNJ
        boundary_chars = r"\w\u0600-\u06FF\u200c"
        for fa_term, en_term in items:
            fa_term = llm.normalize_persian_text(fa_term)
            if not fa_term:
                continue

            pattern = rf"(?<![{boundary_chars}]){re.escape(fa_term)}(?![{boundary_chars}])"
            text_n = re.sub(pattern, en_term, text_n)

        return text_n.strip()

    def refine_transcription_fa_only(self, raw_text: str) -> str:
        
        system_prompt = """
شما یک رادیولوژیست خبره هستید. متن زیر خروجی ASR فارسی است.

وظایف شما:
1) اصلاح خطاهای شنیداری/آوایی و غلط‌های املایی با توجه به کانتکست رادیولوژی.
2) بازسازی متن به شکل یک عبارت/جمله‌بندی حرفه‌ای پزشکی به زبان فارسی.
3) هیچ جزئیات آناتومیک را حذف نکنید (مثلاً middle third، محل، سمت، سطح و ...).

قوانین سختگیرانه خروجی:
- خروجی باید فقط با حروف فارسی/عربی باشد.
- از نوشتن کلمات فارسی با حروف لاتین (transliteration) خودداری کنید.
- از نوشتن اصطلاحات انگلیسی/لاتین در این مرحله خودداری کنید.
- فقط متن نهایی را برگردانید (بدون توضیح مراحل).
        """.strip()

        refined = self.get_answer(raw_text, system_prompt)
        return self.normalize_persian_text(refined)

    def refine_transcription(self, raw_text: str, medical_terms_dict: dict) -> str:
        """
        Final pipeline:
        A) Persian-only refine (LLM)
        B) Deterministic term mapping (Python) => ONLY medical terms become English
        """
        refined_fa = self.refine_transcription_fa_only(raw_text)

        fa_to_en = self.build_fa_to_en_map(medical_terms_dict)
        mapped = self.replace_medical_terms_fa_with_en(refined_fa, fa_to_en)

        return mapped
