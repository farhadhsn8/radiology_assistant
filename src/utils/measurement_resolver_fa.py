from __future__ import annotations

import re
from typing import Optional, Set, Union

Number = Union[int, float]

_DIGITS_FA = "۰۱۲۳۴۵۶۷۸۹"
_DIGITS_AR = "٠١٢٣٤٥٦٧٨٩"
_DIGITS_EN = "0123456789"

_FA_TO_EN = str.maketrans(_DIGITS_FA, _DIGITS_EN)
_AR_TO_EN = str.maketrans(_DIGITS_AR, _DIGITS_EN)

def _to_en_digits(s: str) -> str:
    return s.translate(_FA_TO_EN).translate(_AR_TO_EN)

_UNITS = {
    "صفر": 0,
    "یک": 1, "یه": 1, "اول": 1,
    "دو": 2,
    "سه": 3,
    "چهار": 4,
    "پنج": 5,
    "شش": 6, "شیش": 6,
    "هفت": 7,
    "هشت": 8,
    "نه": 9,
}

_TEENS = {
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
}

_TENS = {
    "بیست": 20,
    "سی": 30,
    "چهل": 40,
    "پنجاه": 50,
    "شصت": 60,
    "هفتاد": 70,
    "هشتاد": 80,
    "نود": 90,
}

_HUNDREDS = {
    "صد": 100, "یکصد": 100,
    "دویست": 200,
    "سیصد": 300,
    "چهارصد": 400,
    "پانصد": 500,
    "ششصد": 600,
    "هفتصد": 700,
    "هشتصد": 800,
    "نهصد": 900,
}

_SCALES = {"هزار": 1000}

def _normalize_num_phrase(phrase: str) -> str:
    p = _to_en_digits(phrase)
    p = p.replace("‌", " ")  
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
    tokens = [t for t in re.split(r"\s+", p) if t and t != "و"]
    if not tokens:
        return None

    if tokens == ["نیم"]:
        return 0.5

    has_half = (tokens and tokens[-1] == "نیم")
    if has_half:
        tokens = tokens[:-1]
        if not tokens:
            return 0.5

    total = 0
    current = 0
    seen = False

    for tok in tokens:
        if tok in _UNITS:
            current += _UNITS[tok]; seen = True
        elif tok in _TEENS:
            current += _TEENS[tok]; seen = True
        elif tok in _TENS:
            current += _TENS[tok]; seen = True
        elif tok in _HUNDREDS:
            current += _HUNDREDS[tok]; seen = True
        elif tok in _SCALES:
            scale = _SCALES[tok]
            if current == 0:
                current = 1
            total += current * scale
            current = 0
            seen = True
        else:
            return None

    val: Number = (total + current) if seen else None
    if val is None:
        return None

    if has_half:
        val = float(val) + 0.5
    return val


def _normalize_units(text: str) -> str:
    
    text = re.sub(r"\bمیلی\s*مت(?:ر)?\b", "میلیمتر", text) 
    text = re.sub(r"\bسانتی\s*مت(?:ر)?\b", "سانتیمتر", text)

    # now map to symbols
    text = re.sub(r"\bمیلیمتر\b", "mm", text)
    text = re.sub(r"\bسانتیمتر\b", "cm", text)
    text = re.sub(r"\bسی\s*سی\b", "cc", text)
    text = re.sub(r"\bسی‌سی\b", "cc", text)
    return text

# numbers near units
_NUM_NEAR_UNIT_PATTERN = re.compile(
    r"(?P<num>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))\s*(?P<unit>mm|cm|cc|میلیمتر|سانتیمتر|سی\s*سی|سی‌سی)\b",
    flags=re.IGNORECASE,
)

def _replace_spoken_numbers_near_units(text: str) -> str:
    def repl(m: re.Match) -> str:
        num_phrase = m.group("num").strip()
        unit = m.group("unit")
        val = parse_fa_number_phrase(num_phrase)
        if val is None:
            return m.group(0)
        return f"{_format_number(val)} {unit}"
    return _NUM_NEAR_UNIT_PATTERN.sub(repl, text)


_DIM_PATTERN = re.compile(
    r"(?P<a>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))\s*(?:در|×|x)\s*"
    r"(?P<b>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?))"
    r"(?:\s*و\s*(?P<c>(?:[\d۰-۹٠-٩]+(?:\.\d+)?|[اآء-ی‌\s]+?)))?\s*"
    r"(?P<unit>mm|cm|میلیمتر|سانتیمتر)\b",
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

def resolve_measurements(text: str) -> str:
    if not text:
        return text

    text = _to_en_digits(text)
    text = _normalize_units(text)
    text = _replace_dimension_patterns(text)
    text = _replace_spoken_numbers_near_units(text)

    text = re.sub(r"[ \t]+", " ", text).strip()
    return text

def extract_allowed_numbers(text: str) -> Set[Number]:
    s = resolve_measurements(text)
    allowed: Set[Number] = set()
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", s):
        v = m.group(0)
        allowed.add(float(v) if "." in v else int(v))
    return allowed
