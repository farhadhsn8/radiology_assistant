from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from src.services.llm.llm import llm
from src.utils.measurement_resolver_fa import resolve_measurements
from src.utils.normalize_and_mapping import (
    build_fa_to_en_map,
    replace_medical_terms_fa_with_en,
    normalize_persian_text,
)


class FarsiTranscriptionRefiner:
    """
    Central LLM-based refiner for Farsi radiology reports:

    - Pre-normalizing raw ASR text (digits + units)
    - Persian-only refinement
    - Mapping Persian medical phrases → canonical English terms
    - Proofreading final report
    - Template-based report generation from 'materials' + 'prompt'
    """

    def __init__(
        self,
        llm_client: llm,
        refine_prompt_path: str = "assets/prompts/refine_fa.txt",
        proofread_prompt_path: str = "assets/prompts/report_editor_fa.txt",
    ) -> None:
        self.llm_client = llm_client
        self.refine_prompt_path = refine_prompt_path
        self.proofread_prompt_path = proofread_prompt_path

        self._refine_prompt_cache: Optional[str] = None
        self._proofread_prompt_cache: Optional[str] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_prompt_file(path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            raise ValueError(f"Empty prompt: {path}")
        return content

    def _read_refine_prompt(self) -> str:
        if self._refine_prompt_cache is None:
            self._refine_prompt_cache = self._read_prompt_file(self.refine_prompt_path)
        return self._refine_prompt_cache

    def _read_proofread_prompt(self) -> str:
        if self._proofread_prompt_cache is None:
            self._proofread_prompt_cache = self._read_prompt_file(
                self.proofread_prompt_path
            )
        return self._proofread_prompt_cache

    def _preprocess_raw(self, raw_text: str) -> str:
        """
        Deterministic preprocessing *before* sending text to the LLM.

        - Normalize digits/measurements (resolve_measurements)
        - Basic Persian normalization
        """
        if not raw_text:
            return raw_text

        text = resolve_measurements(raw_text)
        text = normalize_persian_text(text)
        return text

    def _extract_numbers_in_order(self, text: str) -> List[str]:
        """
        Extract numeric tokens (as strings) from text in order of appearance.
        """
        if not text:
            return []
        normalized = resolve_measurements(text)
        return re.findall(r"\b\d+(?:\.\d+)?\b", normalized)

    def _sync_numbers_with_original(
        self,
        refined_text: str,
        original_numbers: List[str],
    ) -> str:
        """
        If LLM changed numeric values but count is the same,
        force the refined text to use the original numeric sequence.

        Generic guard – هیچ عدد خاصی هاردکد نشده.
        """
        if not refined_text or not original_numbers:
            return refined_text

        current_numbers = self._extract_numbers_in_order(refined_text)
        if not current_numbers:
            return refined_text

        if len(current_numbers) != len(original_numbers):
            # ساختار عددی خیلی فرق کرده، برای احتیاط دست نمی‌زنیم
            print(
                "[FA][WARN] Number count changed: "
                f"{len(original_numbers)} -> {len(current_numbers)}"
            )
            return refined_text

        if current_numbers == original_numbers:
            return refined_text  # همه چیز اوکی است

        idx = 0

        def repl(m: re.Match) -> str:
            nonlocal idx
            if idx >= len(original_numbers):
                return m.group(0)
            val = original_numbers[idx]
            idx += 1
            return val

        base = resolve_measurements(refined_text)
        synced = re.sub(r"\b\d+(?:\.\d+)?\b", repl, base)
        return synced

    @staticmethod
    def _strip_unfilled_placeholders(text: str) -> str:
        """
        Remove lines that still contain '...' or '___' style placeholders.
        Used after template filling.
        """
        if not text:
            return text

        # Remove parenthetical chunks that clearly contain placeholders
        text = re.sub(r"\([^)]*(?:\.\.\.|_{2,})[^)]*\)", "", text)

        lines = []
        for line in text.splitlines():
            if ("..." in line) or re.search(r"_{2,}", line):
                continue
            lines.append(line)

        cleaned = []
        for line in lines:
            # Do not touch HTML-like lines
            if "<" in line and ">" in line:
                cleaned.append(line.rstrip())
                continue
            l = re.sub(r"[ \t]{2,}", " ", line)
            l = re.sub(r"\s+([،:؛.])", r"\1", l)
            cleaned.append(l.rstrip())

        out = "\n".join(cleaned)
        out = re.sub(r"\n{3,}", "\n\n", out).strip()
        return out

    @staticmethod
    def _post_process_final_report(model_output: str) -> str:
        """
        Extract "final_report" from JSON-like model output.
        """
        if not model_output:
            return ""

        # Try strict JSON first
        try:
            data = json.loads(model_output)
            if isinstance(data, dict) and "final_report" in data:
                val = data["final_report"]
                return str(val).strip() if val is not None else ""
        except Exception:
            pass

        # Fallback: regex extract "final_report":"..."
        m = re.search(
            r'"\s*final_report\s*"\s*:\s*"((?:[^"\\]|\\.)*)"',
            model_output,
            re.DOTALL,
        )
        if not m:
            return model_output.strip()

        raw_val = m.group(1)
        try:
            val = json.loads(f'{{"final_report":"{raw_val}"}}')["final_report"]
            return str(val).strip()
        except Exception:
            try:
                return raw_val.encode("utf-8").decode("unicode_escape").strip()
            except Exception:
                return raw_val.strip()

    # ------------------------------------------------------------------
    # Public: Persian-only refine + mapping + proofread
    # ------------------------------------------------------------------

    def refine_transcription_fa_only(self, raw_text: str) -> str:
        """
        Use LLM to produce fluent Persian text only (no term mapping).
        """
        preprocessed = self._preprocess_raw(raw_text)
        original_numbers = self._extract_numbers_in_order(preprocessed)

        prompt = self._read_refine_prompt()
        refined = self.llm_client.get_answer(preprocessed, prompt)
        refined_norm = normalize_persian_text(refined)

        if original_numbers:
            refined_norm = self._sync_numbers_with_original(
                refined_norm,
                original_numbers,
            )

        return refined_norm

    def refine_transcription(
        self,
        raw_text: str,
        medical_terms_dict: Dict[str, Any],
    ) -> str:
        """
        Full pipeline for a free-text (non-template) output:
        1) Deterministic pre-normalization of measurements
        2) LLM-based Persian refinement (with numeric guard)
        3) Map Persian medical phrases → canonical English terms
        """
        refined_fa = self.refine_transcription_fa_only(raw_text)
        fa_to_en = build_fa_to_en_map(medical_terms_dict) if medical_terms_dict else {}
        if fa_to_en:
            refined_fa = replace_medical_terms_fa_with_en(refined_fa, fa_to_en)
        return refined_fa

    def proofread_report(self, report_text: str) -> str:
        """
        Proofread an already-structured Persian report (no structural changes).
        """
        if not report_text:
            return report_text
        prompt = self._read_proofread_prompt()
        out = self.llm_client.get_answer(report_text, prompt)
        return normalize_persian_text(out)

    # ------------------------------------------------------------------
    # Public: Template-based structured report generation
    # ------------------------------------------------------------------

    def generate_structured_report_from_materials(
        self,
        materials: str,
        system_prompt: str,
        medical_terms_dict: Optional[Dict[str, Any]] = None,
        source_numbers_text: Optional[str] = None,
    ) -> str:
        """
        End-to-end template-based report:

        materials:
            Combined text (template + dictated text + rules) prepared by ReporterFA.
        system_prompt:
            General prompt that explains how to use the template (e.g. general_prompt_persian.txt).
        medical_terms_dict:
            Mapping config (configs/medical_terms.json).
        source_numbers_text:
            Text used as source-of-truth for numeric values (e.g. raw dictation).
        """
        # 1) Original numeric sequence from dictation (for guard)
        original_numbers: List[str] = []
        if source_numbers_text:
            original_numbers = self._extract_numbers_in_order(source_numbers_text)

        # 2) LLM call
        out = self.llm_client.get_answer(materials, system_prompt)

        # 3) Extract final_report field
        report = self._post_process_final_report(out)

        # 4) Strip any leftover placeholders from template
        report = self._strip_unfilled_placeholders(report)

        # 5) Numeric guard at report-level
        if original_numbers:
            report = self._sync_numbers_with_original(report, original_numbers)

        # 6) Deterministic mapping (all terms)
        if medical_terms_dict:
            fa_to_en = build_fa_to_en_map(medical_terms_dict)
            if fa_to_en:
                report = replace_medical_terms_fa_with_en(report, fa_to_en)

        # 7) Final proofread (optional) – does not change numbers (prompt rules)
        report = self.proofread_report(report)

        return report.strip()
