import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "SahiDaam — A better way to market",
  description:
    "Money-in-hand crop advice and collective market planning for Maharashtra FPOs.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
