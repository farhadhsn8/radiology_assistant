from __future__ import annotations

import json
import os
import re
from typing import Optional, Set, Union

Number = Union[int, float]


_DIGITS_FA = "۰۱۲۳۴۵۶۷۸۹"
_DIGITS_AR = "٠١٢٣٤٥٦٧٨٩"
_DIGITS_EN = "0123456789"

_FA_TO_EN = str.maketrans(_DIGITS_FA, _DIGITS_EN)
_AR_TO_EN = str.maketrans(_DIGITS_AR, _DIGITS_EN)


def _to_en_digits(text: str) -> str:

    return text.translate(_FA_TO_EN).translate(_AR_TO_EN)



_WORD_VALUE = {
    "صفر": 0,
    "یک": 1,
    "یه": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "پنج": 5,
    "شش": 6,
    "شیش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,
    "ده": 10,
    "یازده": 11,
    "دوازده": 12,
    "سیزده": 13,
    "چهارده": 14,
    "پانزده": 15,
    "شانزده": 16,
    "هفده": 17,
    "هجده": 18,
    "نوزده": 19,
    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
    "صد": 100,
    "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
    "ششصد": 600,
    "هفتصد": 700,
    "هشتصد": 800,
    "نهصد": 900,
}

_SCALE_VALUE = {"هزار": 1000}









def _normalize_num_phrase(phrase: str) -> str:
  
    p = _to_en_digits(phrase).replace("‌", " ")
    p = p.replace(",", ".")
    p = re.sub(r"\s+", " ", p).strip()
    p = re.sub(r"\s*و\s*", " و ", p).strip()
    return p


def _format_number(v: Number) -> str:
  
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def parse_fa_number_phrase(phrase: str) -> Optional[Number]:
    
    if not phrase:
        return None

    p = _normalize_num_phrase(phrase)

   
    if re.fullmatch(r"\d+(?:\.\d+)?", p):
        return float(p) if "." in p else int(p)

    tokens = [t for t in p.split() if t != "و"]
    if not tokens:
        return None

    total = 0
    current = 0
    half = False
    seen = False

    for tok in tokens:
        if tok == "نیم":
            half = True
            seen = True
            continue

        if tok in _WORD_VALUE:
            current += _WORD_VALUE[tok]
            seen = True
            continue

        if tok in _SCALE_VALUE:
            scale = _SCALE_VALUE[tok]
            total += (current or 1) * scale
            current = 0
            seen = True
            continue

        
        return None

    if not seen:
        return None

    val: Number = total + current + (0.5 if half else 0.0)
    return val



_UNIT_PATTERN = re.compile(
    r"(میلی\s*مت(?:ر)?|سانتی\s*مت(?:ر)?|سی(?:\s*سی|‌سی))",
    flags=re.IGNORECASE,
)


def _normalize_units(text: str) -> str:
  
    def repl(m: re.Match) -> str:
        raw = m.group(0)
        compact = re.sub(r"[\s‌]", "", raw)
        if compact.startswith("میلی"):
            return "mm"
        if compact.startswith("سانتی"):
            return "cm"
        return "cc"

    return _UNIT_PATTERN.sub(repl, text)

_DIM_PATTERN = re.compile(
    r"(?P<a>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))\s*(?:در|×|x|\*)\s*"
    r"(?P<b>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))"
    r"(?:\s*و\s*(?P<c>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?)))?\s*"
    r"(?P<unit>mm|cm)\b",
    flags=re.IGNORECASE,
)

_NUM_NEAR_UNIT_PATTERN = re.compile(
    r"(?P<num>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))\s*(?P<unit>mm|cm|cc)\b",
    flags=re.IGNORECASE,
)


def _replace_dimension_patterns(text: str) -> str:
 
    def repl(m: re.Match) -> str:
        a = parse_fa_number_phrase(m.group("a"))
        b = parse_fa_number_phrase(m.group("b"))
        c_raw = m.group("c")
        c = parse_fa_number_phrase(c_raw) if c_raw else None
        unit = m.group("unit")

        if a is None or b is None:
            return m.group(0)
        if c_raw is not None and c is None:
            return m.group(0)

        if c is None:
            return f"{_format_number(a)}×{_format_number(b)} {unit}"
        return f"{_format_number(a)}×{_format_number(b)}×{_format_number(c)} {unit}"

    return _DIM_PATTERN.sub(repl, text)


def _replace_spoken_numbers_near_units(text: str) -> str:
    
    def repl(m: re.Match) -> str:
        val = parse_fa_number_phrase(m.group("num").strip())
        if val is None:
            return m.group(0)
        return f"{_format_number(val)} {m.group('unit')}"

    return _NUM_NEAR_UNIT_PATTERN.sub(repl, text)


def resolve_measurements(text: str) -> str:
  
    if not text:
        return text

    out = _to_en_digits(text)
    out = _normalize_units(out)
    out = _replace_dimension_patterns(out)
    out = _replace_spoken_numbers_near_units(out)
    out = re.sub(r"[ \t]+", " ", out).strip()
    return out


def extract_allowed_numbers(text: str) -> Set[Number]:
 
    s = resolve_measurements(text)
    nums: Set[Number] = set()
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", s):
        v = m.group(0)
        nums.add(float(v) if "." in v else int(v))
    return nums
