"""Farmer text -> crop, quantity, village, cash deadline (+ what was guessed).

Keyword tables only; no language model. Text is normalised first (Devanagari digits to ASCII,
nukta dropped, chandrabindu -> anusvara, lower-case) so the tables hold one spelling each.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from . import data_loader

# The two deadlines the contract allows for cash_needed_in_days.
CASH_SOON, CASH_WEEK = 3, 7

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUKTA, _CHANDRABINDU, _ANUSVARA = "़", "ँ", "ं"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").translate(_DEV_DIGITS).lower()
    text = text.replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    return text.replace("‌", "").replace("‍", "")


def tokenize(text: str) -> list[str]:
    """Words and numbers. Python's \\w doesn't cover Devanagari vowel signs, so split by hand."""
    text = normalize(text)
    chars = []
    for i, c in enumerate(text):
        decimal_point = (c == "." and 0 < i < len(text) - 1
                         and text[i - 1].isdigit() and text[i + 1].isdigit())
        chars.append(c if decimal_point or unicodedata.category(c)[0] not in "PSZC" else " ")
    return re.sub(r"(\d+(?:\.\d+)?)", r" \1 ", "".join(chars)).split()


def _n(*words: str) -> frozenset[str]:
    return frozenset(normalize(w) for w in words)


def _is_devanagari(text: str) -> bool:
    return any("ऀ" <= c <= "ॿ" for c in text)


# ---------- keyword tables ------------------------------------------------

_NUMBER_WORDS = {normalize(k): v for k, v in {
    # Marathi
    "एक": 1, "दोन": 2, "तीन": 3, "चार": 4, "पाच": 5, "सहा": 6, "सात": 7, "आठ": 8, "नऊ": 9,
    "दहा": 10, "अकरा": 11, "बारा": 12, "तेरा": 13, "चौदा": 14, "पंधरा": 15, "सोळा": 16,
    "सतरा": 17, "अठरा": 18, "एकोणीस": 19, "वीस": 20, "पंचवीस": 25, "तीस": 30, "पस्तीस": 35,
    "चाळीस": 40, "पंचेचाळीस": 45, "पन्नास": 50, "साठ": 60, "सत्तर": 70, "पंचाहत्तर": 75,
    "ऐंशी": 80, "नव्वद": 90, "शंभर": 100, "एकशे": 100, "दीडशे": 150, "दोनशे": 200,
    "अडीचशे": 250, "तीनशे": 300, "चारशे": 400, "पाचशे": 500, "सहाशे": 600, "सातशे": 700,
    "आठशे": 800, "नऊशे": 900, "हजार": 1000, "अर्धा": 0.5, "दीड": 1.5, "अडीच": 2.5,
    # Hindi
    "दो": 2, "पाँच": 5, "छह": 6, "छः": 6, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12,
    "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "सोलह": 16, "सत्रह": 17, "अठारह": 18, "उन्नीस": 19,
    "बीस": 20, "पच्चीस": 25, "पैंतीस": 35, "चालीस": 40, "पैंतालीस": 45, "पचास": 50,
    "पचहत्तर": 75, "अस्सी": 80, "नब्बे": 90, "सौ": 100, "आधा": 0.5, "डेढ़": 1.5, "ढाई": 2.5,
    # Latin spellings and English
    "ek": 1, "don": 2, "teen": 3, "tin": 3, "char": 4, "pach": 5, "paach": 5, "panch": 5,
    "paanch": 5, "saha": 6, "aath": 8, "nau": 9, "daha": 10, "das": 10, "dus": 10, "vis": 20,
    "wis": 20, "bees": 20, "tees": 30, "chalis": 40, "pannas": 50, "pachas": 50,
    "shambhar": 100, "sau": 100, "hajar": 1000, "hazar": 1000, "dedh": 1.5, "adich": 2.5,
    "dhai": 2.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ten": 10,
    "twenty": 20, "fifty": 50, "hundred": 100, "thousand": 1000,
}.items()}
_ORDINALS = {normalize(k): v for k, v in {
    "पहिला": 1, "पहिले": 1, "पहिली": 1, "पहला": 1, "पहली": 1, "पहले": 1,
    "दुसरा": 2, "दुसरे": 2, "दुसरी": 2, "दूसरा": 2, "दूसरी": 2, "दूसरे": 2,
    "तिसरा": 3, "तिसरे": 3, "तिसरी": 3, "तीसरा": 3, "तीसरी": 3, "तीसरे": 3,
    "चौथा": 4, "चौथे": 4, "चौथी": 4,
    "pahila": 1, "pehla": 1, "pahla": 1, "dusra": 2, "doosra": 2, "tisra": 3, "teesra": 3,
    "chautha": 4, "first": 1, "second": 2, "third": 3, "fourth": 4,
}.items()}

_UNITS = {
    "quintal": _n("क्विंटल", "क्विन्टल", "कुंटल", "क्विंटल्स", "quintal", "quintals", "qtl",
                  "qtls", "q", "kwintal", "kuntal", "kvintal", "quintle"),
    "ton": _n("टन", "ton", "tons", "tonne", "tonnes"),
    "kg": _n("किलो", "किलोग्रॅम", "किलोग्राम", "केजी", "kilo", "kilos", "kg", "kgs",
             "kilogram", "kilograms"),
    "bag": _n("पोती", "पोते", "पोतं", "पोता", "पोत्या", "गोणी", "गोण्या", "गोणे", "बोरी",
              "बोरे", "बोरा", "बोरियां", "बोऱ्या", "कट्टा", "कट्टे", "बॅग", "बैग", "बॅगा",
              "bag", "bags", "poti", "pote", "pota", "potya", "goni", "gonya", "bori",
              "bore", "bora", "boriya", "katta", "katte"),
    "crate": _n("क्रेट", "क्रेट्स", "कॅरेट", "कैरेट", "करेट", "crate", "crates", "caret",
                "carret", "karet", "kret"),
}
_UNIT_OF = {word: unit for unit, words in _UNITS.items() for word in words}

# Devanagari crop words are matched by prefix so inflected forms (कांद्याचे) still match.
_CROP_PREFIXES = {
    "onion": _n("कांद", "कान्द", "प्याज"),
    "tomato": _n("टोमॅट", "टोमेट", "टोमैट", "टोमाट", "टॉमेट", "टमाट"),
    "soybean": _n("सोयाब"),
}
_CROP_WORDS = {
    "onion": _n("kanda", "kande", "kaanda", "kandya", "pyaz", "pyaj", "pyaaz", "pyaaj",
                "piyaz", "onion", "onions"),
    "tomato": _n("tomato", "tomatoes", "tamatar", "tamater", "tomatar", "tameta", "tamata"),
    "soybean": _n("soybean", "soyabean", "soybeans", "soyabin", "soybin", "soyabeen",
                  "soya", "soy", "सोया"),
}

_DAY_WORDS = _n("दिन", "दिनों", "दिनो", "din", "dino", "day", "days")
_DAY_PREFIXES = _n("दिवस", "divas", "diwas", "divs", "diws")
_SOON = _n("आज", "आजच", "उद्या", "उद्याच", "परवा", "कल", "परसों", "aaj", "aj", "udya",
           "udyach", "parva", "kal", "parso", "today", "tomorrow")
_WEEK = _n("आठवडा", "आठवड्यात", "आठवड्याभरात", "हफ्ता", "हफ्ते", "सप्ताह", "athavda",
           "athavdyat", "aathavdyat", "hafta", "hafte", "week")
_MONEY = _n("पैसे", "पैसा", "पैसों", "पैशांची", "पैशाची", "रक्कम", "कॅश", "कैश", "paise",
            "paisa", "paishe", "cash", "money", "payment")
_URGENT = _n("लगेच", "तातडीने", "तातडी", "ताबडतोब", "तुरंत", "फौरन", "अर्जंट", "urgent",
             "urgently", "lagech", "tatadine", "turant", "arjant")
_HURRY = _n("घाई", "जल्दी", "ghai", "jaldi", "hurry")
_YES = _n("हो", "होय", "हाँ", "हा", "बरोबर", "ठीक", "सही", "ho", "hoy", "haan", "han", "ha",
          "yes", "y", "ok", "okay", "barobar", "correct", "sahi", "right")
_NO = _n("नाही", "नहीं", "नको", "चूक", "गलत", "nahi", "nahin", "nai", "no", "n", "nako",
         "chuk", "galat", "wrong")
_OTHER = _n("इतर", "अन्य", "दुसरे", "other", "another", "itar")
_STOP = _n(
    "आहे", "आहेत", "माझा", "माझे", "माझी", "माझ्या", "माझ्याकडे", "कडे", "आमच्या", "आमचे",
    "गाव", "गावात", "गावचा", "गावातून", "येथे", "येथून", "मध्ये", "मधून", "विकायचा",
    "विकायचे", "विकायची", "विकायचंय", "विकायला", "विकू", "विकणे", "आणि", "चा", "ची", "चे",
    "ला", "हून", "पासून", "साठी", "किती", "भाव", "कुठे", "कधी", "सांगा", "हवे", "हवेत",
    "हवा", "पाहिजे", "का", "है", "हैं", "में", "से", "की", "के", "को", "मेरा", "मेरे", "मेरी",
    "मुझे", "पास", "गाँव", "बेचना", "बेचनी", "बेचने", "कहाँ", "कब", "बताओ", "बताइए", "और",
    "हूँ", "चाहिए", "तक", "नमस्कार", "नमस्ते", "हॅलो", "रुपये", "मी", "आम्ही", "माल",
    "mi", "me", "maza", "majha", "majhe", "mazya", "mazyakade", "kade", "ahe", "aahe", "ahet",
    "gav", "gaav", "gaon", "gaanv", "village", "from", "in", "at", "of", "the", "my", "i",
    "we", "have", "has", "to", "sell", "want", "need", "madhe", "madhun", "yethe", "hai",
    "hain", "mein", "se", "ka", "ki", "ke", "ko", "mera", "mere", "meri", "mujhe", "pas",
    "paas", "bechna", "vikaycha", "vikayche", "sathi", "and", "is", "a", "an", "for", "it",
    "where", "when", "should", "please", "hello", "hi", "hey", "namaste", "namaskar", "rs",
    "have", "havet", "pahije", "chahiye", "by", "within", "option", "number", "mal", "maal",
)

_LANG_MARKERS = {
    "mr": _n("आहे", "आहेत", "कांदा", "कांदे", "पोती", "पोते", "गोणी", "हवे", "हवेत", "हो",
             "होय", "नाही", "उद्या", "गाव", "माझा", "माझे", "माझी", "माझ्याकडे", "मध्ये",
             "टोमॅटो", "विकायचा", "विकायचे", "किती", "आठवड्यात", "लगेच", "तातडीने", "घाई",
             "दिवस", "दिवसात", "दिवसांत", "kanda", "kande", "poti", "pote", "goni", "ahe",
             "aahe", "maza", "majha", "mazya", "divas", "diwas", "divsat", "udya", "ho", "hoy",
             "gav", "madhe", "vikaycha", "pahije", "havet", "lagech", "athavdyat"),
    "hi": _n("है", "हैं", "में", "मेरा", "मेरे", "मेरी", "प्याज", "टमाटर", "बोरी", "बोरे",
             "दिन", "दिनों", "चाहिए", "हाँ", "नहीं", "कल", "गाँव", "बेचना", "मुझे", "हफ्ते",
             "तुरंत", "जल्दी", "कितना", "pyaz", "pyaj", "pyaaz", "tamatar", "bori", "hai",
             "hain", "mein", "mera", "mere", "chahiye", "haan", "nahin", "din", "kal", "gaon",
             "gaanv", "bechna", "mujhe", "hafte", "turant", "jaldi"),
    "en": _n("onion", "onions", "tomatoes", "bags", "crates", "village", "sell", "need",
             "days", "today", "tomorrow", "week", "yes", "hello", "please", "want", "from",
             "money", "tonnes", "should"),
}

# Postpositions glued to a village name: निफाडहून, निफाडला, niphadla, niphadmadhe ...
_SUFFIXES = _n("ला", "हून", "चा", "ची", "चे", "च्या", "त", "मध्ये", "मधून", "मधील", "वरून",
               "कडे", "से", "में", "la", "hun", "hoon", "cha", "chi", "che", "chya", "t",
               "madhe", "madhye", "madhun", "varun", "kade", "se", "me", "mein")


# ---------- pieces --------------------------------------------------------

@dataclass
class _Tok:
    text: str
    kind: str                 # num | unit | crop | day | soon | week | money | urgent | hurry | yes | no | stop | word
    value: object = None
    from_word: bool = False   # a number written as a word
    used: bool = False


def _crop_of(token: str) -> str | None:
    for crop, words in _CROP_WORDS.items():
        if token in words:
            return crop
    for crop, prefixes in _CROP_PREFIXES.items():
        if token.startswith(tuple(prefixes)):
            return crop
    return None


def _classify(token: str) -> _Tok:
    if re.fullmatch(r"\d+(\.\d+)?", token):
        return _Tok(token, "num", float(token))
    if token in _NUMBER_WORDS:
        return _Tok(token, "num", float(_NUMBER_WORDS[token]), from_word=True)
    if token in _UNIT_OF:
        return _Tok(token, "unit", _UNIT_OF[token])
    crop = _crop_of(token)
    if crop:
        return _Tok(token, "crop", crop)
    if token in _DAY_WORDS or token.startswith(tuple(_DAY_PREFIXES)):
        return _Tok(token, "day")
    for kind, words in (("soon", _SOON), ("week", _WEEK), ("money", _MONEY), ("urgent", _URGENT),
                        ("hurry", _HURRY), ("yes", _YES), ("no", _NO), ("stop", _STOP)):
        if token in words:
            return _Tok(token, kind)
    return _Tok(token, "word")


def _items(text: str) -> list[_Tok]:
    """Classified tokens, with spoken compound numbers joined: दोन हजार -> 2000, दोनशे पन्नास -> 250."""
    out: list[_Tok] = []
    for tok in map(_classify, tokenize(text)):
        prev = out[-1] if out else None
        if tok.kind == "num" and tok.from_word and prev and prev.kind == "num":
            if tok.value in (100, 1000) and prev.value < 100:
                prev.value, prev.from_word = prev.value * tok.value, True
                continue
            if prev.from_word and prev.value >= 100 and tok.value < 100:
                prev.value += tok.value
                continue
        out.append(tok)
    return out


def _bucket(days: float) -> int | None:
    """A stated number of days -> the contract's deadline that never sells later than that."""
    if days < CASH_WEEK:
        return CASH_SOON
    if days < max(data_loader.cfg("horizons")):
        return CASH_WEEK
    return None


