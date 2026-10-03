"""Every piece of text the bot sends, in Marathi, Hindi and English.

Templates only: all numbers come from the engine and no language model writes a reply.
A Marathi and a Hindi speaker must read every template before the demo.
"""
from __future__ import annotations

import re
from datetime import date

LANGS = ("mr", "hi", "en")

CROP = {
    "onion": {"mr": "कांदा", "hi": "प्याज", "en": "onion"},
    "tomato": {"mr": "टोमॅटो", "hi": "टमाटर", "en": "tomato"},
    "soybean": {"mr": "सोयाबीन", "hi": "सोयाबीन", "en": "soybean"},
}
UNIT = {
    "quintal": {"mr": "क्विंटल", "hi": "क्विंटल", "en": "quintal"},
    "ton": {"mr": "टन", "hi": "टन", "en": "tonne"},
    "kg": {"mr": "किलो", "hi": "किलो", "en": "kg"},
    "bag": {"mr": "पोती", "hi": "बोरी", "en": "bags"},
    "crate": {"mr": "क्रेट", "hi": "क्रेट", "en": "crates"},
}
CONFIDENCE = {
    "high": {"mr": "जास्त", "hi": "ज़्यादा", "en": "high"},
    "medium": {"mr": "मध्यम", "hi": "मध्यम", "en": "medium"},
    "low": {"mr": "कमी", "hi": "कम", "en": "low"},
}
MONTHS = {
    "mr": ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट",
           "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त",
           "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}

# Devanagari spellings of market names as they appear in mandi price data. The engine returns
# the Latin name from prices_mh.csv; an unknown name is shown as it is.
MANDI_DEVANAGARI = {
    "lasalgaon": "लासलगाव", "niphad": "निफाड", "vinchur": "विंचूर", "pimpalgaon": "पिंपळगाव",
    "pimpalgaon baswant": "पिंपळगाव बसवंत", "saykheda": "सायखेडा", "yeola": "येवला",
    "manmad": "मनमाड", "nashik": "नाशिक", "nasik": "नाशिक", "sinnar": "सिन्नर",
    "satana": "सटाणा", "kalwan": "कळवण", "kalvan": "कळवण", "chandwad": "चांदवड",
    "chandvad": "चांदवड", "deola": "देवळा", "devala": "देवळा", "dindori": "दिंडोरी",
    "vani": "वणी", "malegaon": "मालेगाव", "nandgaon": "नांदगाव", "umrane": "उमराणे",
    "nampur": "नामपूर", "ghoti": "घोटी", "ozar": "ओझर", "chandori": "चांदोरी",
    "pune": "पुणे", "moshi": "मोशी", "pimpri": "पिंपरी", "junnar": "जुन्नर",
    "narayangaon": "नारायणगाव", "otur": "ओतूर", "alephata": "आळेफाटा", "khed": "खेड",
    "chakan": "चाकण", "manchar": "मंचर", "solapur": "सोलापूर", "kolhapur": "कोल्हापूर",
    "ahmednagar": "अहमदनगर", "ahilyanagar": "अहिल्यानगर", "rahuri": "राहुरी",
    "rahata": "राहाता", "sangamner": "संगमनेर", "kopargaon": "कोपरगाव",
    "shrirampur": "श्रीरामपूर", "parner": "पारनेर", "akole": "अकोले", "latur": "लातूर",
    "udgir": "उदगीर", "ausa": "औसा", "nilanga": "निलंगा", "murud": "मुरुड",
    "washim": "वाशिम", "karanja": "कारंजा", "risod": "रिसोड", "mangrulpir": "मंगरूळपीर",
    "mangrulpeer": "मंगरूळपीर", "akola": "अकोला", "murtizapur": "मूर्तिजापूर",
    "amravati": "अमरावती", "amarawati": "अमरावती", "khamgaon": "खामगाव",
    "chikhli": "चिखली", "chikhali": "चिखली", "buldhana": "बुलढाणा", "mehkar": "मेहकर",
    "malkapur": "मलकापूर", "hingoli": "हिंगोली", "nanded": "नांदेड", "jalna": "जालना",
    "nagpur": "नागपूर", "mumbai": "मुंबई", "vashi": "वाशी", "aurangabad": "औरंगाबाद",
    "chhatrapati sambhajinagar": "छत्रपती संभाजीनगर", "jalgaon": "जळगाव", "dhule": "धुळे",
    "barshi": "बार्शी", "lonand": "लोणंद", "satara": "सातारा", "sangli": "सांगली",
    "hinganghat": "हिंगणघाट", "wardha": "वर्धा", "yavatmal": "यवतमाळ",
    "parbhani": "परभणी", "beed": "बीड", "dharashiv": "धाराशिव", "osmanabad": "उस्मानाबाद",
}

_T = {
    "mr": {
        "hold_head": "🟢 *{days} दिवस थांबा → {mandi}*",
        "hold_money": "💰 हातात अंदाजे ₹{net}/क्विंटल (₹{low}–₹{high})",
        "sell_head": "🔴 *आजच विका → {mandi}*",
        "sell_money": "💰 हातात अंदाजे ₹{net}/क्विंटल",
        "gain": "📈 आज जवळच्या बाजारापेक्षा ₹{gain} जास्त",
        "nearest_best": "📈 जवळचा बाजारच सर्वोत्तम आहे",
        "break_even": "⚠️ भाव ₹{breakeven} च्या वर असेल तरच जा. निघण्यापूर्वी खात्री करा",
        "tip": "📦 साठवण: {tip}",
        "success": "📊 मागील हंगामात थांबण्याचा सल्ला {pct}% वेळा फायद्याचा ठरला",
        "unreliable": "ℹ️ येथे अंदाज विश्वासार्ह नाही; फक्त आजच्या भावांची तुलना केली",
        "hold_suppressed": "ℹ️ {mandi} येथे {days} दिवस थांबल्यास ₹{extra}/क्विंटल जास्त मिळू शकतात, पण मागील "
                           "हंगामात असा सल्ला {total} पैकी फक्त {won} वेळा फायद्याचा ठरला. म्हणून आजच विका.",
        "note": "ℹ️ {note}",
        "footer": "🗓 {date} च्या भावांनुसार · खात्री: {confidence}",
        "correct": "बरोबर? 1) हो 2) नाही",
        "village_unclear": "गाव नक्की समजले नाही. कोणते?",
        "other": "इतर",
        "not_covered": "माफ करा, हे गाव अजून आमच्या यादीत नाही.",
        "resend": "ठीक आहे. कृपया पुन्हा पाठवा: पीक, किती माल आणि गाव.\nउदा. {example}",
        "help": "नमस्कार! हे SellSmart आहे. पीक, किती माल आणि गाव पाठवा; "
                "कुठे आणि कधी विकावे ते आम्ही सांगू.\nउदा. {example}\nपिके: {crops}",
        "ask_crop": "कोणते पीक? सध्या {crops} एवढीच पिके आहेत.",
        "ask_quantity": "किती माल आहे? उदा. 20 क्विंटल किंवा 40 पोती",
        "ask_village": "गाव कोणते?",
        "pick_number": "कृपया दिलेल्या पर्यायांपैकी क्रमांक पाठवा.",
        "error": "माफ करा, आत्ता सल्ला देता आला नाही. थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "cash": "पैसे कधीपर्यंत हवेत?\n1) 2–3 दिवसांत\n2) या आठवड्यात\n3) घाई नाही",
        "example": "20 पोती कांदा {village}",
    },
    "hi": {
        "hold_head": "🟢 *{days} दिन रुकें → {mandi}*",
        "hold_money": "💰 हाथ में लगभग ₹{net}/क्विंटल (₹{low}–₹{high})",
        "sell_head": "🔴 *आज ही बेचें → {mandi}*",
        "sell_money": "💰 हाथ में लगभग ₹{net}/क्विंटल",
        "gain": "📈 आज पास की मंडी से ₹{gain} ज़्यादा",
        "nearest_best": "📈 पास की मंडी ही सबसे अच्छी है",
        "break_even": "⚠️ भाव ₹{breakeven} से ऊपर हो तभी जाएँ. निकलने से पहले पक्का करें",
        "tip": "📦 भंडारण: {tip}",
        "success": "📊 पिछले सीज़न में रुकने की सलाह {pct}% बार फ़ायदेमंद रही",
        "unreliable": "ℹ️ यहाँ अनुमान भरोसेमंद नहीं; सिर्फ़ आज के भाव की तुलना की",
        "hold_suppressed": "ℹ️ {mandi} में {days} दिन रुकने पर ₹{extra}/क्विंटल ज़्यादा मिल सकते हैं, पर पिछले "
                           "सीज़न में ऐसी सलाह {total} में से सिर्फ़ {won} बार फ़ायदेमंद रही. इसलिए आज ही बेचें.",
        "note": "ℹ️ {note}",
        "footer": "🗓 {date} के भाव के अनुसार · भरोसा: {confidence}",
        "correct": "सही है? 1) हाँ 2) नहीं",
        "village_unclear": "गाँव ठीक से समझ नहीं आया. कौन सा?",
        "other": "कोई और",
        "not_covered": "माफ़ कीजिए, यह गाँव अभी हमारी सूची में नहीं है.",
        "resend": "ठीक है. कृपया दोबारा भेजें: फसल, मात्रा और गाँव.\nजैसे: {example}",
        "help": "नमस्ते! यह SellSmart है. फसल, मात्रा और गाँव भेजें; "
                "कहाँ और कब बेचें यह हम बताएँगे.\nजैसे: {example}\nफसलें: {crops}",
        "ask_crop": "कौन सी फसल? अभी सिर्फ़ {crops} उपलब्ध हैं.",
        "ask_quantity": "कितना माल है? जैसे: 20 क्विंटल या 40 बोरी",
        "ask_village": "गाँव कौन सा है?",
        "pick_number": "कृपया दिए गए विकल्पों में से नंबर भेजें.",
        "error": "माफ़ कीजिए, अभी सलाह नहीं दे पाए. थोड़ी देर बाद फिर कोशिश करें.",
        "cash": "पैसे कब तक चाहिए?\n1) 2–3 दिन में\n2) इस हफ़्ते\n3) कोई जल्दी नहीं",
        "example": "20 बोरी प्याज {village}",
    },
    "en": {
        "hold_head": "🟢 *Wait {days} {day_word} → {mandi}*",
        "hold_money": "💰 About ₹{net}/quintal in hand (₹{low}–₹{high})",
        "sell_head": "🔴 *Sell today → {mandi}*",
        "sell_money": "💰 About ₹{net}/quintal in hand",
        "gain": "📈 ₹{gain} more than the nearest mandi today",
        "nearest_best": "📈 The nearest mandi is the best one",
        "break_even": "⚠️ Go only if the price is above ₹{breakeven}. Check before you leave",
        "tip": "📦 Storage: {tip}",
        "success": "📊 Last season our advice to wait paid off {pct}% of the time",
        "unreliable": "ℹ️ The forecast isn't reliable here; only today's prices were compared",
        "hold_suppressed": "ℹ️ Waiting {days} days at {mandi} might add ₹{extra}/quintal, but last season this "
                           "advice won {won} of {total} times, so sell today.",
        "note": "ℹ️ {note}",
        "footer": "🗓 Prices as of {date} · Confidence: {confidence}",
        "correct": "Correct? 1) yes 2) no",
        "village_unclear": "I couldn't match the village. Which one?",
        "other": "other",
        "not_covered": "Sorry, this village isn't covered yet.",
        "resend": "OK. Please send it again: crop, quantity and village.\nExample: {example}",
        "help": "Hi! This is SellSmart. Send your crop, quantity and village and we'll tell "
                "you where and when to sell.\nExample: {example}\nCrops: {crops}",
        "ask_crop": "Which crop? We currently cover only {crops}.",
        "ask_quantity": "How much do you have? e.g. 20 quintal or 40 bags",
        "ask_village": "Which village?",
        "pick_number": "Please reply with one of the numbers.",
        "error": "Sorry, we couldn't work out the advice just now. Please try again in a while.",
        "cash": "By when do you need the money?\n1) In 2–3 days\n2) This week\n3) No hurry",
        "example": "20 bags onion {village}",
    },
}

