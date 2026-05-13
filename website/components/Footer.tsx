"use client";
import { motion } from "framer-motion";
import Link from "next/link";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="py-12 border-t border-zinc-900 bg-zinc-950">
      <div className="max-w-6xl mx-auto px-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 mb-12">
          <div>
            <Link href="/" className="group">
              <h3 className="text-xl font-bold text-zinc-100 mb-2 group-hover:text-blue-500 transition-colors">Simple Productivity Blocker</h3>
            </Link>
            <p className="text-zinc-500 text-sm max-w-xs">
              Absolute Focus for the Modern World. A hardened, system-level focus suite for Windows.
            </p>
          </div>
          
          <div className="flex flex-col items-start md:items-end gap-2">
            <span className="text-zinc-400 text-sm font-medium">Built with passion by nvusdev</span>
            <div className="flex items-center gap-4 text-xs text-zinc-600">
              <a href="https://github.com/nvusdev/simple-productivity-blocker" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">GitHub</a>
              <a href="https://github.com/nvusdev/simple-productivity-blocker/releases" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">Releases</a>
              <a href="https://github.com/nvusdev/simple-productivity-blocker/issues" target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 transition-colors">Support</a>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-zinc-900/50 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-zinc-600 text-xs">
            © {currentYear} Simple Productivity Blocker. All rights reserved.
          </p>
          
          <div className="flex items-center gap-2 text-zinc-500 text-[10px] uppercase tracking-widest font-mono">
            <span className="w-1 h-1 rounded-full bg-blue-500/50"></span>
            Disclaimer: System-Level Enforcement Tool. Use Responsibly.
          </div>
        </div>
      </div>
    </footer>
  );
}
