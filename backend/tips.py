"""Storage tip per crop and language. Shown only with hold advice.

General guidance, not from a model. Check against an agricultural source before the pitch.
"""

TIPS = {
    "onion": {
        "en": "Keep in a dry, well-ventilated place off the ground; don't pile deep; "
              "remove rotting or sprouting bulbs.",
        "mr": "कोरड्या, हवेशीर जागी जमिनीपासून उंचावर ठेवा; उंच ढीग लावू नका; "
              "सडलेले किंवा कोंब आलेले कांदे काढून टाका.",
        "hi": "सूखी, हवादार जगह पर ज़मीन से ऊपर रखें; ऊँचा ढेर न लगाएँ; "
              "सड़े या अंकुरित प्याज़ निकाल दें.",
    },
    "tomato": {
        "en": "Keep in shade, in crates not sacks; don't stack deep; move it in the cool hours.",
        "mr": "सावलीत, पोत्यांऐवजी क्रेटमध्ये ठेवा; जास्त थर लावू नका; "
              "वाहतूक थंड वेळेत करा.",
        "hi": "छाया में, बोरियों के बजाय क्रेट में रखें; ज़्यादा परतें न लगाएँ; "
              "ढुलाई ठंडे समय में करें.",
    },
    "soybean": {
        "en": "Store only fully dried grain, in clean dry bags, off the floor and away from walls.",
        "mr": "पूर्ण वाळलेले धान्यच साठवा; स्वच्छ, कोरड्या पोत्यांत, "
              "जमिनीपासून उंचावर आणि भिंतीपासून दूर ठेवा.",
        "hi": "पूरी तरह सूखा दाना ही रखें; साफ़, सूखी बोरियों में, "
              "फ़र्श से ऊपर और दीवारों से दूर रखें.",
    },
}


def storage_tip(crop: str, lang: str = "mr") -> str | None:
    by_lang = TIPS.get(crop)
    if not by_lang:
        return None
    return by_lang.get(lang, by_lang["en"])


def _selftest():
    for crop, by_lang in TIPS.items():
        assert set(by_lang) == {"en", "mr", "hi"}, crop
        assert all(text.strip() for text in by_lang.values()), crop
    assert storage_tip("onion", "mr").startswith("कोरड्या")
    assert storage_tip("onion", "xx") == TIPS["onion"]["en"]
    assert storage_tip("wheat") is None
    print("tips ok")


if __name__ == "__main__":
    _selftest()
