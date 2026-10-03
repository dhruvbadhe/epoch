"use client";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Info,
  Leaf,
  ShieldCheck,
} from "lucide-react";
import type { Advice, Lang } from "@/lib/types";
import { percentage, rupees, signedRupees } from "@/lib/format";
const labels = {
  en: {
    recommendation: "Recommendation",
    hold: "Hold",
    days: "days",
    sell: "Sell today",
    at: "Sell at",
    hand: "per harvested quintal in hand",
    range: "Expected range",
    total: "Estimated total for your lot",
    confidence: "confidence",
    gain: "compared with selling today at",
    condition: "Before you dispatch",
    check: "Go only if the reported price is above",
    verify: "Check with the mandi before sending the crop.",
    limit: "Estimated selling window: up to",
    why: "Why this estimate?",
    refine: "Would refine it",
    reading: "Further reading (no figures taken from these)",
    storage: "Storage guidance",
    suppressed:
      "Holding was switched off: past hold advice for this crop did not pay off often enough, so sell today.",
    notes: "Notes from the engine",
  },
  mr: {
    recommendation: "तुमच्यासाठी सल्ला",
    hold: "थांबा",
    days: "दिवस",
    sell: "आज विका",
    at: "येथे विका",
    hand: "प्रति कापणी केलेल्या क्विंटल हातात",
    range: "अंदाजित श्रेणी",
    total: "तुमच्या मालाची अंदाजित एकूण रक्कम",
    confidence: "खात्री",
    gain: "आज विकण्याच्या तुलनेत",
    condition: "माल पाठवण्यापूर्वी",
    check: "बाजारभाव यापेक्षा जास्त असेल तरच जा",
    verify: "माल पाठवण्यापूर्वी बाजारात खात्री करा.",
    limit: "अंदाजे विक्री कालावधी: जास्तीत जास्त",
    why: "हा अंदाज का?",
    refine: "अधिक अचूकतेसाठी",
    reading: "अधिक वाचन (यातील आकडे वापरलेले नाहीत)",
    storage: "साठवण मार्गदर्शन",
    suppressed:
      "थांबण्याचा सल्ला बंद केला: या पिकासाठी मागील थांबण्याचे सल्ले पुरेसे वेळा फायद्याचे ठरले नाहीत, म्हणून आजच विका.",
    notes: "इंजिनच्या नोंदी",
  },
  hi: {
    recommendation: "आपके लिए सलाह",
    hold: "रुकें",
    days: "दिन",
    sell: "आज बेचें",
    at: "यहाँ बेचें",
    hand: "प्रति कटाई किए गए क्विंटल हाथ में",
    range: "अनुमानित सीमा",
    total: "आपके माल की अनुमानित कुल राशि",
    confidence: "भरोसा",
    gain: "आज बेचने की तुलना में",
    condition: "माल भेजने से पहले",
    check: "बाजार भाव इससे ऊपर हो तभी जाएं",
    verify: "माल भेजने से पहले मंडी से जांचें।",
    limit: "अनुमानित बिक्री समय: अधिकतम",
    why: "यह अनुमान क्यों?",
    refine: "और सटीकता के लिए",
    reading: "और पढ़ें (इनसे कोई आंकड़ा नहीं लिया गया)",
    storage: "भंडारण मार्गदर्शन",
    suppressed:
      "रुकने की सलाह बंद की गई: इस फसल के लिए पिछली रुकने की सलाह पर्याप्त बार फ़ायदेमंद नहीं रही, इसलिए आज ही बेचें।",
    notes: "इंजन के नोट",
  },
};
export function AdviceCard({
  advice,
  quantity,
  lang,
  village,
}: {
  advice: Advice;
  quantity: number;
  lang: Lang;
  village?: string;
}) {
  const t = labels[lang];
  const hold = advice.action === "hold";
  const confidence =
    lang === "en"
      ? advice.confidence
      : lang === "mr"
        ? { high: "उच्च", medium: "मध्यम", low: "कमी" }[advice.confidence]
        : { high: "उच्च", medium: "मध्यम", low: "कम" }[advice.confidence];
  return (
    <section
      className={`advice-card ${hold ? "" : "sell-now"}`}
      aria-label="Recommendation"
    >
      <div className="advice-top">
        <span className="eyebrow">
          <span className="light-dot" />
          {t.recommendation}
        </span>
        <span className="confidence">
          <ShieldCheck size={14} />
          {confidence} {t.confidence}
        </span>
      </div>
      <h2 className="action-line">
        {hold ? (
          <>
            {t.hold}{" "}
            <span>
              {advice.days} {t.days}
            </span>
          </>
        ) : (
          t.sell
        )}
        <ArrowRight size={27} />
      </h2>
      <div className="destination">
        <span>{t.at}</span> {advice.mandi}
      </div>
      <div className="advice-money">
        <strong>{rupees(advice.net_per_qtl)}</strong>
        <span>{t.hand}</span>
      </div>
      {hold && (
        <div className="advice-range">
          {t.range}{" "}
          <strong>
            {rupees(advice.net_low)} – {rupees(advice.net_high)}
          </strong>
        </div>
      )}
      <div className="advice-gain">
        <ArrowUpRight size={18} />
        <strong>{signedRupees(advice.gain_vs_baseline)}</strong>
        <span>
          {t.gain} {advice.baseline_today.mandi}
        </span>
      </div>
      <div className="advice-bottom">
        <div>
          <span>{t.total}</span>
          <strong>{rupees(advice.net_per_qtl * quantity)}</strong>
        </div>
        <div className="crop-mark" aria-hidden="true">
          <Leaf size={45} />
        </div>
      </div>
      {hold && advice.break_even_price !== null && (
        <div className="dispatch">
          <CheckCircle2 size={19} />
          <div>
            <strong>{t.condition}</strong>
            <p>
              {t.check} <b>{rupees(advice.break_even_price!)}</b>. {t.verify}
            </p>
          </div>
        </div>
      )}
      <div className="advice-footnote">
        <CalendarDays size={14} />
        {t.limit}{" "}
        {advice.freshness?.estimated_window_days ?? advice.hold_limit_days}{" "}
        {t.days}.
        {advice.freshness && (
          <>
            <br />
            <span className="tiny">{advice.freshness.basis}</span>
            <details className="freshness-why">
              <summary>{t.why}</summary>
              {advice.freshness.reasons.map((r, i) => (
                <p key={i}>{r}</p>
              ))}
              <p>
                {t.refine}: {advice.freshness.missing.join(", ")}
              </p>
              <p className="tiny">
                {t.reading}: {advice.freshness.references.join(" · ")}
              </p>
            </details>
          </>
        )}
        {hold && advice.storage_tip && (
          <>
            <br />
            <Leaf size={14} />
            <span>
              {t.storage}: {advice.storage_tip}
            </span>
          </>
        )}
      </div>
      {hold && advice.hold_success_rate !== null && (
        <p className="advice-footnote">
          Last season, hold advice beat the best sell-today option{" "}
          {percentage(advice.hold_success_rate)} of the time.
        </p>
      )}
      {advice.hold_suppressed && (
        <p className="advice-footnote hold-suppressed" role="note">
          <Info size={14} />
          <strong>
            {lang === "en"
              ? `Waiting not recommended. ${advice.notes.find((note) => /hold suppressed/i.test(note)) ?? t.suppressed}`
              : t.suppressed}
          </strong>
        </p>
      )}
      {advice.notes.length > 0 && (
        <div className="advice-footnote advice-card-notes">
          <span>{t.notes}:</span>
          {advice.notes.map((note, i) => (
            <p key={i}>{note}</p>
          ))}
        </div>
      )}
      {advice.uses_baseline && (
        <p className="advice-footnote">
          <Info size={14} />
          The selected option uses a baseline price from the API.
        </p>
      )}
    </section>
  );
}
