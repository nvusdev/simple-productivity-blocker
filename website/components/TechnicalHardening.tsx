"use client";
import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Network, FileText, Sparkles, ShieldCheck, Terminal as TerminalIcon } from "lucide-react";

interface LogLine {
  text: string;
  type: "info" | "success" | "warn" | "error" | "cmd";
  timestamp: string;
}

const terminalLogs: Record<string, LogLine[]> = {
  default: [
    { text: "Initializing SPB Security Subsystem...", type: "info", timestamp: "17:50:31" },
    { text: "system_status: ACTIVE [Kernel-Enforcement Mode]", type: "success", timestamp: "17:50:31" },
    { text: "Listening for focus session triggers...", type: "info", timestamp: "17:50:32" },
    { text: "Ready. Click a hardened component card to inspect operations.", type: "cmd", timestamp: "17:50:32" }
  ],
  "triple-lock": [
    { text: "spb_daemon.exe -> request: enforce_group_locks('DeepWork')", type: "cmd", timestamp: "18:02:11" },
    { text: "Acquiring win32file exclusive lock on target binaries...", type: "info", timestamp: "18:02:11" },
    { text: "CreateFileW(C:\\Program Files\\Slack\\slack.exe, GENERIC_READ, 0, NULL) -> SUCCESS [File Handle Locked]", type: "success", timestamp: "18:02:12" },
    { text: "Applying NTFS Discretionary Access Control Lists (DACL)...", type: "info", timestamp: "18:02:12" },
    { text: "SetNamedSecurityInfoW(C:\\Users\\User\\Documents\\Confidential, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, SID:Everyone, ACCESS:DENIED) -> SUCCESS [NTFS ACL Blocked]", type: "success", timestamp: "18:02:13" },
    { text: "Enforcement level: 100% (Kernel-level block active)", type: "success", timestamp: "18:02:13" }
  ],
  "dns-redundancy": [
    { text: "spb_daemon.exe -> audit: website_protection_status", type: "cmd", timestamp: "18:03:02" },
    { text: "Initializing local DNS proxy server on 127.0.0.1:53...", type: "info", timestamp: "18:03:02" },
    { text: "Local DNS proxy listening successfully.", type: "success", timestamp: "18:03:03" },
    { text: "Warning: High-priority bypass vector detected (Firefox custom DoH settings).", type: "warn", timestamp: "18:03:03" },
    { text: "Hardening browser configurations via Registry overrides...", type: "info", timestamp: "18:03:04" },
    { text: "Writing hosts file mirroring rules (YouTube, Discord, Spotify)...", type: "info", timestamp: "18:03:04" },
    { text: "Hosts file synchronization complete. 48 domains locked.", type: "success", timestamp: "18:03:05" }
  ],
  "atomic-recovery": [
    { text: "spb_daemon.exe -> transaction: checkpoint_state", type: "cmd", timestamp: "18:04:15" },
    { text: "Serializing active locks and adapter metrics...", type: "info", timestamp: "18:04:15" },
    { text: "Writing backup snapshot to programdata\\SimpleProductivityBlocker\\recovery.tmp...", type: "info", timestamp: "18:04:16" },
    { text: "Calling win32file.FlushFileBuffers() -> fsync complete [Disk Committed]", type: "success", timestamp: "18:04:16" },
    { text: "Executing atomic file swap: recovery.tmp -> recovery_history.json...", type: "info", timestamp: "18:04:17" },
    { text: "Transaction committed. State is fully crash-proof.", type: "success", timestamp: "18:04:17" }
  ],
  "and-more": [
    { text: "spb_daemon.exe -> query: list_auxiliary_systems", type: "cmd", timestamp: "18:07:01" },
    { text: "Checking Transactional LIFO Lifecycle rollback stack... OK.", type: "success", timestamp: "18:07:01" },
    { text: "Auditing modular background resource consumption...", type: "info", timestamp: "18:07:02" },
    { text: "Active memory usage: 8.4 MB | CPU usage: < 0.01% [Pruned Release Build]", type: "success", timestamp: "18:07:02" },
    { text: "Local Safe-Mode standby state monitoring: ACTIVE", type: "info", timestamp: "18:07:03" },
    { text: "Telemetry state: 100% Host-local. No cloud sync requested.", type: "success", timestamp: "18:07:03" }
  ]
};

