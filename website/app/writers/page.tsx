import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Writers | Draft More, Scroll Less",
  description: "The writing partner that holds the line. Block research rabbit holes and social media during your drafting sessions with absolute concentration.",
  alternates: { canonical: 'https://nvus.dev/spb/writers/' },
  openGraph: { url: 'https://nvus.dev/spb/writers/' },
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
      <TechnicalHardening />
      <Solutions highlightTitle="ADHD" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Distraction-Free Writing Environment</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Finish Your Draft Faster</h3>
              <p>
                Writing requires a rare level of concentration. Our <strong>writing focus tool</strong> prevents the "research rabbit hole" by locking down distracting sites before they pull you away from your manuscript or copy. 
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Unbreakable Drafting Flow</h3>
              <p>
                Whether you are a novelist, journalist, or technical writer, SPB provides the <strong>absolute focus</strong> needed to get words on the page. Stop the cycle of editing and start shipping finished work with hardened Windows distraction blocking.
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
