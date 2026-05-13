import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
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
      <Solutions highlightTitle="Entrepreneurs" />
      <Installation />
      <Footer />
    </main>
  );
}