def _mark_days(items: list[_Tok]) -> float | None:
    """'2 दिवस' / '2 din': returns the number and marks it so it isn't read as the quantity."""
    days = None
    for i, tok in enumerate(items):
        if tok.kind == "day" and i > 0 and items[i - 1].kind == "num":
            items[i - 1].used = True
            days = items[i - 1].value
    return days


def _cash(items: list[_Tok], days: float | None, need_money_word: bool) -> tuple[bool, int | None]:
    """(deadline known?, cash_needed_in_days)."""
    kinds = {t.kind for t in items}
    if "hurry" in kinds and "no" in kinds:                     # घाई नाही / no hurry
        return True, None
    money, urgent = "money" in kinds, bool(kinds & {"urgent", "hurry"})
    if need_money_word and not (money or urgent):
        return False, None
    if days is not None:
        return True, _bucket(days)
    if "soon" in kinds or (money and urgent) or (not need_money_word and urgent):
        return True, CASH_SOON
    if "week" in kinds:
        return True, CASH_WEEK
    return False, None


def _phon(text: str) -> str:
    """Rough sound key so nifad = niphad and नीफाड = निफाड."""
    if _is_devanagari(text):
        return text.replace("ी", "ि").replace("ू", "ु")
    for a, b in (("ph", "f"), ("w", "v"), ("sh", "s"), ("aa", "a"), ("ee", "i"), ("oo", "u"),
                 ("gaanv", "gaon"), ("gav", "gaon"), ("gao", "gaon"), ("gaonn", "gaon")):
        text = text.replace(a, b)
    return re.sub(r"(.)\1+", r"\1", text)


