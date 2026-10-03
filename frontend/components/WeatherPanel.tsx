"use client";

import {
  CloudSun,
  Droplets,
  Leaf,
  MapPin,
  RefreshCw,
  Thermometer,
  WifiOff,
} from "lucide-react";
import { getWeather } from "@/lib/api";
import { useResource } from "@/lib/useResource";
import { dateLabel } from "@/lib/format";
import type { Crop, Lang, LotCondition } from "@/lib/types";
import styles from "./WeatherPanel.module.css";

const copy = {
  en: {
    eyebrow: "Current local conditions",
    title: "Local weather & storage",
    temperature: "Air temperature",
    humidity: "Relative humidity",
    loading: "Checking village weather…",
    unavailable: "Weather unavailable",
    offline:
      "Your advice is ready. Local weather could not be loaded; follow the crop guidance below and check conditions in your store.",
    refresh: "Refresh weather",
    updated: "Weather updated",
    missing: "Not enough data",
    check: "Your lot’s storage check",
    unanswered: "Freshness not answered",
    boundary:
      "Outdoor weather is a guide; conditions inside your store may differ. It does not change the selling window, spoilage assumptions or recommendation.",
    history: "Advice uses historical prices as of",
    provider: "Weather model data by Open-Meteo",
    more: "How to use this guidance",
    note: "This is crop-specific storage guidance, not a measured rot percentage or a guarantee of shelf life.",
    crops: { onion: "Onion", tomato: "Tomato", soybean: "Soybean" },
  },
  mr: {
    eyebrow: "सध्याचे स्थानिक हवामान",
    title: "स्थानिक हवामान आणि साठवण",
    temperature: "हवेचे तापमान",
    humidity: "सापेक्ष आर्द्रता",
    loading: "गावाचे हवामान तपासत आहोत…",
    unavailable: "हवामान उपलब्ध नाही",
    offline:
      "तुमचा सल्ला तयार आहे. हवामान मिळाले नाही; खालील मार्गदर्शन वापरा आणि साठवणीतील परिस्थिती तपासा.",
    refresh: "हवामान पुन्हा तपासा",
    updated: "हवामानाची वेळ",
    missing: "पुरेसा डेटा नाही",
    check: "तुमच्या मालाची साठवण तपासा",
    unanswered: "ताजेपणाचे उत्तर दिले नाही",
    boundary:
      "बाहेरील हवामान मार्गदर्शक आहे; साठवणीतील परिस्थिती वेगळी असू शकते. विक्री कालावधी, नासाडीची गृहीतके किंवा सल्ला बदलत नाही.",
    history: "सल्ल्यासाठी वापरलेल्या ऐतिहासिक किमतींची तारीख",
    provider: "Open-Meteo चे हवामान मॉडेल डेटा",
    more: "हे मार्गदर्शन कसे वापरावे",
    note: "हे पिकानुसार साठवण मार्गदर्शन आहे; मोजलेली नासाडीची टक्केवारी किंवा टिकण्याची हमी नाही.",
    crops: { onion: "कांदा", tomato: "टोमॅटो", soybean: "सोयाबीन" },
  },
  hi: {
    eyebrow: "वर्तमान स्थानीय मौसम",
    title: "स्थानीय मौसम और भंडारण",
    temperature: "हवा का तापमान",
    humidity: "सापेक्ष आर्द्रता",
    loading: "गांव का मौसम देख रहे हैं…",
    unavailable: "मौसम उपलब्ध नहीं",
    offline:
      "आपकी सलाह तैयार है। मौसम नहीं मिल पाया; नीचे का मार्गदर्शन अपनाएं और भंडारण की स्थिति जांचें।",
    refresh: "मौसम फिर देखें",
    updated: "मौसम का समय",
    missing: "पर्याप्त डेटा नहीं",
    check: "आपके माल की भंडारण जांच",
    unanswered: "ताज़गी का उत्तर नहीं दिया",
    boundary:
      "बाहर का मौसम एक मार्गदर्शक है; भंडारण के अंदर स्थिति अलग हो सकती है। बिक्री अवधि, खराब होने की धारणाएं या सलाह नहीं बदलती।",
    history: "सलाह में इस्तेमाल ऐतिहासिक कीमतों की तारीख",
    provider: "Open-Meteo का मौसम मॉडल डेटा",
    more: "इस मार्गदर्शन का उपयोग",
    note: "यह फसल के अनुसार भंडारण मार्गदर्शन है; मापी गई सड़न प्रतिशत या टिकने की गारंटी नहीं।",
    crops: { onion: "प्याज", tomato: "टमाटर", soybean: "सोयाबीन" },
  },
};

