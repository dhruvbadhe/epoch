"""Freshness: a guidance-based lookup, not a model.

The estimated selling window is the hold limit for the crop and the freshness answer already collected:
the same value the engine uses (ml/engine/api.py _hold_limit on config.yaml hold_limit_days). The reasons
are fixed sentences; the references are further reading only, with no figures taken from them. Added to
the /advise response in the backend response layer; never passed into the engine.
"""
from __future__ import annotations

from . import engine_api

BASIS = "Based on general post-harvest guidance; local accuracy not evaluated"
REFERENCES = ["NHRDF post-harvest guidance", "ICAR-DOGR onion storage", "UC Davis Postharvest tomato facts",
              "UMN Extension soybean storage", "FAO post-harvest management"]

# (crop, answer) -> sentence per language. Answers: tomato 0/1/2 (picked today / 1-2 days / 3+ days),
# onion and soybean True/False (cured and ventilated / fully dried), None = not asked.
_REASON = {
    ("tomato", 0): {"en": "Picked today: ripe tomatoes soften quickly at room temperature, so the window is short.",
                    "mr": "आज तोडलेले: पिकलेले टोमॅटो खोलीच्या तापमानात लवकर मऊ होतात, म्हणून कालावधी कमी आहे.",
                    "hi": "आज तोड़े गए: पके टमाटर कमरे के तापमान पर जल्दी नरम होते हैं, इसलिए समय कम है."},
    ("tomato", 1): {"en": "Picked 1–2 days ago: part of the shelf life is already used, so the window is shorter.",
                    "mr": "1–2 दिवसांपूर्वी तोडलेले: टिकण्याचा काही काळ आधीच गेला आहे, म्हणून कालावधी अजून कमी आहे.",
                    "hi": "1–2 दिन पहले तोड़े गए: टिकने का कुछ समय पहले ही बीत चुका है, इसलिए समय और कम है."},
    ("tomato", 2): {"en": "Picked 3 or more days ago: sell as soon as possible.",
                    "mr": "3 किंवा जास्त दिवसांपूर्वी तोडलेले: शक्य तितक्या लवकर विका.",
                    "hi": "3 या ज़्यादा दिन पहले तोड़े गए: जितनी जल्दी हो सके बेचें."},
    ("onion", True): {"en": "Cured onion in a ventilated store keeps much longer than uncured onion.",
                      "mr": "वाळवलेला कांदा हवेशीर चाळीत न वाळवलेल्या कांद्यापेक्षा खूप जास्त टिकतो.",
                      "hi": "सुखाया हुआ प्याज हवादार गोदाम में बिना सुखाए प्याज से कहीं ज़्यादा टिकता है."},
    ("onion", False): {"en": "Uncured or poorly ventilated onion rots and sprouts sooner, so the window is short.",
                       "mr": "न वाळवलेला किंवा हवा न लागणारा कांदा लवकर सडतो व कोंब येतात, म्हणून कालावधी कमी आहे.",
                       "hi": "बिना सुखाया या बिना हवा का प्याज जल्दी सड़ता और अंकुरित होता है, इसलिए समय कम है."},
    ("soybean", True): {"en": "Fully dried grain stores well when kept dry and off the floor.",
                        "mr": "पूर्ण वाळलेले दाणे कोरड्या जागी, जमिनीपासून उंच ठेवल्यास चांगले टिकतात.",
                        "hi": "पूरी तरह सूखा दाना सूखी जगह, ज़मीन से ऊपर रखने पर अच्छा टिकता है."},
    ("soybean", False): {"en": "Grain that is not fully dried can heat up and grow mould, so the window is short.",
                         "mr": "पूर्ण न वाळलेले दाणे गरम होऊन बुरशी येऊ शकते, म्हणून कालावधी कमी आहे.",
                         "hi": "पूरा न सूखा दाना गरम होकर फफूंद पकड़ सकता है, इसलिए समय कम है."},
}
_NOT_ASKED = {"en": "Freshness was not asked, so this is the crop's default window.",
              "mr": "ताजेपणा विचारला नाही, म्हणून हा पिकाचा नेहमीचा कालावधी आहे.",
              "hi": "ताज़गी नहीं पूछी गई, इसलिए यह फसल का सामान्य समय है."}
_WINDOW = {"en": "Up to {n} days: the hold limit SahiDaam uses for this answer.",
           "mr": "जास्तीत जास्त {n} दिवस: या उत्तरासाठी सही दाम वापरत असलेली मर्यादा.",
           "hi": "ज़्यादा से ज़्यादा {n} दिन: इस जवाब के लिए सही दाम की सीमा."}
_MISSING = {
    "onion": {"en": ["harvest season", "variety"], "mr": ["काढणीचा हंगाम", "जात"], "hi": ["कटाई का मौसम", "किस्म"]},
    "tomato": {"en": ["ripeness"], "mr": ["पिकण्याची अवस्था"], "hi": ["पकने की अवस्था"]},
    "soybean": {"en": ["grain moisture"], "mr": ["दाण्यातील ओलावा"], "hi": ["दाने की नमी"]},
}


def estimate(crop: str, lot_condition=None, lang: str = "en") -> dict:
    lang = lang if lang in ("en", "mr", "hi") else "en"
    engine = engine_api._load_module()
    window = engine._hold_limit(crop, lot_condition, engine._config(None))
    first = _NOT_ASKED if lot_condition is None else _REASON[(crop, lot_condition)]
    return {"estimated_window_days": window, "answer": lot_condition, "basis": BASIS,
            "reasons": [first[lang], _WINDOW[lang].format(n=window)],
            "missing": _MISSING[crop][lang], "references": REFERENCES}
