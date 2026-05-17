"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Download, FolderOpen, ShieldAlert, Settings, Trash2, ShieldCheck } from "lucide-react";

const steps = [
  {
    title: "Download",
    description: "Get the native installer executable directly from our GitHub release page.",
    icon: Download,
    details: "spb_setup.exe (82.4 MB)",
  },
  {
    title: "Install",
    description: "Run the setup wizard to compile and configure system pathways silently.",
    icon: FolderOpen,
    details: "Nullsoft NSIS Setup Wizard",
  },
  {
    title: "Deploy",
    description: "Run the desktop dashboard to register rules and security descriptors.",
    icon: ShieldCheck,
    details: "Admin rights required for enforcement",
  },
  {
    title: "Secure",
    description: "Engage Triple-Lock enforcement and active scheduled filtering.",
    icon: Settings,
    details: "Start your focus session instantly",
  }
];

export default function Installation() {
  const [latestReleaseUrl, setLatestReleaseUrl] = useState("https://github.com/nvusdev/simple-productivity-blocker/releases/latest/download/spb_setup.exe");

  useEffect(() => {
    async function fetchLatestRelease() {
      try {
        const response = await fetch("https://api.github.com/repos/nvusdev/simple-productivity-blocker/releases/latest");
        const data = await response.json();
        const asset = data.assets.find((a: any) => a.name.endsWith(".exe"));
        if (asset) {
          setLatestReleaseUrl(asset.browser_download_url);
        }
      } catch (error) {
        console.error("Failed to fetch latest release:", error);
      }
    }
    fetchLatestRelease();
  }, []);

  return (
    <section id="installation" className="py-20 bg-zinc-950/50">
      <div className="max-w-6xl mx-auto px-8">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Simple to Deploy.</h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Setting up SPB takes less than two minutes. No bloat, no sign-ups, just absolute focus.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 max-w-6xl mx-auto mb-20">
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

        <div className="max-w-4xl mx-auto bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 md:p-12 mb-20 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <ShieldCheck size={120} />
          </div>
          
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-2xl font-bold mb-6 flex items-center gap-3">
                <Download className="text-blue-500" /> Get the Latest Build
              </h3>
              <p className="text-zinc-400 text-sm mb-8 leading-relaxed">
                Download the native, highly-compressed setup wizard. The compiled installer registers custom system services, security descriptors, and policy overrides safely.
              </p>
              <motion.a
                href={latestReleaseUrl}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="bg-zinc-100 text-zinc-950 hover:bg-white px-8 py-4 rounded-xl font-bold flex items-center justify-center gap-3 transition-colors shadow-lg"
              >
                <Download size={20} /> Download Latest Installer
              </motion.a>
              <p className="text-zinc-600 text-[10px] mt-4 text-center">
                Always fetches the most recent release from GitHub
              </p>
            </div>
            
            <div className="bg-zinc-950/50 rounded-2xl p-6 border border-zinc-800/50">
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-500/80">
                <Trash2 size={18} /> Safe Uninstallation
              </h4>
              <p className="text-zinc-500 text-xs leading-relaxed mb-4">
                SPB takes system modifications seriously. To remove the software safely:
              </p>
              <ul className="space-y-3 text-xs text-zinc-400">
                <li className="flex gap-2">
                  <span className="text-blue-500 font-bold">•</span>
                  <span>Use standard <strong>Windows Add/Remove Programs</strong> or run <strong>uninstall.exe</strong> in the installation folder.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-blue-500 font-bold">•</span>
                  <span>The uninstaller runs in safe temporary workspace to release file locks and sweep folders completely.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-blue-500 font-bold">•</span>
                  <span>Restores all system DNS configurations, hosts buffers, and file permissions to default.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