FRESHNESS = {
    "tomato": {
        "mr": "टोमॅटो कधी तोडले?\n1) आज\n2) 1–2 दिवसांपूर्वी\n3) 3 किंवा जास्त दिवसांपूर्वी",
        "hi": "टमाटर कब तोड़े गए?\n1) आज\n2) 1–2 दिन पहले\n3) 3 या ज़्यादा दिन पहले",
        "en": "When was the tomato picked?\n1) today\n2) 1–2 days ago\n3) 3 or more days ago",
    },
    "onion": {
        "mr": "कांदा वाळवलेला आहे आणि हवेशीर जागी साठवला आहे का?\n1) हो\n2) नाही",
        "hi": "क्या प्याज सुखाया हुआ है और हवादार जगह पर रखा है?\n1) हाँ\n2) नहीं",
        "en": "Is the onion dried (cured) and kept in ventilated storage?\n1) yes\n2) no",
    },
    "soybean": {
        "mr": "सोयाबीन पूर्ण वाळलेले आहे का?\n1) हो\n2) नाही",
        "hi": "क्या सोयाबीन का दाना पूरी तरह सूखा है?\n1) हाँ\n2) नहीं",
        "en": "Is the soybean grain fully dried?\n1) yes\n2) no",
    },
}

VOICE_FAILED = ("आवाज नीट समजला नाही. कृपया पुन्हा बोला किंवा टाइप करून पाठवा.\n"
                "आवाज़ ठीक से समझ नहीं आई. कृपया दोबारा बोलें या टाइप करके भेजें.")
