import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Higher Education | Deep Focus for Researchers & Ph.D.s",
  description: "Secure your research sessions with kernel-level focus. Perfect for Ph.D. students, professors, and academic writing. Block research rabbit holes at the source.",
};

export default function HigherEdPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Academic Deep Work"
        title="Research Without"
        highlight="Interruption."
        description={
          <>
            Don't let a quick citation check turn into two hours of doomscrolling. SPB creates a <strong>hardened research environment</strong> for Ph.D.s and academics.
          </>
        }
      />
      <Comparison />
      <TechnicalHardening />
      <Solutions highlightTitle="Schools" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Deep Work for Academic Researchers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Master Your Research Sessions</h3>
              <p>
                Academic writing requires long periods of undisturbed concentration. Our <strong>research focus tool</strong> prevents the "quick search" from becoming a distraction, ensuring your citation checks stay focused and your thesis drafting remains uninterrupted.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Scholarly Focus</h3>
              <p>
                Whether you are a professor or a Ph.D. candidate, SPB provides the <strong>absolute focus</strong> needed to push the boundaries of knowledge. Eliminate digital clutter and focus on the deep intellectual work that matters most with kernel-level Windows enforcement.
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
