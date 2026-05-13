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
      <Installation />
      <Footer />
    </main>
  );
}
