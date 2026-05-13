import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Students | Focus on Finals, Not Your Feed",
  description: "The hardened Windows blocker for student success. Lock down distractions during exam prep and essay writing. Absolute concentration for K-12 and university students.",
};

export default function StudentsPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Academic Excellence"
        title="Focus on Finals."
        highlight="Not Your Feed."
        description={
          <>
            Stop the "just five minutes" loop. SPB provides the <strong>hardened support</strong> students need to survive exam season and finish that essay.
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
