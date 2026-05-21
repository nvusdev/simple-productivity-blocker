import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Professionals | Unbreakable Corporate Focus",
  description: "Eliminate doomscrolling in the office. Secure your work blocks with hardened Windows enforcement. Perfect for project managers, analysts, and corporate leaders.",
  alternates: { canonical: 'https://nvus.dev/spb/professionals/' },
  openGraph: { url: 'https://nvus.dev/spb/professionals/' },
};

export default function ProfessionalsPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Corporate Productivity"
        title="Unbreakable"
        highlight="Office Focus."
        description={
          <>
            Bridge the gap between your goals and your browser. SPB provides the <strong>hardened enforcement</strong> needed to stay productive in high-distraction environments.
          </>
        }
      />
      <Comparison />
      <TechnicalHardening />
      <Solutions highlightTitle="Professionals" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">High-Performance Office Productivity</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Block Workplace Distractions</h3>
              <p>
                In a high-stakes corporate environment, focus is your competitive advantage. Our <strong>professional focus tool</strong> eliminates doomscrolling and impulsive news checking, ensuring your work blocks remain sacred and productive.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Remote Work Support</h3>
              <p>
                Working from home presents unique distractions. SPB provides the <strong>hardened digital boundaries</strong> needed to separate work time from leisure. Secure your output and reclaim your time with system-level enforcement for Windows.
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
