"use client";
import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Scale, FileText, ShieldAlert, Cpu, AlertTriangle, HelpCircle, ArrowLeft } from "lucide-react";
import Footer from "@/components/Footer";

export default function EulaPage() {
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
      icon: FileText,
      title: "1. Grant of License",
      color: "text-blue-500 bg-blue-500/10 border-blue-500/20",
      content: (
        <p>
          Subject to the terms of this Agreement, nvusdev grants you a personal, non-transferable, non-exclusive license to use the Software on your Windows devices in accordance with the official <strong>MIT License terms</strong>.
        </p>
      )
    },
    {
      icon: Cpu,
      title: "2. System-Level Enforcement",
      color: "text-purple-500 bg-purple-500/10 border-purple-500/20",
      content: (
        <div className="space-y-3">
          <p>You acknowledge that the Software operates at the deep Windows operating system level and performs high-integrity system adjustments:</p>
          <ul className="list-disc pl-5 space-y-1.5 text-zinc-400">
            <li><strong>DNS Interception:</strong> Reconfigures network adapters to query a loopback-bound DNS proxy.</li>
            <li><strong>Hosts File Modification:</strong> Appends redundancy blocking records to the system <code>hosts</code> file.</li>
            <li><strong>NTFS ACL Management:</strong> Restructures directory and file security descriptors to lock execution.</li>
            <li><strong>Process Management:</strong> Monitors active task names and forcibly terminates targeted executables.</li>
            <li><strong>Registry Overrides:</strong> Applies policy edits to restrict browser DNS-over-HTTPS bypass vectors.</li>
          </ul>
        </div>
      )
    },
    {
      icon: ShieldAlert,
      title: "3. 'As-Is' Warranty Disclaimer",
      color: "text-rose-500 bg-rose-500/10 border-rose-500/20",
      content: (
        <div className="space-y-3 font-mono text-xs text-zinc-400 bg-zinc-950/60 p-4 rounded-xl border border-zinc-900 leading-relaxed uppercase">
          THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. THE DEVELOPER DOES NOT WARRANT THAT THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE. YOU ASSUME ALL RISKS ASSOCIATED WITH SYSTEM-LEVEL PERMISSION MODIFICATIONS AND NETWORK ADAPTER MANIPULATIONS.
        </div>
      )
    },
    {
      icon: AlertTriangle,
      title: "4. Strict Limitation of Liability",
      color: "text-amber-500 bg-amber-500/10 border-amber-500/20",
      content: (
        <div className="space-y-3">
          <p className="font-mono text-xs text-zinc-400 bg-zinc-950/60 p-4 rounded-xl border border-zinc-900 leading-relaxed uppercase mb-3">
            IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS.
          </p>
          <p>
            This exclusion specifically limits liability for <strong>data loss, OS instability, or loss of access to files</strong> resulting from password losses, configuration corruption, or improper execution of background services.
          </p>
        </div>
      )
    },
    {
      icon: HelpCircle,
      title: "5. Non-Bypass & Recovery Paths",
      color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
      content: (
        <div className="space-y-3">
          <p>
            The software is intentionally designed to bridge the "willpower gap." You agree not to attempt to reverse engineer, decompile, or bypass the application rules during active enforcement sessions.
          </p>
          <p>
            If a lock becomes orphaned or unstable, you are expected to use the provided recovery utility (<code>recovery_uplift.exe</code>) in Windows Safe Mode. You are solely responsible for keeping system backups.
          </p>
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
            <Scale size={12} /> Legal Agreement
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-4"
          >
            End User License Agreement
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

        {/* EULA Legal Notice Banner */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="p-6 rounded-2xl border border-red-500/20 bg-red-500/5 backdrop-blur-md mb-12 flex gap-4 items-start"
        >
          <ShieldAlert className="text-red-500 shrink-0 mt-0.5" size={24} />
          <div>
            <h3 className="text-base font-bold text-red-400 mb-2">High-Integrity System Notice</h3>
            <p className="text-zinc-300 text-sm leading-relaxed">
              By installing and running Simple Productivity Blocker, you grant permissions to alter registry structures, filter DNS ports, and secure system files. Please read these terms carefully before initialization.
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
