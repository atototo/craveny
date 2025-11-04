import type { Metadata } from "next";
import "./globals.css";
import Navigation from "./components/Navigation";
import PredictionStatusBanner from "./components/PredictionStatusBanner";

export const metadata: Metadata = {
  title: "Craveny Dashboard",
  description: "주가 예측 대시보드",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-50">
        <Navigation />
        <PredictionStatusBanner />
        {children}
      </body>
    </html>
  );
}
