import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Entrepreneurs | Absolute Focus for Solo-Founders",
  description: "Protect your most valuable asset: your time. SPB provides kernel-level Windows focus for entrepreneurs and solo-founders who need to ship.",
};

export default function EntrepreneursPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Founders Focus"
        title="Absolute Focus for"
        highlight="Solo-Founders."
        description={
          <>
            When you're the entire team, focus is your only leverage. SPB is the <strong>hardened partner</strong> that keeps you locked into what actually matters.
          </>
        }
      />
      <Comparison />
      <TechnicalHardening />
      <Solutions highlightTitle="Entrepreneurs" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Absolute Focus for High-Stakes Founders</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Maximize Your Most Valuable Asset</h3>
              <p>
                For entrepreneurs, time is more than money—it's your survival. Our <strong>founder productivity tool</strong> helps you reclaim hours lost to mindless scrolling and unproductive tabs, ensuring that your energy is focused on building, shipping, and scaling.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Discipline for Solo-Founders</h3>
              <p>
                When you are the boss, no one is watching your screen. SPB provides the <strong>hardened digital discipline</strong> needed to stay on track. By creating absolute digital boundaries, you can ensure your focus remains on high-leverage activities that grow your business.
              </p>
            </div>
          </div>
        </div>
      </section>

      <Installation />
      <Footer />
    </main>
  );
}
