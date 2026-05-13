import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
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
      <Solutions highlightTitle="Schools" />
      <Installation />
      <Footer />
    </main>
  );
}
