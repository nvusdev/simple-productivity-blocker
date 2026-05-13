"use client";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { Download, ShieldCheck } from "lucide-react";
import React from "react";

interface HeroProps {
  badge?: string;
  title?: string;
  highlight?: string;
  description?: React.ReactNode;
}

export default function Hero({
  badge = "System-Level Protection",
  title = "Secure Your",
  highlight = "Focus.",
  description = (
    <>
      They <strong>ask</strong> you to be strong every second. We provide the hardened support you need when willpower isn't enough.
    </>
  ),
}: HeroProps) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseXSpring = useSpring(x);
  const mouseYSpring = useSpring(y);

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["10deg", "-10deg"]);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-10deg", "10deg"]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const xPct = mouseX / width - 0.5;
    const yPct = mouseY / height - 0.5;

    x.set(xPct);
    y.set(yPct);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative pt-20 pb-20 overflow-hidden bg-zinc-950">
      {/* Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.05),transparent_70%)] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-8 grid grid-cols-1 md:grid-cols-2 gap-8 items-center relative z-10">
        <div className="text-left">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/5 text-blue-500 text-xs font-semibold mb-6"
          >
            <ShieldCheck size={14} /> {badge}
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-8 leading-[1.1]"
          >
            {title} <br />
            <span className="text-blue-500">{highlight}</span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-lg md:text-xl text-zinc-400 mb-10 max-w-lg leading-relaxed"
          >
            {description}
          </motion.p>

          <div className="flex flex-col sm:flex-row gap-4">
            <motion.button
              onClick={() => scrollToSection("installation")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="bg-blue-500 hover:bg-blue-600 transition-colors text-zinc-950 px-8 py-4 rounded-xl font-bold flex items-center justify-center gap-3 shadow-[0_0_20px_rgba(59,130,246,0.2)]"
            >
              <Download size={20} /> Download for Windows
            </motion.button>
            <motion.button
              onClick={() => scrollToSection("comparison")}
              whileHover={{ scale: 1.02, backgroundColor: "rgba(39, 39, 42, 0.8)" }}
              className="px-8 py-4 rounded-xl font-bold border border-zinc-800 bg-zinc-900/50 text-zinc-100 backdrop-blur-sm transition-colors"
            >
              Learn the Science
            </motion.button>
          </div>
        </div>

        <div className="relative mt-12 md:mt-0">
          <motion.div 
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{
              rotateX,
              rotateY,
              transformStyle: "preserve-3d",
            }}
            initial={{ opacity: 0, scale: 0.9, rotateY: -10 }}
            animate={{ opacity: 1, scale: 1, rotateY: 0 }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            className="relative group mx-auto max-w-md"
          >
            {/* Double-Bezel Architecture */}
            <div className="relative rounded-2xl border border-zinc-800 bg-zinc-900/40 p-2 backdrop-blur-xl shadow-2xl overflow-hidden">
               <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 overflow-hidden aspect-[16/10] relative">
                  {/* Mockup Placeholder */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center">
                    <div className="w-20 h-20 rounded-full bg-blue-500/10 flex items-center justify-center mb-4 border border-blue-500/20">
                      <ShieldCheck className="text-blue-500" size={40} />
                    </div>
                    <h3 className="text-xl font-bold mb-2">SPB Dashboard</h3>
                    <p className="text-sm text-zinc-500">Active Monitoring: Triple-Lock Suite Engaged</p>
                    
                    {/* Animated Scanning Line */}
                    <motion.div 
                      animate={{ top: ["0%", "100%", "0%"] }}
                      transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                      className="absolute left-0 right-0 h-[1px] bg-blue-500/30 blur-[2px] z-10 pointer-events-none"
                    />
                  </div>
                  
                  {/* Glass Highlights */}
                  <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 to-transparent pointer-events-none" />
               </div>
            </div>

            {/* Floating Elements for 3D depth */}
            <motion.div
              style={{ translateZ: "50px" }}
              className="absolute -top-6 -right-6 px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 shadow-xl text-xs font-mono text-blue-500"
            >
              STATUS: HARDENED
            </motion.div>
            
            <motion.div
              style={{ translateZ: "30px" }}
              className="absolute -bottom-6 -left-6 px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 shadow-xl text-xs font-mono text-zinc-400"
            >
              KERNEL_LOCK: ACTIVE
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

