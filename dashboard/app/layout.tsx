import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { headers } from "next/headers";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("host") ?? "localhost:3000";
  const protocol = host.startsWith("localhost") ? "http" : "https";
  const image = new URL("/og.png", `${protocol}://${host}`);
  return {
    title: "OpenSignal PH | Safety Surveillance",
    description:
      "Evidence-first adverse-event signal detection and public-health surveillance.",
    openGraph: {
      title: "OpenSignal PH",
      description: "Safety surveillance, without false certainty.",
      images: [image],
    },
    twitter: {
      card: "summary_large_image",
      title: "OpenSignal PH",
      description: "Safety surveillance, without false certainty.",
      images: [image],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
