import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Writers | Draft More, Scroll Less",
  description: "The writing partner that holds the line. Block research rabbit holes and social media during your drafting sessions with absolute concentration.",
};

export default function WritersPage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-blue-500/30 selection:text-blue-500">
      <Hero 
        badge="Creative Focus"
        title="Draft More."
        highlight="Scroll Less."
        description={
          <>
            Stop letting "research" turn into distraction. SPB provides <strong>unbreakable boundaries</strong> for authors and copywriters who need to finish that draft.
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
