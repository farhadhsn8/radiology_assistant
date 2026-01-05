from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Mapping



_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]"
)


def normalize_persian_text(text: str) -> str:
    if not text:
        return text

    text = text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")

    text = _DIACRITICS_RE.sub("", text)

    text = re.sub(r"[ \t]+", " ", text).strip()
    return text


def _norm(text: str) -> str:
    return normalize_persian_text(text) if text else ""


def build_fa_to_en_map(medical_terms_dict: Mapping[str, Any]) -> Dict[str, str]:

    resolved: Dict[str, str] = {}
    conflicts: Dict[str, set[str]] = defaultdict(set)

    pt = medical_terms_dict.get("persian_transcriptions")
    if isinstance(pt, Mapping):
        for mapping in pt.values():
            if not isinstance(mapping, Mapping):
                continue
            for fa, en in mapping.items():
                if not isinstance(fa, str) or not isinstance(en, str):
                    continue

                k = _norm(fa)
                v = en.strip()
                if not k or not v:
                    continue

                if k in resolved and resolved[k] != v:
                    conflicts[k].update([resolved[k], v])
                    continue

                resolved[k] = v

        if conflicts:
            print("[FA][WARN] Conflicting medical term mappings detected:")
            for k, vals in conflicts.items():
                print(f"  - '{k}' -> {list(vals)} (kept: '{resolved.get(k)}')")

        return resolved

    fa_to_en = dict(medical_terms_dict.get("fa_to_en", {}))
    variants = dict(medical_terms_dict.get("variants_fa", {}))

    fa_to_en_norm = {
        _norm(k): str(v).strip()
        for k, v in fa_to_en.items()
        if isinstance(k, str) and v is not None
    }

    for k_norm, v in fa_to_en_norm.items():
        if k_norm and v:
            resolved[k_norm] = v

    for var, target in variants.items():
        if not isinstance(var, str) or not isinstance(target, str):
            continue

        var_n = _norm(var)
        tgt_n = _norm(target)

        if not var_n:
            continue

        if tgt_n in fa_to_en_norm:
            resolved[var_n] = fa_to_en_norm[tgt_n]
        else:
            resolved[var_n] = target.strip()

    return resolved


def _term_to_pattern(term: str) -> str | None:

    term_n = _norm(term)
    if not term_n:
        return None

    parts = [p for p in re.split(r"[\s\u200c]+", term_n) if p]
    if not parts:
        return None

    return r"[\s\u200c]+".join(re.escape(p) for p in parts)


def replace_medical_terms_fa_with_en(text: str, fa_to_en: Dict[str, str]) -> str:
   
    if not text or not fa_to_en:
        return text

    text_n = _norm(text)

    items = sorted(fa_to_en.items(), key=lambda kv: len(kv[0]), reverse=True)

    boundary_chars = r"\w\u0600-\u06FF\u200c"

    for fa_term, en_term in items:
        pat = _term_to_pattern(fa_term)
        if not pat:
            continue

        pattern = rf"(?<![{boundary_chars}]){pat}(?![{boundary_chars}])"
        text_n = re.sub(pattern, str(en_term).strip(), text_n)

    return text_n.strip()
