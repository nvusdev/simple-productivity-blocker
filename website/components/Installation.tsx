"use client";
import { motion } from "framer-motion";
import { Download, FolderOpen, ShieldAlert, Settings } from "lucide-react";

const steps = [
  {
    title: "Download",
    description: "Get the latest system-level build directly from our GitHub repository.",
    icon: Download,
    details: "Supports Windows 10 & 11 (x64)",
  },
  {
    title: "Extract",
    description: "Unzip the archive to a permanent folder on your local drive.",
    icon: FolderOpen,
    details: "No complex installer required",
  },
  {
    title: "Deploy",
    description: "Run the main application as Administrator to initialize kernel locks.",
    icon: ShieldAlert,
    details: "Admin rights required for enforcement",
  },
  {
    title: "Secure",
    description: "Configure your blocklists and engage the Triple-Lock suite.",
    icon: Settings,
    details: "Start your focus session instantly",
  }
];

export default function Installation() {
  return (
    <section className="py-32 bg-zinc-950/50">
      <div className="container mx-auto px-6">
        <div className="text-center mb-24">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Simple to Deploy.</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Setting up SPB takes less than two minutes. No bloat, no sign-ups, just absolute focus.
          </p>
        </div>

        <div className="relative max-w-5xl mx-auto">
          {/* Connecting Line (Desktop) */}
          <div className="absolute top-1/2 left-0 w-full h-[1px] bg-zinc-800 -translate-y-1/2 hidden md:block" />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-12 relative z-10">
            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                viewport={{ once: true }}
                className="flex flex-col items-center text-center group"
              >
                <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-8 group-hover:border-emerald-500/50 group-hover:bg-emerald-500/5 transition-all shadow-xl relative">
                  <step.icon className="text-zinc-400 group-hover:text-emerald-500 transition-colors" size={28} />
                  
                  {/* Step Number Badge */}
                  <div className="absolute -top-3 -right-3 w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-bold text-zinc-500">
                    0{i + 1}
                  </div>
                </div>
                
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-zinc-500 text-sm leading-relaxed mb-4">
                  {step.description}
                </p>
                <div className="text-[10px] font-mono text-emerald-500/60 uppercase tracking-tighter">
                  {step.details}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="mt-24 text-center">
          <motion.a
            href="https://github.com/nvusdev/simple-productivity-blocker/releases/latest"
            target="_blank"
            rel="noopener noreferrer"
            whileHover={{ scale: 1.02 }}
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-emerald-500 transition-colors text-sm font-medium border-b border-zinc-800 hover:border-emerald-500/50 pb-1"
          >
            View Installation Docs on GitHub
          </motion.a>
        </div>
      </div>
    </section>
  );
}
