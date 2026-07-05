import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { ColdStartNotice } from "@/components/layout/ColdStartNotice";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "台股分析平台 | Stock Analysis",
  description: "台灣股票五維度深度分析平台 - 消息面、基本面、技術面、籌碼面、總經面",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-TW"
      className={`dark ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <Sidebar />
        <ColdStartNotice />
        <main className="min-h-screen pt-14 md:ml-60 md:pt-0">{children}</main>
      </body>
    </html>
  );
}