EXAMPLE_DATA = "🧪 Example data: decision engine not connected"


def _lang(lang: str) -> str:
    return lang if lang in LANGS else "mr"


# ---------- formatting helpers --------------------------------------------

def money(value) -> str:
    """Whole rupees with Indian digit grouping: 1844 -> '1,844', 123456 -> '1,23,456'."""
    number = round(value)
    sign, digits = ("-" if number < 0 else ""), str(abs(number))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        digits = ",".join(([head] if head else []) + groups + [tail])
    return sign + digits


def qty(value) -> str:
    """10.0 -> '10', 1.4 -> '1.4', 0.25 -> '0.25'."""
    return f"{round(float(value), 2):g}"


def long_date(iso: str | None, lang: str) -> str:
    try:
        d = date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{d.day} {MONTHS[_lang(lang)][d.month - 1]} {d.year}"


def mandi_name(name: str, lang: str) -> str:
    """'Junnar(Narayangaon)' -> 'जुन्नर (नारायणगाव)' for mr/hi; unknown parts stay as they are."""
    if _lang(lang) == "en" or not name:
        return name
    whole = MANDI_DEVANAGARI.get(name.strip().lower())
    if whole:
        return whole
    parts = [p.strip() for p in re.split(r"[()]", name) if p.strip()]
    shown = [MANDI_DEVANAGARI.get(p.lower(), p) for p in parts]
    if not shown:
        return name
    return shown[0] + (f" ({', '.join(shown[1:])})" if len(shown) > 1 else "")


