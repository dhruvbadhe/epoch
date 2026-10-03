export const rupees = (n: number) =>
  `₹${Math.round(n).toLocaleString("en-IN")}`;
export const signedRupees = (n: number) =>
  `${n < 0 ? "−" : "+"}${rupees(Math.abs(n))}`;
export const NOT_ENOUGH = "not enough data";
export const percentage = (n: number | null | undefined) =>
  n === null || n === undefined ? NOT_ENOUGH : `${(n * 100).toFixed(1)}%`;
export const metric = (n: number | null | undefined) =>
  n === null || n === undefined ? NOT_ENOUGH : rupees(n);
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
export const dateLabel = (date: string) => {
  const [y, m, d] = date.slice(0, 10).split("-").map(Number);
  return y && m && d ? `${d} ${MONTHS[m - 1]} ${y}` : date;
};
export const sellDay = (day: number) => (day === 0 ? "Today" : `Day ${day}`);
export const cropLabel = (crop: string) =>
  crop.charAt(0).toUpperCase() + crop.slice(1);