const guidance = {
  en: {
    onion:
      "Check airflow and keep bulbs dry. Outdoor humidity does not tell you whether moisture is building up inside the onion store.",
    tomato:
      "Keep crates shaded, avoid bruising and inspect for soft fruit. Prevent condensation; humidity alone cannot tell you how much fruit will rot.",
    soybean:
      "Keep grain dry and off the floor. Check grain moisture and condensation inside the store before planning to hold it.",
    onionReady:
      "Cured and ventilated: maintain airflow and separate bulbs showing decay.",
    onionWet:
      "Not cured: check drying and ventilation before storing. Separate wet or damaged bulbs.",
    tomatoToday:
      "Picked today: check ripeness and packing conditions before holding.",
    tomatoRecent:
      "Picked 1–2 days ago: inspect ripeness and firmness before dispatch.",
    tomatoOlder:
      "Picked 3+ days ago: prioritise inspection and separate soft or damaged fruit.",
    soybeanReady:
      "Fully dried: keep moisture out and inspect the grain regularly.",
    soybeanWet:
      "Not fully dried: check drying and grain moisture before storage.",
    unknown:
      "Answer the freshness question above to make this storage check more specific.",
  },
  mr: {
    onion:
      "हवा खेळती ठेवा आणि कांदा कोरडा ठेवा. बाहेरील आर्द्रतेवरून चाळीत ओलावा साचतो आहे का हे समजत नाही.",
    tomato:
      "क्रेट सावलीत ठेवा, इजा टाळा आणि मऊ फळे तपासा. पाणी साचू देऊ नका; फक्त आर्द्रतेवरून नासाडी समजत नाही.",
    soybean:
      "दाणे कोरडे आणि जमिनीपासून उंच ठेवा. साठवण्यापूर्वी दाण्यातील ओलावा आणि साठवणीतील ओल तपासा.",
    onionReady: "वाळवलेला आणि हवेशीर: हवा खेळती ठेवा आणि खराब कांदे वेगळे करा.",
    onionWet:
      "न वाळवलेला: साठवण्यापूर्वी वाळवणे आणि हवा तपासा. ओले किंवा खराब कांदे वेगळे करा.",
    tomatoToday: "आज तोडलेले: ठेवण्यापूर्वी पिकण्याची अवस्था आणि पॅकिंग तपासा.",
    tomatoRecent:
      "1–2 दिवसांपूर्वी तोडलेले: पाठवण्यापूर्वी पिकण्याची अवस्था आणि घट्टपणा तपासा.",
    tomatoOlder:
      "3+ दिवसांपूर्वी तोडलेले: आधी तपासणी करा आणि मऊ किंवा खराब फळे वेगळी करा.",
    soybeanReady: "पूर्ण वाळलेले: ओलावा टाळा आणि नियमित तपासा.",
    soybeanWet:
      "पूर्ण न वाळलेले: साठवण्यापूर्वी वाळवणे आणि दाण्यातील ओलावा तपासा.",
    unknown:
      "अधिक नेमक्या मार्गदर्शनासाठी वरील ताजेपणाच्या प्रश्नाचे उत्तर द्या.",
  },
  hi: {
    onion:
      "हवा का प्रवाह बनाए रखें और प्याज सूखा रखें। बाहर की आर्द्रता से गोदाम के अंदर जमा नमी का पता नहीं चलता।",
    tomato:
      "क्रेट छाया में रखें, चोट से बचाएं और नरम फल जांचें। संघनन रोकें; केवल आर्द्रता से सड़न का अनुमान नहीं होता।",
    soybean:
      "दाना सूखा और फर्श से ऊपर रखें। भंडारण से पहले दाने की नमी और अंदर जमा नमी जांचें।",
    onionReady: "सुखाया और हवादार: हवा बनाए रखें और खराब प्याज अलग करें।",
    onionWet:
      "बिना सुखाया: भंडारण से पहले सुखाने और हवा की व्यवस्था जांचें। गीले या खराब प्याज अलग करें।",
    tomatoToday: "आज तोड़े गए: रखने से पहले पकने की अवस्था और पैकिंग जांचें।",
    tomatoRecent:
      "1–2 दिन पहले तोड़े गए: भेजने से पहले पकने की अवस्था और मजबूती जांचें।",
    tomatoOlder:
      "3+ दिन पहले तोड़े गए: पहले जांच करें और नरम या खराब फल अलग करें।",
    soybeanReady: "पूरी तरह सूखा: नमी से बचाएं और नियमित जांच करें।",
    soybeanWet:
      "पूरी तरह नहीं सूखा: रखने से पहले सुखाने और दाने की नमी जांचें।",
    unknown: "अधिक व्यक्तिगत मार्गदर्शन के लिए ऊपर ताज़गी का उत्तर दें।",
  },
};

