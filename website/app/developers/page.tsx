import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Developers | Code Deep, Ship Fast",
  description: "The focus suite for high-performance engineering. Block social media during sprints and keep your flow state unbroken with kernel-level enforcement.",
};

export default function DevelopersPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Engineering Focus"
        title="Code Deep."
        highlight="Ship Fast."
        description={
          <>
            Protect your flow state from the "quick check" of Hacker News or Reddit. SPB is <strong>system-level armor</strong> for developers who value deep work.
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
