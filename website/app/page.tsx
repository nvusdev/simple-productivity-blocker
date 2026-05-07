import Hero from "@/components/Hero";
import Comparison from "@/components/Comparison";
import Solutions from "@/components/Solutions";
import Installation from "@/components/Installation";

export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-emerald-500/30 selection:text-emerald-500">
      <Hero />
      <Comparison />
      <Solutions />
      <Installation />
      {/* Other sections will be added here */}
    </main>
  );
}