def _village_scores(candidates: list[str]) -> list[tuple[float, bool, dict]]:
    """(score, exact, village) for every village, best first. exact = spelled as in villages.csv."""
    scored = []
    for village in data_loader.villages():
        spellings = {normalize(village[k]) for k in ("village", "name_mr", "name_hi")}
        best, exact = 0.0, False
        for text in candidates:
            for name in spellings:
                if _is_devanagari(text) != _is_devanagari(name):
                    continue
                if text == name or (text.startswith(name) and text[len(name):] in _SUFFIXES):
                    best, exact = 1.0, True
                    continue
                a, b = _phon(text), _phon(name)
                best = max(best, 1.0 if a == b else SequenceMatcher(None, a, b).ratio())
        scored.append((best, exact, village))
    scored.sort(key=lambda s: (-s[0], not s[1]))   # stable: ties keep villages.csv order
    return scored


def detect_lang(text: str) -> str:
    """Hindi or Marathi by marker words (Devanagari or romanised). Otherwise: Latin script is English,
    Devanagari is Marathi."""
    tokens = tokenize(text)
    count = {lang: sum(t in words for t in tokens) for lang, words in _LANG_MARKERS.items()}
    if count["hi"] > count["mr"]:
        return "hi"
    if count["mr"]:
        return "mr"
    return "mr" if _is_devanagari(text) else "en"


