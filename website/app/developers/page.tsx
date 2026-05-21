import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import TechnicalHardening from "@/components/TechnicalHardening";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";
import Footer from "@/components/Footer";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "For Developers | Code Deep, Ship Fast",
  description: "The focus suite for high-performance engineering. Block social media during sprints and keep your flow state unbroken with kernel-level enforcement.",
  alternates: { canonical: 'https://nvus.dev/spb/developers/' },
  openGraph: { url: 'https://nvus.dev/spb/developers/' },
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
      <TechnicalHardening />
      <Solutions highlightTitle="Professionals" />
      
      <section className="py-24 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Deep Work for Software Engineers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Master Your Coding Flow</h3>
              <p>
                As a developer, your value is tied to your ability to solve complex problems. Our <strong>coding focus tool</strong> ensures that you stay in the zone during critical sprints by blocking access to distractions like Hacker News, Reddit, and YouTube at the system level.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Sprint Support</h3>
              <p>
                Browser extensions are too easy to disable. SPB provides <strong>unbreakable digital boundaries</strong> that respect your flow state. It is the perfect companion for developers who need to ship high-quality code without the constant pull of social media.
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
