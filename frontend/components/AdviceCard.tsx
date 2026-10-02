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
    recommendation: "YOUR RECOMMENDATION",
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
    limit: "This lot can be held up to",
    storage: "Storage guidance",
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
    limit: "हा माल इतके दिवस ठेवता येईल",
    storage: "साठवण मार्गदर्शन",
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
    limit: "यह माल इतने दिन रखा जा सकता है",
    storage: "भंडारण मार्गदर्शन",
  },
};
export function AdviceCard({
  advice,
  quantity,
  lang,
}: {
  advice: Advice;
  quantity: number;
  lang: Lang;
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
        {t.limit} {advice.hold_limit_days} {t.days}.
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
      {advice.uses_baseline && (
        <p className="advice-footnote">
          <Info size={14} />
          Forecast self-check failed. Only today’s options are recommended.
        </p>
      )}
    </section>
  );
}