def village_name(village: dict, lang: str) -> str:
    return {"mr": village["name_mr"], "hi": village["name_hi"]}.get(_lang(lang), village["village"])


def crop_list(lang: str) -> str:
    lang = _lang(lang)
    names = [CROP[c][lang] for c in ("onion", "tomato", "soybean")]
    joiner = {"mr": " आणि ", "hi": " और ", "en": " and "}[lang]
    return ", ".join(names[:-1]) + joiner + names[-1]


def _example(lang: str, example_village: dict | None) -> str:
    lang = _lang(lang)
    village = village_name(example_village, lang) if example_village else ""
    return _T[lang]["example"].format(village=village).strip()


# ---------- the advice ----------------------------------------------------

def advice_message(advice: dict, lang: str = "mr", tip: str | None = None,
                   example_data: bool = False) -> str:
    lang = _lang(lang)
    t = _T[lang]
    hold = advice.get("action") == "hold"
    mandi = mandi_name(advice.get("mandi", ""), lang)
    net = money(advice["net_per_qtl"])

    lines = []
    if hold:
        days = advice["days"]
        lines.append(t["hold_head"].format(days=days, mandi=mandi,
                                           day_word="day" if days == 1 else "days"))
        lines.append(t["hold_money"].format(net=net, low=money(advice["net_low"]),
                                            high=money(advice["net_high"])))
    else:
        lines.append(t["sell_head"].format(mandi=mandi))
        lines.append(t["sell_money"].format(net=net))

    gain = advice.get("gain_vs_baseline")
    if gain is not None and round(gain) > 0:
        lines.append(t["gain"].format(gain=money(gain)))
    elif gain is not None and round(gain) == 0 and not hold:
        lines.append(t["nearest_best"])

    if hold:
        if advice.get("break_even_price") is not None:
            lines.append(t["break_even"].format(breakeven=money(advice["break_even_price"])))
        if tip:
            lines.append(t["tip"].format(tip=tip))
        if advice.get("hold_success_rate") is not None:
            lines.append(t["success"].format(pct=round(advice["hold_success_rate"] * 100)))

    confidence = advice.get("confidence")
    if confidence == "low" and advice.get("uses_baseline"):
        lines.append(t["unreliable"])
    for note in advice.get("notes") or []:
        line = note_line(note, lang)
        if line not in lines:
            lines.append(line)
    lines.append(t["footer"].format(
        date=long_date(advice.get("prices_as_of"), lang),
        confidence=CONFIDENCE.get(confidence, {}).get(lang, confidence or "–")))
    if example_data:
        lines.append(EXAMPLE_DATA)
    return "\n".join(lines)


