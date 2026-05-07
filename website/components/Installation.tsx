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
    <section id="installation" className="py-24 bg-zinc-950/50">
      <div className="max-w-6xl mx-auto px-8">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Simple to Deploy.</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Setting up SPB takes less than two minutes. No bloat, no sign-ups, just absolute focus.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 max-w-5xl mx-auto mb-20">
          {steps.map((step, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              viewport={{ once: true }}
              className="flex flex-col items-center text-center group"
            >
              <div className="w-16 h-16 shrink-0 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-6 group-hover:border-blue-500/50 group-hover:bg-blue-500/5 transition-all shadow-xl relative">
                <step.icon className="text-zinc-400 group-hover:text-blue-500 transition-colors" size={28} />
                
                {/* Step Number Badge */}
                <div className="absolute -top-3 -right-3 w-7 h-7 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-[10px] font-bold text-zinc-500">
                  0{i + 1}
                </div>
              </div>
              
              <h3 className="text-xl font-bold mb-3">{step.title}</h3>
              <p className="text-zinc-500 text-sm leading-relaxed mb-4 grow">
                {step.description}
              </p>
              <div className="text-[10px] font-mono text-blue-500/60 uppercase tracking-tighter">
                {step.details}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="text-center flex flex-col items-center justify-center gap-6">
          <motion.a
            href="https://github.com/nvusdev/simple-productivity-blocker/releases/latest/download/SimpleProductivityBlocker.zip"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="bg-zinc-100 text-zinc-950 hover:bg-white px-8 py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-colors max-w-sm w-full shadow-lg"
          >
            <Download size={20} /> Download Latest .zip
          </motion.a>

          <motion.a
            href="https://github.com/nvusdev/simple-productivity-blocker#installation"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-zinc-400 hover:text-blue-500 transition-colors text-sm font-medium border-b border-zinc-800 hover:border-blue-500/50 pb-1"
          >
            Read Full Installation Guide on GitHub
          </motion.a>
        </div>
      </div>
    </section>
  );
}

