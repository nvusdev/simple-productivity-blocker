"use client";
import { motion } from "framer-motion";
import { XCircle, CheckCircle2, ShieldAlert, ShieldCheck } from "lucide-react";

const comparisonData = [
  {
    feature: "Enforcement Level",
    competitors: "Browser-level (Easy to bypass)",
    spb: "Kernel-level (Triple-Lock Suite)",
    status: true,
  },
  {
    feature: "Block Method",
    competitors: "Passive URL matching",
    spb: "Deep DNS & Registry Interception",
    status: true,
  },
  {
    feature: "Circumvention",
    competitors: "Can be closed or uninstalled",
    spb: "Hardened against task termination",
    status: true,
  },
  {
    feature: "System Integration",
    competitors: "Generic application layer",
    spb: "Windows Native ACLs & NTFS Locks",
    status: true,
  },
  {
    feature: "Recovery",
    competitors: "Manual cleanup required",
    spb: "Automated Safe-Boot Sweep",
    status: true,
  }
];

export default function Comparison() {
  return (
    <section className="py-32 bg-zinc-950/50 relative overflow-hidden">
      <div className="container mx-auto px-6">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">The Focus Reality.</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Most focus tools are just "suggestions." SPB is a commitment. We've built the most 
            hardened <strong>Windows app blocker</strong> to bridge the gap between intent and action.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {/* Competitors Card */}
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-3xl border border-zinc-800 bg-zinc-900/20 p-8 backdrop-blur-sm"
          >
            <div className="flex items-center gap-3 mb-8 text-zinc-500">
              <ShieldAlert size={24} />
              <h3 className="text-xl font-bold uppercase tracking-widest">Weak Surface Blockers</h3>
            </div>
            
            <ul className="space-y-6">
              {comparisonData.map((item, i) => (
                <li key={i} className="flex items-start gap-4 text-zinc-500">
                  <XCircle className="shrink-0 mt-1" size={18} />
                  <div>
                    <p className="text-sm font-semibold text-zinc-600 mb-1">{item.feature}</p>
                    <p className="text-base">{item.competitors}</p>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* SPB Card */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-3xl border border-emerald-500/20 bg-emerald-500/5 p-8 backdrop-blur-md shadow-[0_0_50px_rgba(16,185,129,0.05)] relative overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 blur-[80px]" />
            
            <div className="flex items-center gap-3 mb-8 text-emerald-500">
              <ShieldCheck size={24} />
              <h3 className="text-xl font-bold uppercase tracking-widest">The Supportive Shield</h3>
            </div>
            
            <ul className="space-y-6">
              {comparisonData.map((item, i) => (
                <li key={i} className="flex items-start gap-4">
                  <CheckCircle2 className="shrink-0 mt-1 text-emerald-500" size={18} />
                  <div>
                    <p className="text-sm font-semibold text-emerald-500/60 mb-1">{item.feature}</p>
                    <p className="text-base text-zinc-100 font-medium">{item.spb}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-12 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400 font-mono text-center">
              KERNEL_ENFORCEMENT: 100% RELIABILITY
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