# ---------- the parse -----------------------------------------------------

@dataclass
class Parsed:
    lang: str = "mr"
    crop: str | None = None
    qty_value: float | None = None      # the number as typed
    qty_unit: str | None = None         # quintal | ton | kg | bag | crate; None = no unit said
    village: dict | None = None         # villages.csv row, matched at or above the threshold
    village_exact: bool = False         # False = fuzzy match, so it was guessed
    village_candidates: list[dict] = field(default_factory=list)   # top 3 when a name didn't match
    cash_known: bool = False
    cash_days: int | None = None


def parse(text: str) -> Parsed:
    items = _items(text)
    p = Parsed(lang=detect_lang(text))
    p.crop = next((t.value for t in items if t.kind == "crop"), None)

    days = _mark_days(items)
    p.cash_known, p.cash_days = _cash(items, days, need_money_word=True)

    free = [t for t in items if t.kind == "num" and not t.used and t.value > 0]
    paired = next(((t, items[i + 1].value) for i, t in enumerate(items[:-1])
                   if t in free and items[i + 1].kind == "unit"), None)
    if paired:
        p.qty_value, p.qty_unit = paired[0].value, paired[1]
    elif free:
        units = [t.value for t in items if t.kind == "unit"]
        p.qty_value, p.qty_unit = free[0].value, (units[0] if len(units) == 1 else None)

    words = [(i, t.text) for i, t in enumerate(items) if t.kind == "word" and len(t.text) >= 2]
    candidates = [w for _, w in words]
    for (i, a), (j, b) in zip(words, words[1:]):
        if j == i + 1:                                   # two-word names, or one name split in two
            candidates += [a + b, f"{a} {b}"]
    if candidates:
        scored = _village_scores(candidates)
        score, exact, village = scored[0]
        if score >= data_loader.cfg("parser", "village_match_threshold"):
            p.village, p.village_exact = village, exact
        else:
            p.village_candidates = [v for _, _, v in scored[:3]]
    return p


