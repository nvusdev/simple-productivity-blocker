import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

import type { Metadata } from "next";

export const metadata: Metadata = {
  metadataBase: new URL('https://nvusdev.github.io/simple-productivity-blocker/'),
  title: "Simple Productivity Blocker | Absolute Focus for ADHD & Students",
  description: "A hardened, kernel-level Windows productivity blocker. Secure your focus with the Triple-Lock suite. Perfect for students, ADHD, and deep work.",
  keywords: ["productivity blocker", "windows app blocker", "ADHD focus tool", "hardened focus software", "kernel-level blocker", "website filter for windows"],
  alternates: {
    canonical: '/',
  },
  openGraph: {
    title: "Simple Productivity Blocker",
    description: "Secure your focus when willpower isn't enough. System-level enforcement for absolute concentration.",
    type: "website",
    url: "/",
    siteName: "SPB",
  },
  twitter: {
    card: "summary_large_image",
    title: "Simple Productivity Blocker",
    description: "Hardened Windows focus tool for absolute productivity.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${outfit.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
