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
      
      <section className="py-24 border-t border-zinc-900 bg-zinc-950/50">
        <div className="max-w-4xl mx-auto px-8">
          <h2 className="text-3xl font-bold mb-8 text-zinc-100">Healthy Screen Time for Families</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 text-zinc-400 leading-relaxed">
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Secure Homework Boundaries</h3>
              <p>
                Maintaining a distraction-free environment for homework can be a constant battle. Our <strong>parental focus tool</strong> for Windows creates absolute digital boundaries, ensuring that computers remain tools for learning during school hours rather than gateways to games and social media.
              </p>
            </div>
            <div>
              <h3 className="text-xl font-semibold mb-4 text-blue-400">Hardened Educational Support</h3>
              <p>
                SPB provides the <strong>digital guardrails</strong> families need to foster healthy tech habits. By enforcing focus blocks that cannot be easily bypassed, parents can trust that homework time is actually being spent on schoolwork, reducing friction and improving academic success.
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