# The engine's notes (ml/engine/api.py), rendered through a fixed template per language. The numbers
# are copied from the note text as they are; a note we don't recognise is shown as the engine wrote it.
_HOLD_SUPPRESSED = re.compile(r"Hold suppressed: (?P<days>\d+) days at (?P<mandi>.+?), expected extra "
                              r"Rs (?P<extra>-?\d+) per qtl; won (?P<won>\d+) of (?P<total>\d+)\.")
_UNRELIABLE_NOTE = "forecast not reliable here; compared today's prices only"


def note_line(note: str, lang: str = "mr") -> str:
    t = _T[_lang(lang)]
    m = _HOLD_SUPPRESSED.fullmatch(note.strip())
    if m:
        return t["hold_suppressed"].format(**{**m.groupdict(), "mandi": mandi_name(m["mandi"], lang)})
    if note.strip() == _UNRELIABLE_NOTE:
        return t["unreliable"]
    return t["note"].format(note=note)


# ---------- the conversation ----------------------------------------------

def echo(crop: str, qty_value: float, qty_unit: str | None, quantity_qtl: float, lang: str) -> str:
    """'20 पोती कांदा (≈ 10 क्विंटल)': what we understood, with the converted quantity."""
    lang = _lang(lang)
    quintal, crop_word = UNIT["quintal"][lang], CROP[crop][lang]
    if qty_unit in (None, "quintal"):
        return f"{qty(quantity_qtl)} {quintal} {crop_word}"
    unit = UNIT[qty_unit][lang]
    if lang == "en" and qty_value == 1:
        unit = unit.removesuffix("s")
    sign = "≈" if qty_unit in ("bag", "crate") else "="
    return f"{qty(qty_value)} {unit} {crop_word} ({sign} {qty(quantity_qtl)} {quintal})"


def confirm(echo_text: str, village: dict, lang: str) -> str:
    lang = _lang(lang)
    return f"{echo_text}, {village_name(village, lang)}. {_T[lang]['correct']}"


def village_options(echo_text: str, candidates: list[dict], lang: str) -> str:
    lang = _lang(lang)
    t = _T[lang]
    lines = [f"{echo_text}. {t['village_unclear']}" if echo_text else t["village_unclear"]]
    lines += [f"{i}) {village_name(v, lang)}" for i, v in enumerate(candidates, 1)]
    lines.append(f"{len(candidates) + 1}) {t['other']}")
    return "\n".join(lines)


def ask_missing(missing: list[str], lang: str) -> str:
    lang = _lang(lang)
    t = _T[lang]
    return "\n".join(t["ask_" + what].format(crops=crop_list(lang)) for what in missing)


def freshness_question(crop: str, lang: str) -> str:
    return FRESHNESS[crop][_lang(lang)]


def cash_question(lang: str) -> str:
    return _T[_lang(lang)]["cash"]


def pick_number(question: str, lang: str) -> str:
    return f"{_T[_lang(lang)]['pick_number']}\n{question}"


def help_message(lang: str, example_village: dict | None = None) -> str:
    lang = _lang(lang)
    return _T[lang]["help"].format(example=_example(lang, example_village), crops=crop_list(lang))


def resend(lang: str, example_village: dict | None = None) -> str:
    lang = _lang(lang)
    return _T[lang]["resend"].format(example=_example(lang, example_village))


def not_covered(lang: str) -> str:
    return _T[_lang(lang)]["not_covered"]


def error(lang: str) -> str:
    return _T[_lang(lang)]["error"]


# ---------- the guided flow (greeting or an unparsed message) ---------------

LANG_MENU = ("भाषा निवडा / भाषा चुनें / Choose language:\n1) मराठी\n2) हिंदी\n3) English\n"
             "(0 = पुन्हा सुरू / फिर से / restart)")
