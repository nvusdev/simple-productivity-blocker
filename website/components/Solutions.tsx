"use client";
import { motion } from "framer-motion";
import { GraduationCap, Users, Briefcase, Heart, AppWindow, Globe, FolderLock, Zap, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

const solutions = [
  {
    title: "Schools & Labs",
    description: "Secure exam environments and computer labs with absolute control. Prevent students from bypassing browser blocks.",
    icon: GraduationCap,
    className: "md:col-span-2 md:row-span-1",
    color: "bg-blue-500/10 border-blue-500/20 text-blue-500",
    href: "/students/",
  },
  {
    title: "Supportive Parents",
    description: "Set healthy boundaries without surveillance. Create focus-only profiles for homework hours.",
    icon: Users,
    className: "md:col-span-1 md:row-span-1",
    color: "bg-purple-500/10 border-purple-500/20 text-purple-500",
    href: "/parents/",
  },
  {
    title: "Professionals",
    description: "Block 'doomscrolling' at the source. Lock in for deep work sessions that actually move the needle.",
    icon: Briefcase,
    className: "md:col-span-1 md:row-span-1",
    color: "bg-blue-500/10 border-blue-500/20 text-blue-500",
    href: "/professionals/",
  },
  {
    title: "ADHD & Personal",
    description: "A digital partner that holds the line when willpower fades. Hardened support for neurodivergent focus.",
    icon: Heart,
    className: "md:col-span-2 md:row-span-1",
    color: "bg-rose-500/10 border-rose-500/20 text-rose-500",
    href: "/adhd/",
  }
];

const features = [
  { icon: Globe, title: "DNS-Level Website Filtering", text: "Blocks connections before they happen." },
  { icon: AppWindow, title: "Strict Process Termination", text: "Forces distractive apps to close." },
  { icon: FolderLock, title: "NTFS Hardened Access", text: "Restricts access to specific folders." },
  { icon: Zap, title: "Battery-Aware", text: "Zero-drain background operation." },
];

interface SolutionsProps {
  highlightTitle?: string;
}

export default function Solutions({ highlightTitle }: SolutionsProps) {
  return (
    <section className="py-20 bg-zinc-950 relative overflow-hidden">
      <div className="max-w-6xl mx-auto px-8 relative z-10">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-16 gap-12">
          <div className="max-w-2xl">
            <h2 className="text-4xl md:text-5xl font-bold mb-6">Built for Every Goal.</h2>
            <p className="text-zinc-400 text-lg">
              Whether you're managing a classroom, a household, or your own 
              <strong> entrepreneurial focus</strong>, SPB adapts to your mission.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
             {features.map((f, i) => (
               <div key={i} className="flex items-start gap-3 text-sm text-zinc-500 font-medium">
                 <f.icon size={20} className="text-blue-500 shrink-0 mt-0.5" />
                 <div>
                   <span className="text-zinc-300 block mb-0.5">{f.title}</span>
                   <span className="text-xs text-zinc-500">{f.text}</span>
                 </div>
               </div>
             ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[240px]">
          {solutions.map((s, i) => {
            const isHighlighted = s.title.toLowerCase().includes(highlightTitle?.toLowerCase() || "");
            
            return (
              <Link 
                key={i} 
                href={s.href}
                className={cn(
                  "group relative rounded-3xl border p-8 overflow-hidden transition-all duration-500 block",
                  isHighlighted 
                    ? "border-blue-500/50 bg-blue-500/5 shadow-[0_0_30px_rgba(59,130,246,0.1)] ring-1 ring-blue-500/20" 
                    : "border-zinc-800 bg-zinc-900/40 hover:border-blue-500/30 hover:bg-zinc-900/60",
                  s.className
                )}
              >
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  viewport={{ once: true }}
                >
                  <div className={cn("inline-flex p-3 rounded-2xl mb-6 border", s.color)}>
                    <s.icon size={24} />
                  </div>
                  <h3 className="text-2xl font-bold mb-3 flex items-center gap-2 group-hover:text-blue-400 transition-colors">
                    {s.title}
                    <ArrowRight size={20} className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                  </h3>
                  <p className="text-zinc-400 leading-relaxed text-sm max-w-[280px] md:max-w-none">
                    {s.description}
                  </p>
                  
                  {/* Decorative Corner Glow */}
                  <div className={cn(
                    "absolute -bottom-8 -right-8 w-24 h-24 blur-[40px] transition-opacity", 
                    isHighlighted ? "opacity-30" : "opacity-0 group-hover:opacity-20",
                    s.color
                  )} />
                </motion.div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

