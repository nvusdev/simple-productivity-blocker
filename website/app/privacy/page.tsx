"use client";
import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShieldCheck, Eye, Network, Lock, Globe, AlertCircle, ArrowLeft } from "lucide-react";
import Footer from "@/components/Footer";

export default function PrivacyPolicyPage() {
  const [backUrl, setBackUrl] = React.useState("/");

  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const fromParam = params.get("from");
      if (fromParam) {
        setBackUrl(fromParam);
      }
    }
  }, []);
  const sections = [
    {
      icon: ShieldCheck,
      title: "1. Local-First Architecture",
      color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
      content: (
        <div className="space-y-3">
          <p>SPB is designed with a <strong>privacy-first, local-only architecture</strong>. Your data never leaves your computer.</p>
          <ul className="list-disc pl-5 space-y-1.5 text-zinc-400">
            <li><strong>No Data Collection:</strong> We do not collect, store, or transmit any personal data, browsing history, application usage, or configurations.</li>
            <li><strong>Local Storage:</strong> Configurations, lists, schedules, and logs are stored exclusively on your local device (typically in <code>%ProgramData%\SimpleProductivityBlocker</code>).</li>
            <li><strong>No Accounts Required:</strong> Absolutely no accounts, cloud registration, or user profiling.</li>
          </ul>
        </div>
      )
    },
    {
      icon: Network,
      title: "2. Network Interception",
      color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
      content: (
        <div className="space-y-3">
          <p>To provide website blocking functionality, SPB intercepts DNS requests locally on your machine or writes entries to the system hosts file.</p>
          <ul className="list-disc pl-5 space-y-1.5 text-zinc-400">
            <li><strong>Local Processing:</strong> All filtering decisions are evaluated locally. No network traffic is routed through third-party servers.</li>
            <li><strong>Upstream DNS:</strong> Unblocked traffic is forwarded directly to your system's configured DNS provider or ISP DNS. We have no control over upstream DNS logging.</li>
          </ul>
        </div>
      )
    },
    {
      icon: Lock,
      title: "3. System Permissions",
      color: "text-rose-500 bg-rose-500/10 border-rose-500/20",
      content: (
        <div className="space-y-3">
          <p>SPB requires Administrative privileges to perform its core functions. These elevated privileges are used **strictly** to enforce your productivity rules:</p>
          <ul className="list-disc pl-5 space-y-1.5 text-zinc-400">
            <li>Modifying local adapter DNS settings to point to the local DNS proxy.</li>
            <li>Managing Windows Scheduled Tasks for persistent startup enforcement.</li>
            <li>Modifying NTFS Access Control Lists (ACLs) to secure protected files and folders.</li>
            <li>Terminating process handles of unauthorized applications.</li>
          </ul>
        </div>
      )
    },
    {
      icon: Globe,
      title: "4. Third-Party Services",
      color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
      content: (
        <div className="space-y-3">
          <p>If you configure external adblocker or filter category lists:</p>
          <ul className="list-disc pl-5 space-y-1.5 text-zinc-400">
            <li><strong>Direct Downloads:</strong> SPB pulls lists directly from the URLs you specify.</li>
            <li><strong>SSRF Protection:</strong> Security logic strictly ensures these connections do not query your local network.</li>
            <li><strong>IP Visibility:</strong> Third-party list hosters see your IP address during downloads, subject to their own policies.</li>
          </ul>
        </div>
      )
    },
    {
      icon: AlertCircle,
      title: "5. Policy Changes & Support",
      color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
      content: (
        <div className="space-y-3">
          <p>We may update this Privacy Policy from time to time to reflect changes in our local practices. Any updates are bundled in our repository and releases.</p>
          <p>For support, questions about application privacy behavior, or audits, refer directly to our GitHub repository at <a href="https://github.com/nvusdev/simple-productivity-blocker" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">github.com/nvusdev/simple-productivity-blocker</a>.</p>
        </div>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500 flex flex-col font-sans">
      {/* Background Radial Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[600px] bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.03),transparent_70%)] pointer-events-none" />

      {/* Main Content Area */}
      <main className="max-w-4xl mx-auto px-8 pt-28 pb-20 relative z-10 grow w-full">
        {/* Back Link */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="mb-8"
        >
          <Link
            href={backUrl}
            className="inline-flex items-center gap-2 text-zinc-500 hover:text-blue-500 transition-colors text-sm font-semibold group"
          >
            <ArrowLeft size={16} className="transition-transform group-hover:-translate-x-1" />
            Back to Home
          </Link>
        </motion.div>

        {/* Title and Metadata */}
        <div className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-500 text-xs font-semibold mb-4"
          >
            <Eye size={12} /> Privacy First
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-4"
          >
            Privacy Policy
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="text-zinc-500 text-sm font-mono"
          >
            LAST UPDATED: MAY 15, 2026
          </motion.p>
        </div>

        {/* Introduction Warning Banner */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="p-6 rounded-2xl border border-blue-500/20 bg-blue-500/5 backdrop-blur-md mb-12 flex gap-4 items-start"
        >
          <ShieldCheck className="text-blue-500 shrink-0 mt-0.5" size={24} />
          <div>
            <h3 className="text-base font-bold text-blue-400 mb-2">Absolute Local Privacy</h3>
            <p className="text-zinc-300 text-sm leading-relaxed">
              Simple Productivity Blocker functions as an offline system utility. We believe your productivity rules are private; therefore, **no cloud synchronization, backend telemetries, or diagnostic analytics** are ever integrated.
            </p>
          </div>
        </motion.div>

        {/* Section Cards */}
        <div className="space-y-8 mb-16">
          {sections.map((sec, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="p-8 rounded-3xl border border-zinc-900 bg-zinc-900/20 hover:border-zinc-800 transition-all duration-300 backdrop-blur-sm"
            >
              <div className="flex gap-4 items-start mb-6">
                <div className={`p-2.5 rounded-xl border shrink-0 ${sec.color}`}>
                  <sec.icon size={20} />
                </div>
                <h2 className="text-xl font-bold text-zinc-100 pt-1.5">{sec.title}</h2>
              </div>
              <div className="text-zinc-300 leading-relaxed text-sm">
                {sec.content}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom Back Button */}
        <div className="flex justify-center border-t border-zinc-900 pt-12">
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <Link
              href={backUrl}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900 transition-all text-zinc-100 text-sm font-bold shadow-lg"
            >
              <ArrowLeft size={16} /> Return to Dashboard Home
            </Link>
          </motion.div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