def to_quintals(crop: str, value: float, unit: str | None) -> float | None:
    """Quantity in quintals, or None if this crop has no weight for that unit (e.g. onion crates)."""
    if unit in (None, "quintal"):
        qtl = float(value)
    elif unit == "ton":
        qtl = value * 10
    elif unit == "kg":
        qtl = value / 100
    else:
        kg = data_loader.cfg("units", f"{unit}_kg").get(crop)
        if kg is None:
            return None
        qtl = value * kg / 100
    qtl = round(qtl, 2)
    return int(qtl) if qtl.is_integer() else qtl


def unit_guessed(unit: str | None) -> bool:
    """No unit (we assumed quintals) or a bag/crate weight from config: both need the echo-back."""
    return unit in (None, "bag", "crate")


def is_new_request(p: Parsed) -> bool:
    """A fresh crop message, as opposed to an answer to the open question."""
    return p.crop is not None and (p.village is not None or p.qty_unit is not None)


def parse_message(text: str) -> dict:
    """The parse as plain data: crop, quantity_qtl, village, plus what was guessed or missing."""
    p = parse(text)
    qtl = to_quintals(p.crop, p.qty_value, p.qty_unit) if p.crop and p.qty_value is not None else None
    guessed = []
    if p.qty_value is not None and unit_guessed(p.qty_unit):
        guessed.append("unit")
    if p.village and not p.village_exact:
        guessed.append("village")
    missing = [name for name, value in (("crop", p.crop), ("quantity", p.qty_value),
                                        ("village", p.village)) if value is None]
    return {"crop": p.crop, "quantity_qtl": qtl, "village": p.village["village"] if p.village else None,
            "guessed": guessed, "missing": missing, "lang": p.lang,
            "cash_needed_in_days": p.cash_days, "cash_known": p.cash_known,
            "village_options": [v["village"] for v in p.village_candidates]}


