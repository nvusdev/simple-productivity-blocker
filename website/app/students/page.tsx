import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Students | Focus on Finals, Not Your Feed",
  description: "The hardened Windows blocker for student success. Lock down distractions during exam prep and essay writing. Absolute concentration for K-12 and university students.",
  alternates: { canonical: 'https://nvus.dev/spb/students/' },
  openGraph: { url: 'https://nvus.dev/spb/students/' },
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
      <TechnicalHardening />
      <Solutions highlightTitle="Schools" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">The Best Way to Focus While Studying</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Exam Productivity Tools</h3>
              <p>
                When finals approach, willpower often fails. Our <strong>system-level distraction blocker</strong> for students ensures that your browser and apps stay closed until your study timer is up. Unlike simple browser extensions, SPB cannot be bypassed by simply opening a new private window.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Lock Down Study Sessions</h3>
              <p>
                Whether you are writing a Ph.D. thesis or studying for high school SATs, maintaining a deep work state is critical. SPB helps you <strong>avoid procrastination</strong> by enforcing absolute digital boundaries, making it the perfect productivity companion for Windows users in academia.
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
