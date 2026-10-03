import { Lightbulb } from "lucide-react";
import type { Advice } from "@/lib/types";
import { dateLabel, rupees, signedRupees } from "@/lib/format";

// "What influenced this advice": every value is a field of the engine's /advise response.
export function Influences({
  advice,
  village,
}: {
  advice: Advice;
  village: string;
}) {
  const chosen = advice.options.find(
    (o) => o.mandi === advice.mandi && o.sell_day === advice.days,
  );
  const today = advice.options.filter((o) => o.sell_day === 0);
  const topPrice = today.reduce<(typeof today)[number] | null>(
    (best, o) => (!best || o.price_mid > best.price_mid ? o : best),
    null,
  );
  const items: string[] = [
    `Price: ${rupees(advice.why.price)} per quintal at ${advice.mandi}${
      advice.days
        ? ` in ${advice.days} days (forecast mid)`
        : ", the latest reported price"
    } (prices as of ${dateLabel(advice.prices_as_of)}).`,
  ];
  if (chosen)
    items.push(
      `Transport: ${chosen.distance_km.toFixed(1)} km by road from ${village}, ${rupees(chosen.transport_per_qtl)} per quintal (assumed rate).`,
    );
  if (advice.why.spoilage_loss || advice.why.storage)
    items.push(
      `Holding costs: ${rupees(advice.why.spoilage_loss)} spoilage and ${rupees(advice.why.storage)} storage per quintal (assumptions).`,
    );
  items.push(
    advice.gain_vs_baseline > 0
      ? `Nearest mandi ${advice.baseline_today.mandi} leaves ${rupees(advice.baseline_today.net)} in hand today; this choice leaves ${signedRupees(advice.gain_vs_baseline)} more.`
      : `The nearest mandi, ${advice.baseline_today.mandi}, is already the best choice today.`,
  );
  if (topPrice && topPrice.mandi !== advice.mandi)
    items.push(
      `${topPrice.mandi} pays the highest price (${rupees(topPrice.price_mid)}), but after transport it leaves ${rupees(topPrice.net_per_qtl)} in hand.`,
    );
  items.push(
    advice.hold_suppressed
      ? "Waiting was considered but switched off: past advice to wait for this crop did not pay off often enough."
      : advice.days > 0
        ? `Waiting ${advice.days} days adds ${signedRupees(advice.gain_from_waiting)} per quintal over selling today.`
        : "No waiting option beat selling today by enough.",
  );
  items.push(
    advice.uses_baseline
      ? `Confidence: ${advice.confidence}. The forecast model did not beat "price stays the same" here, so only today's prices were compared.`
      : `Confidence: ${advice.confidence}, from the forecast's self-check and the age of the last price report.`,
  );
  return (
    <section
      className="panel influences"
      aria-label="What influenced this advice"
    >
      <div className="section-heading">
        <h2>
          <Lightbulb size={18} /> What influenced this advice
        </h2>
      </div>
      <ul>
        {items.map((t, i) => (
          <li key={i}>{t}</li>
        ))}
      </ul>
    </section>
  );
}