_G = {
    "mr": {
        "crop_q": "कोणते पीक?",
        "qty_q": "किती माल आहे? उदा. 20 क्विंटल, 500 किलो किंवा 40 पोती",
        "qty_bad": "माल शून्यापेक्षा जास्त हवा.",
        "unit_bad": "हे माप या पिकासाठी चालत नाही. क्विंटल, किलो किंवा पोती वापरा.",
        "unit_q": "{value} किलो की क्विंटल?\n1) किलो\n2) क्विंटल",
        "village_q": "गाव कोणते? क्रमांक पाठवा किंवा गावाचे नाव टाइप करा:",
        "village_other": "दुसरे गाव (नाव टाइप करा)",
        "village_type": "गावाचे नाव टाइप करा:",
        "village_unknown": "हे गाव आमच्या यादीत नाही. यादीतील सर्वात जवळचे गाव निवडा:",
        "summary": "तपासा:\nपीक: {crop}\nमाल: {qty}\nगाव: {village}{fresh}{cash}\n1) बरोबर, सल्ला द्या\n2) बदला",
        "fresh": "ताजेपणा", "cash": "पैसे",
        "used_same": "ℹ️ ताजेपणा आणि पैशाची उत्तरे विचारात घेतली; त्यांनी सल्ला बदलला नाही.",
        "used_changed": "ℹ️ ताजेपणा आणि पैशाच्या उत्तरांमुळे सल्ला बदलला (थांबण्याची मर्यादा {limit} दिवस{cash}).",
        "used_cash": ", पैसे {days} दिवसांत",
    },
    "hi": {
        "crop_q": "कौन सी फसल?",
        "qty_q": "कितना माल है? जैसे: 20 क्विंटल, 500 किलो या 40 बोरी",
        "qty_bad": "माल शून्य से ज़्यादा होना चाहिए.",
        "unit_bad": "यह माप इस फसल के लिए नहीं चलता. क्विंटल, किलो या बोरी लिखें.",
        "unit_q": "{value} किलो या क्विंटल?\n1) किलो\n2) क्विंटल",
        "village_q": "गाँव कौन सा? नंबर भेजें या गाँव का नाम लिखें:",
        "village_other": "दूसरा गाँव (नाम लिखें)",
        "village_type": "गाँव का नाम लिखें:",
        "village_unknown": "यह गाँव हमारी सूची में नहीं है. सूची में से सबसे पास का गाँव चुनें:",
        "summary": "जाँचें:\nफसल: {crop}\nमाल: {qty}\nगाँव: {village}{fresh}{cash}\n1) सही है, सलाह दें\n2) बदलें",
        "fresh": "ताज़गी", "cash": "पैसे",
        "used_same": "ℹ️ ताज़गी और पैसे के जवाब देखे गए; उनसे सलाह नहीं बदली.",
        "used_changed": "ℹ️ ताज़गी और पैसे के जवाबों से सलाह बदली (रुकने की सीमा {limit} दिन{cash}).",
        "used_cash": ", पैसे {days} दिन में",
    },
    "en": {
        "crop_q": "Which crop?",
        "qty_q": "How much do you have? e.g. 20 quintal, 500 kg or 40 bags",
        "qty_bad": "The quantity must be more than zero.",
        "unit_bad": "That unit doesn't work for this crop. Use quintal, kg or bags.",
        "unit_q": "{value} kg or quintal?\n1) kg\n2) quintal",
        "village_q": "Which village? Send a number or type your village:",
        "village_other": "another village (type its name)",
        "village_type": "Type your village name:",
        "village_unknown": "That village isn't in our list. Pick the nearest village from the list:",
        "summary": "Please check:\nCrop: {crop}\nQuantity: {qty}\nVillage: {village}{fresh}{cash}\n1) Correct, give advice\n2) Edit",
        "fresh": "Freshness", "cash": "Cash needed",
        "used_same": "ℹ️ Your freshness and cash answers were checked; they did not change this advice.",
        "used_changed": "ℹ️ Your freshness and cash answers changed this advice (hold limit {limit} days{cash}).",
        "used_cash": ", cash needed in {days} days",
    },
}


def guided(key: str, lang: str, **values) -> str:
    return _G[_lang(lang)][key].format(**values)


def crop_menu(lang: str) -> str:
    lang = _lang(lang)
    return _G[lang]["crop_q"] + "".join(f"\n{i}) {CROP[c][lang]}" for i, c in
                                        enumerate(("onion", "tomato", "soybean"), 1))


