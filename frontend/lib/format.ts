export const rupees = (n: number) =>
  `₹${Math.round(n).toLocaleString("en-IN")}`;
export const signedRupees = (n: number) =>
  `${n < 0 ? "−" : "+"}${rupees(Math.abs(n))}`;
export const percentage = (n: number | null) =>
  n === null ? "Not evaluated" : `${(n * 100).toFixed(1)}%`;
export const metric = (n: number | null) =>
  n === null ? "Not evaluated" : rupees(n);
export const dateLabel = (date: string) =>
  new Date(date + "T12:00:00").toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
export const sellDay = (day: number) => (day === 0 ? "Today" : `Day ${day}`);
export const cropLabel = (crop: string) =>
  crop.charAt(0).toUpperCase() + crop.slice(1);
