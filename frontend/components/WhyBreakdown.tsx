import { ArrowDown, ArrowUpRight, ReceiptText } from "lucide-react";
import type { Advice } from "@/lib/types";
import { rupees, signedRupees } from "@/lib/format";
export function WhyBreakdown({ advice }: { advice: Advice }) {
  const deductions = [
    { label: "Spoilage loss (assumption)", value: advice.why.spoilage_loss },
    { label: "Transport & loading (assumption)", value: advice.why.transport },
    { label: "Storage (assumption)", value: advice.why.storage },
    { label: "Mandi fees", value: advice.why.fees },
  ];
  return (
    <section className="panel breakdown">
      <div className="section-heading">
        <div>
          <span className="eyebrow">THE MATH BEHIND THE ADVICE</span>
          <h2>Price isn’t your profit.</h2>
        </div>
        <ReceiptText size={22} />
      </div>
      <p className="muted">Every cost counted. Every rupee explained.</p>
      <div className="breakdown-row initial">
        <span>
          {advice.days ? "Forecast price" : "Reported price"}
          <small>/quintal</small>
        </span>
        <strong>{rupees(advice.why.price)}</strong>
      </div>
      {deductions.map((item) => (
        <div className="breakdown-row" key={item.label}>
          <span>
            <span className="minus">−</span>
            {item.label}
          </span>
          <span>{rupees(item.value)}</span>
        </div>
      ))}
      <div className="breakdown-total">
        <span>
          <ArrowDown size={16} />
          Money in hand
        </span>
        <strong>{rupees(advice.net_per_qtl)}</strong>
      </div>
      <div className="gain-split">
        <div>
          <ArrowUpRight size={17} />
          <strong>{signedRupees(advice.gain_from_mandi)}</strong>
          <span>from choosing the mandi</span>
        </div>
        <div>
          <ArrowUpRight size={17} />
          <strong>{signedRupees(advice.gain_from_waiting)}</strong>
          <span>from waiting</span>
        </div>
      </div>
      <p className="tiny">
        All amounts per harvested quintal. Costs use{" "}
        {advice.assumptions_default ? "default" : "your edited"} assumptions.
      </p>
    </section>
  );
}
