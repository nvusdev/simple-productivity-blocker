import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Parents | Secure Family Focus & Boundaries",
  description: "Set healthy digital boundaries without surveillance. Create focus-only profiles for homework hours with kernel-level Windows enforcement.",
};

export default function ParentsPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Family Focus"
        title="Secure Healthy"
        highlight="Boundaries."
        description={
          <>
            Stop the homework battles. SPB provides <strong>unbreakable digital guardrails</strong> to ensure focus time actually remains focus time.
          </>
        }
      />
      <Comparison />
      <Solutions highlightTitle="Parents" />
      <Installation />
      <Footer />
    </main>
  );
}