def village_menu(villages: list[dict], lang: str, head: str = "village_q") -> str:
    lang = _lang(lang)
    lines = [_G[lang][head]] + [f"{i}) {village_name(v, lang)}" for i, v in enumerate(villages, 1)]
    return "\n".join(lines + [f"{len(villages) + 1}) {_G[lang]['village_other']}"])


def _option_text(question: str, number: int) -> str:
    """'2) 1–2 दिवसांपूर्वी' -> '1–2 दिवसांपूर्वी' from a numbered question."""
    line = next(l for l in question.splitlines() if l.startswith(f"{number})"))
    return line.split(")", 1)[1].strip()


def summary(crop: str, qty_value, qty_unit, quantity_qtl, village: dict, lot_condition,
            cash_days, lang: str) -> str:
    lang = _lang(lang)
    g = _G[lang]
    fresh = cash = ""
    if crop in ("onion", "tomato"):
        number = (lot_condition + 1) if crop == "tomato" else (1 if lot_condition else 2)
        fresh = f"\n{g['fresh']}: {_option_text(FRESHNESS[crop][lang], number)}"
    number = {3: 1, 7: 2, None: 3}.get(cash_days)
    cash = f"\n{g['cash']}: " + (_option_text(_T[lang]["cash"], number) if number else str(cash_days))
    amount = f"{qty(qty_value)} {UNIT[qty_unit or 'quintal'][lang]}"
    if qty_unit not in (None, "quintal"):
        amount += f" (= {qty(quantity_qtl)} {UNIT['quintal'][lang]})"
    return g["summary"].format(crop=CROP[crop][lang], qty=amount, village=village_name(village, lang),
                               fresh=fresh, cash=cash)


# ---------- offer check (after advice) --------------------------------------

_OFFER = {
    "mr": {
        "prompt": "💬 व्यापाऱ्याकडून भाव मिळाला? पाठवा, उदा. 23 प्रति किलो किंवा 2300 प्रति क्विंटल",
        "head": "💬 तुम्ही सांगितलेल्या भावावर आधारित: {mandi} येथे ₹{offer}/क्विंटल",
        "net": "हातात: ₹{net}/क्विंटल · जवळचा बाजार ({base_mandi}): ₹{base}/क्विंटल",
        "diff": "पूर्ण मालावर ({qty} क्विंटल) फरक: {diff}",
        "better": "✅ या भावाला {mandi} अजूनही जवळच्या बाजारापेक्षा चांगला आहे.",
        "worse": "❌ या भावाला जवळचा बाजार ({base_mandi}) चांगला आहे.",
    },
    "hi": {
        "prompt": "💬 व्यापारी से भाव मिला? भेजें, जैसे 23 प्रति किलो या 2300 प्रति क्विंटल",
        "head": "💬 आपके बताए भाव पर आधारित: {mandi} में ₹{offer}/क्विंटल",
        "net": "हाथ में: ₹{net}/क्विंटल · पास की मंडी ({base_mandi}): ₹{base}/क्विंटल",
        "diff": "पूरे माल पर ({qty} क्विंटल) फ़र्क: {diff}",
        "better": "✅ इस भाव पर {mandi} अब भी पास की मंडी से बेहतर है.",
        "worse": "❌ इस भाव पर पास की मंडी ({base_mandi}) बेहतर है.",
    },
    "en": {
        "prompt": "💬 Got a price offer? Send it, for example 23 per kg or 2300 per quintal.",
        "head": "💬 Based on your quoted price: ₹{offer}/quintal at {mandi}",
        "net": "In hand: ₹{net}/quintal · nearest mandi ({base_mandi}): ₹{base}/quintal",
        "diff": "Difference on the whole lot ({qty} quintal): {diff}",
        "better": "✅ At this price {mandi} still beats the nearest mandi.",
        "worse": "❌ At this price the nearest mandi ({base_mandi}) is better.",
    },
}


def offer_prompt(lang: str) -> str:
    return _OFFER[_lang(lang)]["prompt"]


def offer_check(mandi: str, offer_per_qtl, net, base_mandi: str, base_net, quantity_qtl, lang: str) -> str:
    lang = _lang(lang)
    o = _OFFER[lang]
    diff = round((net - base_net) * quantity_qtl)
    signed = ("+" if diff >= 0 else "−") + "₹" + money(abs(diff))
    names = {"mandi": mandi_name(mandi, lang), "base_mandi": mandi_name(base_mandi, lang)}
    return "\n".join([o["head"].format(offer=money(offer_per_qtl), **names),
                      o["net"].format(net=money(net), base=money(base_net), **names),
                      o["diff"].format(qty=qty(quantity_qtl), diff=signed),
                      o["better" if net > base_net else "worse"].format(**names)])