# ---------- answers to the bot's questions --------------------------------

def yes_no(text: str) -> bool | None:
    kinds = {t.kind for t in _items(text)}
    if ("yes" in kinds) == ("no" in kinds):
        return None
    return "yes" in kinds


def choice(text: str, upto: int) -> int | None:
    """A numbered answer: '1', '१', 'एक', 'पहिला', 'option 2'. None if the message is anything else."""
    tokens = tokenize(text)
    if not 1 <= len(tokens) <= 3:
        return None
    numbers = []
    for token in tokens:
        if re.fullmatch(r"\d+", token):
            numbers.append(int(token))
        elif token in _ORDINALS:
            numbers.append(_ORDINALS[token])
        elif token in _NUMBER_WORDS and float(_NUMBER_WORDS[token]).is_integer():
            numbers.append(int(_NUMBER_WORDS[token]))
    if len(numbers) == 1 and 1 <= numbers[0] <= upto:
        return numbers[0]
    return None


def is_other(text: str) -> bool:
    return any(t in _OTHER for t in tokenize(text))


def freshness_answer(crop: str, text: str) -> tuple[bool, object]:
    """(understood?, lot_condition). Tomato: 0 | 1 | 2. Onion, soybean: True | False."""
    if crop == "tomato":
        items = _items(text)
        days = _mark_days(items)
        if days is not None:                               # 'picked 2 days ago'
            return True, 0 if days < 1 else (1 if days <= 2 else 2)
        picked = choice(text, 3)
        if picked:
            return True, picked - 1
        if any(t.text in _n("आज", "आजच", "aaj", "aj", "today") for t in items):
            return True, 0
        return False, None
    picked = choice(text, 2)
    if picked:
        return True, picked == 1
    answer = yes_no(text)
    return answer is not None, answer


_PRICE_WORDS = _n("per", "प्रति", "rs", "रु", "रुपये", "रुपए", "rupees", "rupaye", "bhav", "भाव", "दर",
                  "rate", "price", "offer", "ऑफर")


def offer_per_quintal(text: str) -> float | None:
    """A quoted price such as '23 per kg', '2300 per quintal' or '₹2300/क्विंटल', in ₹ per quintal.
    None unless the message has one number, a kg or quintal unit, and a price word, ₹ or '/'."""
    tokens = tokenize(text.replace(",", ""))
    marked = "₹" in text or "/" in text or any(t in _PRICE_WORDS for t in tokens)
    units = {_UNIT_OF[t] for t in tokens if t in _UNIT_OF}
    numbers = [float(t) for t in tokens if re.fullmatch(r"\d+(?:\.\d+)?", t)]
    if not marked or len(numbers) != 1 or numbers[0] <= 0 or units not in ({"kg"}, {"quintal"}):
        return None
    return numbers[0] * 100 if units == {"kg"} else numbers[0]     # 1 quintal = 100 kg


def cash_answer(text: str) -> tuple[bool, int | None]:
    """(understood?, cash_needed_in_days) for 'by when do you need the money?'."""
    items = _items(text)
    days = _mark_days(items)
    if days is None:
        picked = choice(text, 3)
        if picked:
            return True, (CASH_SOON, CASH_WEEK, None)[picked - 1]
    return _cash(items, days, need_money_word=False)


