import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

import type { Metadata } from "next";

export const metadata: Metadata = {
  metadataBase: new URL('https://nvusdev.github.io/simple-productivity-blocker/'),
  title: {
    default: "Simple Productivity Blocker | Absolute Focus for Windows",
    template: "%s | Simple Productivity Blocker"
  },
  description: "A hardened, kernel-level Windows productivity blocker. Secure your focus with the Triple-Lock suite. Perfect for students, developers, writers, and ADHD focus.",
  keywords: ["productivity blocker", "windows app blocker", "ADHD focus tool", "hardened focus software", "kernel-level blocker", "website filter for windows", "deep work tool", "student focus", "developer productivity"],
  alternates: {
    canonical: './',
  },
  openGraph: {
    title: "Simple Productivity Blocker",
    description: "Secure your focus when willpower isn't enough. System-level enforcement for absolute concentration.",
    type: "website",
    url: "/",
    siteName: "SPB",
    locale: 'en_US',
  },
  twitter: {
    card: "summary_large_image",
    title: "Simple Productivity Blocker",
    description: "Hardened Windows focus tool for absolute productivity.",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
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