export function WeatherPanel({
  village,
  crop,
  condition,
  lang,
  pricesAsOf,
}: {
  village: string;
  crop: Crop;
  condition: LotCondition;
  lang: Lang;
  pricesAsOf: string;
}) {
  const { result, loading, error, reload } = useResource(
    `weather:${village}`,
    () => getWeather(village),
  );
  const t = copy[lang];
  const g = guidance[lang];
  const weather = result?.data;
  const available =
    !loading &&
    !error &&
    weather?.available === true &&
    weather.village === village;
  const display = (value: number | undefined, unit: string) =>
    typeof value === "number" && Number.isFinite(value)
      ? `${new Intl.NumberFormat(lang === "en" ? "en-IN" : lang === "mr" ? "mr-IN" : "hi-IN", { maximumFractionDigits: 1 }).format(value)}${unit}`
      : t.missing;
  const timestamp = weather?.time
    ? new Date(
        /(?:Z|[+-]\d{2}:\d{2})$/.test(weather.time)
          ? weather.time
          : weather.time + "+05:30",
      )
    : null;
  const updated =
    timestamp && !Number.isNaN(timestamp.getTime())
      ? new Intl.DateTimeFormat(
          lang === "en" ? "en-IN" : lang === "mr" ? "mr-IN" : "hi-IN",
          {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "numeric",
            minute: "2-digit",
            timeZone: "Asia/Kolkata",
          },
        ).format(timestamp) + " IST"
      : t.missing;
  const conditionText =
    condition === null
      ? g.unknown
      : crop === "onion"
        ? condition === true
          ? g.onionReady
          : g.onionWet
        : crop === "soybean"
          ? condition === true
            ? g.soybeanReady
            : g.soybeanWet
          : condition === 0
            ? g.tomatoToday
            : condition === 1
              ? g.tomatoRecent
              : g.tomatoOlder;

  return (
    <section
      className={`panel ${styles.panel}`}
      aria-label={t.title}
      aria-busy={loading}
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow">{t.eyebrow}</span>
          <h2>
            <CloudSun size={20} /> {t.title}
          </h2>
        </div>
        <span className={`badge ${styles.location}`}>
          <MapPin size={12} /> {village}
        </span>
      </div>
      <div className={styles.content}>
        <div className={styles.conditions}>
          {available ? (
            <>
              <div className={styles.readings}>
                <div>
                  <span>
                    <Thermometer size={15} /> {t.temperature}
                  </span>
                  <strong>{display(weather.temperature_c, "°C")}</strong>
                </div>
                <div>
                  <span>
                    <Droplets size={15} /> {t.humidity}
                  </span>
                  <strong>{display(weather.relative_humidity_pct, "%")}</strong>
                </div>
              </div>
              <p className={styles.timestamp}>
                {t.updated}: {updated}
              </p>
            </>
          ) : (
            <div className={styles.unavailable} role="status">
              {loading ? (
                <RefreshCw size={22} className={styles.spinner} />
              ) : (
                <WifiOff size={22} />
              )}
              <strong>{loading ? t.loading : t.unavailable}</strong>
              {!loading && <p>{t.offline}</p>}
            </div>
          )}
          <button className="button subtle" disabled={loading} onClick={reload}>
            <RefreshCw size={13} /> {t.refresh}
          </button>
        </div>
        <div className={styles.guidance}>
          <span className="eyebrow">
            <Leaf size={13} /> {t.crops[crop]} · {t.check}
          </span>
          <p className={styles.answer}>{conditionText}</p>
          <p>{g[crop]}</p>
        </div>
      </div>
      <div className={styles.footer}>
        <p>{t.boundary}</p>
        {available && weather.time?.slice(0, 10) !== pricesAsOf && (
          <p>
            {t.history} {dateLabel(pricesAsOf)}.
          </p>
        )}
        <details>
          <summary>{t.more}</summary>
          <p>{t.note}</p>
          <div className={styles.sources}>
            <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">
              {t.provider}
            </a>
            <a
              href={
                crop === "onion"
                  ? "https://postharvest.ucdavis.edu/produce-facts-sheets/onions-dry"
                  : crop === "tomato"
                    ? "https://postharvest.ucdavis.edu/produce-facts-sheets/tomato"
                    : "https://extension.umn.edu/agriculture/crop-production/soybean/storing-drying-and-handling-wet-soybeans"
              }
              target="_blank"
              rel="noreferrer"
            >
              {lang === "en"
                ? "Crop storage reference"
                : lang === "mr"
                  ? "साठवण संदर्भ"
                  : "भंडारण संदर्भ"}
            </a>
          </div>
        </details>
        {available && (
          <a
            className={styles.attribution}
            href="https://open-meteo.com/"
            target="_blank"
            rel="noreferrer"
          >
            {weather.attribution || t.provider}
          </a>
        )}
      </div>
    </section>
  );
}
