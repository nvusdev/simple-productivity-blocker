import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Professionals | Unbreakable Corporate Focus",
  description: "Eliminate doomscrolling in the office. Secure your work blocks with hardened Windows enforcement. Perfect for project managers, analysts, and corporate leaders.",
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
      <Solutions highlightTitle="Professionals" />
      <Installation />
      <Footer />
    </main>
  );
}