const cards = [
  {
    id: "triple-lock",
    title: "Triple-Lock Suite",
    icon: Lock,
    description: "Operates at the OS-level using exclusive win32file handles, Registry policy overrides, and native NTFS Access Control Lists (ACLs) to block binary execution and lock down files.",
    color: "from-blue-500/20 to-cyan-500/20 border-blue-500/30 text-blue-400"
  },
  {
    id: "dns-redundancy",
    title: "Dual-Layer Redundancy",
    icon: Network,
    description: "Intercepts website requests via a lightweight local DNS proxy, automatically backed by native system hosts-file mirroring to block DoH and browser proxy bypass loops.",
    color: "from-purple-500/20 to-indigo-500/20 border-purple-500/30 text-purple-400"
  },
  {
    id: "atomic-recovery",
    title: "Atomic Recovery Log",
    icon: FileText,
    description: "Leverages a local write-ahead log backed by fsync operations and atomic file swaps. Prevents data corruption and ensures state restoration even after sudden power failures.",
    color: "from-rose-500/20 to-pink-500/20 border-rose-500/30 text-rose-400"
  },
  {
    id: "and-more",
    title: "And so much more...",
    icon: Sparkles,
    description: "Features transactional installer lifecycles with LIFO rollback, dormant Safe Mode standby, low-latency background execution (8.4MB, <0.01% CPU), and strictly local privacy telemetry.",
    color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400"
  }
];

