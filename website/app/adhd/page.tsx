import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "ADHD Support | Hardened Neurodivergent Focus",
  description: "The digital partner that holds the line when willpower fades. Hardened Windows support for ADHD minds. Secure your focus with the Triple-Lock suite.",
};

export default function ADHDPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Neurodivergent Support"
        title="Hardened Support for"
        highlight="ADHD Minds."
        description={
          <>
            Stop fighting your own tools. SPB provides the <strong>digital guardrails</strong> needed to keep your focus where it belongs, even when willpower isn't enough.
          </>
        }
      />
      <Comparison />
      <Solutions highlightTitle="ADHD" />
      
      <section className="py-24 border-t border-zinc-900 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Executive Function Support for ADHD</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Digital Guardrails for Concentration</h3>
              <p>
                Willpower is a finite resource. For those with ADHD, digital distractions can be overwhelming. SPB acts as an external <strong>executive function support</strong>, holding the line on your focus when your internal filters are exhausted.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Focus Suite</h3>
              <p>
                Our <strong>ADHD productivity tool</strong> for Windows uses system-level enforcement to prevent impulsive browser hopping. By creating absolute digital boundaries, SPB helps you stay on task and reduces the friction of starting difficult projects.
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