def answers_used(changed: bool, hold_limit_days, cash_days, lang: str) -> str:
    g = _G[_lang(lang)]
    if not changed:
        return g["used_same"]
    return g["used_changed"].format(limit=hold_limit_days,
                                    cash=g["used_cash"].format(days=cash_days) if cash_days is not None else "")


def _selftest():
    from . import data_loader, tips

    assert money(1844) == "1,844" and money(950) == "950" and money(123456) == "1,23,456"
    assert money(1234567) == "12,34,567" and money(-40) == "-40" and money(1843.6) == "1,844"
    assert qty(10.0) == "10" and qty(1.4) == "1.4" and qty(0.25) == "0.25"
    assert long_date("2026-08-31", "mr") == "31 ऑगस्ट 2026"
    assert long_date("2026-08-31", "hi") == "31 अगस्त 2026"
    assert mandi_name("Pimpalgaon", "mr") == "पिंपळगाव" and mandi_name("Pimpalgaon", "en") == "Pimpalgaon"
    assert mandi_name("Junnar(Narayangaon)", "hi") == "जुन्नर (नारायणगाव)"
    assert mandi_name("Somewhere New", "mr") == "Somewhere New"
    assert all(set(t) == set(_T["mr"]) for t in _T.values()), "a template is missing in one language"

    hold = data_loader.fake("advise.json")
    text = advice_message(hold, "mr", tips.storage_tip("onion", "mr"))
    assert text.splitlines() == [
        "🟢 *14 दिवस थांबा → पिंपळगाव*",
        "💰 हातात अंदाजे ₹1,844/क्विंटल (₹1,652–₹2,035)",
        "📈 आज जवळच्या बाजारापेक्षा ₹184 जास्त",
        "⚠️ भाव ₹1,850 च्या वर असेल तरच जा. निघण्यापूर्वी खात्री करा",
        "📦 साठवण: " + tips.storage_tip("onion", "mr"),
        "🗓 31 ऑगस्ट 2026 च्या भावांनुसार · खात्री: मध्यम",
    ], text

    sell = dict(hold, action="sell_now", days=0, mandi="Lasalgaon", net_per_qtl=1660,
                gain_vs_baseline=0, break_even_price=None, confidence="low", uses_baseline=True,
                hold_success_rate=None)
    assert advice_message(sell, "hi").splitlines() == [
        "🔴 *आज ही बेचें → लासलगाव*",
        "💰 हाथ में लगभग ₹1,660/क्विंटल",
        "📈 पास की मंडी ही सबसे अच्छी है",
        "ℹ️ यहाँ अनुमान भरोसेमंद नहीं; सिर्फ़ आज के भाव की तुलना की",
        "🗓 31 अगस्त 2026 के भाव के अनुसार · भरोसा: कम",
    ]
    rated = advice_message(dict(hold, hold_success_rate=0.64, days=1), "en", "tip")
    assert "paid off 64% of the time" in rated and "*Wait 1 day → Pimpalgaon*" in rated

    niphad = {"village": "Niphad", "name_mr": "निफाड", "name_hi": "निफाड"}
    assert confirm(echo("onion", 20, "bag", 10, "mr"), niphad, "mr") == \
        "20 पोती कांदा (≈ 10 क्विंटल), निफाड. बरोबर? 1) हो 2) नाही"
    assert echo("onion", 10, None, 10, "mr") == "10 क्विंटल कांदा"
    assert echo("tomato", 2, "ton", 20, "en") == "2 tonne tomato (= 20 quintal)"
    assert village_options("10 क्विंटल कांदा", [niphad], "mr").splitlines()[-2:] == ["1) निफाड", "2) इतर"]
    assert crop_list("mr") == "कांदा, टोमॅटो आणि सोयाबीन"
    assert "20 पोती कांदा निफाड" in help_message("mr", niphad)
    for lang in LANGS:
        for crop in CROP:
            assert freshness_question(crop, lang).count("\n") >= 2
        assert ask_missing(["crop", "quantity", "village"], lang).count("\n") == 2
    print("replies ok")
    print(text)


if __name__ == "__main__":
    _selftest()
