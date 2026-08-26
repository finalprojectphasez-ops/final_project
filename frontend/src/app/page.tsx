"use client";

import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">

      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="text-xl font-bold text-white tracking-tight">PreMock</span>
          <div className="hidden md:flex items-center gap-8">
            {["Features", "How It Works", "Pricing"].map(l => (
              <a key={l} href={`#${l.toLowerCase().replace(/ /g, "-")}`} className="text-sm text-zinc-400 hover:text-white transition-colors">{l}</a>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="text-sm text-zinc-400 hover:text-white transition-colors px-4 py-2">Sign In</Link>
            <Link href="/auth/signup" className="text-sm font-semibold bg-primary hover:bg-primary/90 text-white px-5 py-2.5 rounded-lg transition-all shadow-[0_0_20px_rgba(168,85,247,0.3)]">
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="pt-40 pb-28 px-6 relative text-center">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-primary/10 rounded-full blur-[140px] pointer-events-none" />
        <div className="max-w-4xl mx-auto relative z-10">

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Ace Your Next<br />
            <span className="text-gradient">Technical Interview</span>
          </h1>
          <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Practice with an AI that reads your resume, adapts to your answers, tracks your emotions, and gives you brutal honest feedback — just like a real hiring manager.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/auth/signup" className="px-8 py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl text-base transition-all shadow-[0_0_40px_rgba(168,85,247,0.4)] hover:scale-105">
              Start Practicing Free →
            </Link>
            <Link href="#features" className="px-8 py-4 glass-panel text-white font-semibold rounded-xl text-base hover:bg-white/10 transition-all">
              See How It Works
            </Link>
          </div>
          <p className="text-zinc-600 text-sm mt-6">No credit card required • 3 free interviews</p>
        </div>
      </section>

      {/* Mock Interview UI Preview */}
      <section className="px-6 pb-28">
        <div className="max-w-5xl mx-auto">
          <div className="glass-panel rounded-2xl border border-white/10 overflow-hidden shadow-[0_0_80px_rgba(168,85,247,0.1)]">
            <div className="h-10 border-b border-white/5 flex items-center px-4 gap-2 bg-black/60">
              <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
              <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
              <span className="ml-3 text-zinc-500 text-xs">premock.ai — Live Interview Session</span>
            </div>
            <div className="p-8 md:p-12 flex flex-col md:flex-row gap-8 items-center bg-gradient-to-br from-black/60 to-zinc-900/60">
              <div className="w-full md:w-1/2 aspect-video bg-zinc-900 rounded-xl overflow-hidden relative border border-white/5">
                <div className="absolute inset-0 bg-cover bg-center opacity-60" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=1000&auto=format&fit=crop')" }} />
                <div className="absolute inset-x-0 bottom-0 p-4 flex gap-2 justify-between items-end">
                  <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded border border-green-500/30 backdrop-blur-md">Eye Contact: 92%</span>
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded border border-blue-500/30 backdrop-blur-md">Confidence: High</span>
                  <div className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30 backdrop-blur-md">
                    <div className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse"></div> LIVE
                  </div>
                </div>
              </div>
              <div className="w-full md:w-1/2 flex flex-col gap-4">
                <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-sm text-zinc-300">
                  <span className="text-primary font-bold block mb-2">AI Interviewer</span>
                  I noticed you mentioned building a scalable platform with Next.js. Can you walk me through how you managed state across 10,000+ concurrent users?
                </div>
                <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 text-sm text-zinc-100 ml-6">
                  <span className="text-white font-bold block mb-2">You (Live Transcript)</span>
                  We opted for React Query for server state and Zustand for global UI state to minimize unnecessary re-renders across components...
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 pb-28">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block text-xs font-semibold uppercase tracking-widest text-primary/80 mb-4 px-3 py-1 rounded-full border border-primary/20 bg-primary/5">Platform Features</span>
            <h2 className="text-4xl font-bold text-white mb-4">Everything You Need to Land the Job</h2>
            <p className="text-zinc-400 max-w-xl mx-auto">PreMock is the only platform with real-time emotional intelligence baked into every interview.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {[
              {
                title: "Resume-Aware AI",
                desc: "Questions are generated directly from your uploaded resume. No generic content — only role-specific, personalized grilling.",
                color: "from-violet-500/10 to-transparent border-violet-500/20",
                iconBg: "bg-violet-500/15",
                iconColor: "text-violet-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>,
              },
              {
                title: "Emotional Tracking",
                desc: "Real-time webcam analysis measures eye contact, stress spikes, and confidence score throughout the entire session.",
                color: "from-blue-500/10 to-transparent border-blue-500/20",
                iconBg: "bg-blue-500/15",
                iconColor: "text-blue-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" /></svg>,
              },
              {
                title: "Anti-Cheat Proctoring",
                desc: "Fullscreen lock, focus detection, tab-switch tracking, and filler-word counting to simulate real exam conditions.",
                color: "from-emerald-500/10 to-transparent border-emerald-500/20",
                iconBg: "bg-emerald-500/15",
                iconColor: "text-emerald-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>,
              },
              {
                title: "Live Transcription",
                desc: "Powered by Deepgram's nova-2 model, your speech is transcribed in under 300ms with full filler word detection.",
                color: "from-orange-500/10 to-transparent border-orange-500/20",
                iconBg: "bg-orange-500/15",
                iconColor: "text-orange-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" /></svg>,
              },
              {
                title: "Detailed Reports",
                desc: "After every session, receive a full breakdown with skill radar, confidence timeline, and specific areas to improve.",
                color: "from-cyan-500/10 to-transparent border-cyan-500/20",
                iconBg: "bg-cyan-500/15",
                iconColor: "text-cyan-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>,
              },
              {
                title: "Dynamic Follow-ups",
                desc: "If you lack depth, the AI immediately pivots with a harder follow-up question targeting exactly your weak spots.",
                color: "from-rose-500/10 to-transparent border-rose-500/20",
                iconBg: "bg-rose-500/15",
                iconColor: "text-rose-400",
                icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>,
              },
            ].map((f, i) => (
              <div key={i} className={`group relative rounded-2xl p-6 bg-gradient-to-br ${f.color} border backdrop-blur-sm hover:-translate-y-1 transition-all duration-300 overflow-hidden`}
                style={{ background: "rgba(12,12,16,0.7)" }}>
                {/* Subtle top-border accent */}
                <div className={`absolute top-0 left-6 right-6 h-px bg-gradient-to-r ${f.color.split(" ")[0].replace("from-", "from-").replace("/10", "/60")} to-transparent`} />
                <div className={`w-10 h-10 rounded-xl ${f.iconBg} ${f.iconColor} flex items-center justify-center mb-5 border border-white/5`}>
                  {f.icon}
                </div>
                <h3 className="text-base font-semibold text-white mb-2 tracking-tight">{f.title}</h3>
                <p className="text-zinc-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* How It Works */}
      <section id="how-it-works" className="px-6 pb-28 bg-white/[0.02]">
        <div className="max-w-4xl mx-auto py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">How It Works</h2>
          </div>
          <div className="space-y-10">
            {[
              { num: "01", title: "Upload Your Resume", desc: "Our AI parses your PDF and extracts your tech stack, projects, and experience to build a custom question set." },
              { num: "02", title: "Configure Your Session", desc: "Pick your target role (Frontend, Backend, DevOps, etc.) and difficulty (Easy to Hard). Go live instantly." },
              { num: "03", title: "Interviewed in Real-Time", desc: "The AI conducts your interview via text — you respond via microphone. Deepgram transcribes your voice live." },
              { num: "04", title: "Get Your Report", desc: "Receive a comprehensive analytics report with technical score, emotional insights, and actionable improvement tips." },
            ].map((s, i) => (
              <div key={i} className="flex gap-8 items-start">
                <div className="text-6xl font-black text-primary/20 shrink-0 w-16 leading-none">{s.num}</div>
                <div className="pt-2">
                  <h3 className="text-xl font-bold text-white mb-2">{s.title}</h3>
                  <p className="text-zinc-400 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-28">
        <div className="max-w-3xl mx-auto text-center glass-panel rounded-3xl p-14 border border-primary/20 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent pointer-events-none" />
          <h2 className="text-4xl font-bold text-white mb-4 relative z-10">Ready to Practice Like a Pro?</h2>
          <p className="text-zinc-400 mb-8 relative z-10">Join thousands of engineers acing their interviews with PreMock.</p>
          <Link href="/auth/signup" className="relative z-10 inline-block px-10 py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl text-lg transition-all shadow-[0_0_50px_rgba(168,85,247,0.5)] hover:scale-105">
            Start Free — No Credit Card
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-zinc-500">
          <span className="font-bold text-white">PreMock</span>
          <span>© 2026 PreMock. All rights reserved.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