export default function TechnicalHardening() {
  const [activeTab, setActiveTab] = useState<string>("default");
  const [logs, setLogs] = useState<LogLine[]>([]);
  const terminalContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Populate logs with transition effect
    const activeLogs = terminalLogs[activeTab] || [];
    setLogs([]);
    
    let currentLogIndex = 0;
    const interval = setInterval(() => {
      if (currentLogIndex < activeLogs.length) {
        const logItem = activeLogs[currentLogIndex];
        if (logItem) {
          setLogs(prev => [...prev, logItem]);
        }
        currentLogIndex++;
      } else {
        clearInterval(interval);
      }
    }, 120);

    return () => clearInterval(interval);
  }, [activeTab]);

  useEffect(() => {
    if (terminalContainerRef.current) {
      terminalContainerRef.current.scrollTop = terminalContainerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <section id="technical-hardening" className="py-24 bg-zinc-950 relative overflow-hidden">
      {/* Background radial glows */}
      <div className="absolute top-1/2 left-1/3 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/5 blur-[120px] pointer-events-none rounded-full" />
      <div className="absolute bottom-10 right-1/4 w-[500px] h-[500px] bg-purple-500/5 blur-[150px] pointer-events-none rounded-full" />

      <div className="max-w-6xl mx-auto px-8 relative z-10">
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-500 text-xs font-semibold mb-6"
          >
            <ShieldCheck size={14} /> Low-Level Hardening
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
            Under the Hood. <span className="text-blue-500">Uncompromising.</span>
          </h2>
          <p className="text-zinc-400 text-lg max-w-3xl mx-auto leading-relaxed">
            SPB is built for absolute resilience. Unlike browser-bound blockers, we design and enforce rules directly at the native Windows system level, locking bypass paths while ensuring robust transactional recovery.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* Feature List */}
          <div className="lg:col-span-5 flex flex-col gap-4 justify-between">
            {cards.map((card) => {
              const isActive = activeTab === card.id;
              
              return (
                <button
                  key={card.id}
                  onClick={() => setActiveTab(card.id)}
                  className={`text-left p-5 rounded-2xl border transition-all duration-300 relative group overflow-hidden ${
                    isActive 
                      ? `bg-zinc-900 border-zinc-700 shadow-lg scale-[1.02] ring-1 ring-zinc-800`
                      : "bg-zinc-950 border-zinc-900/50 hover:bg-zinc-900/40 hover:border-zinc-800"
                  }`}
                >
                  {/* Left accent indicator */}
                  <div className={`absolute left-0 top-0 bottom-0 w-[3px] transition-transform duration-300 ${
                    isActive ? "bg-blue-500 scale-y-100" : "bg-transparent scale-y-0"
                  }`} />

                  <div className="flex gap-4">
                    <div className={`p-2.5 rounded-xl border shrink-0 flex items-center justify-center transition-colors bg-zinc-900/50 ${
                      isActive ? card.color : "border-zinc-800 text-zinc-500"
                    }`}>
                      <card.icon size={20} />
                    </div>
                    <div>
                      <h3 className={`text-base font-bold mb-1 transition-colors ${
                        isActive ? "text-zinc-100" : "text-zinc-300 group-hover:text-zinc-100"
                      }`}>
                        {card.title}
                      </h3>
                      <p className="text-xs text-zinc-500 leading-relaxed max-w-md">
                        {card.description}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Real-time Interactive Terminal Console */}
          <div className="lg:col-span-7 flex flex-col">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950 flex flex-col overflow-hidden h-full min-h-[460px] shadow-2xl relative">
              
              {/* Terminal Title Bar */}
              <div className="bg-zinc-900/90 border-b border-zinc-800 px-5 py-3.5 flex justify-between items-center shrink-0">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
                  <span className="text-xs font-mono font-semibold text-zinc-400 ml-3 tracking-wider flex items-center gap-1.5">
                    <TerminalIcon size={12} className="text-blue-500" />
                    SPB_HARDENED_SHELL v1.4.10
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-tighter">
                    active_view: {activeTab.toUpperCase()}
                  </span>
                  {activeTab !== "default" && (
                    <button 
                      onClick={() => setActiveTab("default")}
                      className="text-[10px] font-mono text-blue-500 hover:underline hover:text-blue-400"
                    >
                      Clear Log
                    </button>
                  )}
                </div>
              </div>

              {/* Terminal Output */}
              <div ref={terminalContainerRef} className="p-6 font-mono text-xs overflow-y-auto grow space-y-4 max-h-[380px] scrollbar-thin select-text">
                <AnimatePresence mode="popLayout">
                  {logs.map((log, index) => {
                    if (!log) return null;
                    let textClass = "text-zinc-400";
                    let prefix = "[*]";
                    
                    if (log.type === "success") {
                      textClass = "text-emerald-400";
                      prefix = "[✓]";
                    } else if (log.type === "warn") {
                      textClass = "text-amber-400 font-semibold";
                      prefix = "[!]";
                    } else if (log.type === "error") {
                      textClass = "text-rose-500 font-semibold";
                      prefix = "[✗]";
                    } else if (log.type === "cmd") {
                      textClass = "text-blue-400 font-medium";
                      prefix = "spb >";
                    }

                    return (
                      <motion.div
                        key={`${activeTab}-${index}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="flex gap-3 items-start leading-relaxed border-b border-zinc-900/40 pb-2 last:border-0"
                      >
                        <span className="text-zinc-600 select-none shrink-0 font-medium">{log.timestamp}</span>
                        <span className="text-zinc-600 select-none shrink-0 font-bold">{prefix}</span>
                        <span className={`${textClass} break-all whitespace-pre-wrap`}>{log.text}</span>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>

              {/* Glowing Console Grid Mask */}
              <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] pointer-events-none bg-[length:100%_4px,3px_100%] opacity-20" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