@data_loader.with_example_data
def _selftest():
    def check(text, **want):
        got = parse_message(text)
        for key, value in want.items():
            assert got[key] == value, f"{text!r}: {key} = {got[key]!r}, wanted {value!r}"

    assert tokenize("२० पोती, कांदा!") == ["20", "पोती", "कांदा"]
    assert tokenize("20kg 2.5ton") == ["20", "kg", "2.5", "ton"]
    check("20 poti kanda Niphad", crop="onion", quantity_qtl=10, village="Niphad",
          guessed=["unit"], missing=[], lang="mr")
    check("२० क्विंटल कांदा निफाड", crop="onion", quantity_qtl=20, village="Niphad", guessed=[])
    check("वीस पोती कांदा निफाड", quantity_qtl=10, village="Niphad")
    check("2 टन प्याज लासलगाँव", crop="onion", quantity_qtl=20, village="Lasalgaon",
          guessed=[], lang="hi")
    check("500 kg tamatar Narayangaon", crop="tomato", quantity_qtl=5, village="Narayangaon",
          guessed=[], lang="hi")
    check("30 crate tomato narayangaon", crop="tomato", quantity_qtl=6, guessed=["unit"])
    check("30 crate kanda niphad", crop="onion", quantity_qtl=None)        # no crate weight for onion
    check("10 quintal soyabean Nifad", crop="soybean", quantity_qtl=10, village="Niphad",
          guessed=["village"])
    check("kanda 15 niphad", quantity_qtl=15, guessed=["unit"])
    check("निफाडहून 20 क्विंटल कांदा", village="Niphad", guessed=[])
    check("दीड टन सोयाबीन औसा", crop="soybean", quantity_qtl=15, village="Ausa")
    check("दोन हजार किलो कांदा येवला", quantity_qtl=20, village="Yeola")
    check("एकशे वीस क्विंटल कांदा निफाड", quantity_qtl=120)                 # spoken numbers from voice notes
    check("एक सौ बीस बोरी प्याज येवला", quantity_qtl=60, lang="hi")
    check("अठरा क्विंटल सोयाबीन औसा", quantity_qtl=18)
    check("माझ्याकडे ४० गोणी कांदा आहे, गाव विंचूर", quantity_qtl=20, village="Vinchur")
    check("टोमॅटो 100 क्रेट नारायणगावहून", crop="tomato", quantity_qtl=20, village="Narayangaon")
    check("pyaz 10 bori Manmad 5 din me paise chahiye", quantity_qtl=5, cash_needed_in_days=3)
    check("20 bags onion Sinnar", crop="onion", quantity_qtl=10, village="Sinnar", lang="en")
    check("20 poti kanda Pune", village=None, missing=["village"])
    assert len(parse_message("20 poti kanda Pune")["village_options"]) == 3
    check("kanda niphad", missing=["quantity"])
    check("20 quintal niphad", crop=None, missing=["crop"])
    check("hello", crop=None, quantity_qtl=None, village=None)
    check("20 poti kanda Niphad 2 divsat paise have", quantity_qtl=10, cash_needed_in_days=3,
          cash_known=True)
    check("२० क्विंटल कांदा निफाड, पैसे या आठवड्यात हवेत", cash_needed_in_days=7, cash_known=True)
    check("10 quintal pyaz Yeola paise turant chahiye", cash_needed_in_days=3, lang="hi")
    check("10 quintal pyaz Yeola paise jaldi chahiye", cash_needed_in_days=3, cash_known=True)
    check("कांदा लगेच विकायचा आहे 20 क्विंटल निफाड", cash_known=False)      # urgency without money or a date
    check("आज 20 क्विंटल कांदा निफाड", cash_known=False)                    # 'today' without a money word
    assert (yes_no("हो"), yes_no("नाही"), yes_no("haan"), yes_no("kanda")) == (True, False, True, None)
    assert (choice("1", 2), choice("१", 2), choice("दोन", 3), choice("पहिला", 3)) == (1, 1, 2, 1)
    assert choice("5", 3) is None and choice("20 poti kanda niphad", 3) is None
    assert freshness_answer("tomato", "2") == (True, 1) and freshness_answer("tomato", "आज") == (True, 0)
    assert freshness_answer("tomato", "3 दिवसांपूर्वी") == (True, 2)
    assert freshness_answer("onion", "1") == (True, True) and freshness_answer("onion", "नाही") == (True, False)
    assert freshness_answer("soybean", "maybe") == (False, None)
    assert cash_answer("1") == (True, 3) and cash_answer("2") == (True, 7) and cash_answer("3") == (True, None)
    assert cash_answer("2 दिवस") == (True, 3) and cash_answer("घाई नाही") == (True, None)
    assert cash_answer("या आठवड्यात") == (True, 7) and cash_answer("उद्या") == (True, 3)
    assert cash_answer("10 din") == (True, 7) and cash_answer("kanda") == (False, None)
    assert is_new_request(parse("5 ton tomato Otur")) and not is_new_request(parse("हो कांदा वाळलेला आहे"))
    print("parser ok")


if __name__ == "__main__":
    _selftest()
