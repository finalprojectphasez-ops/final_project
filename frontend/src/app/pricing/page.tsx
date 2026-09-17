"use client";

import Link from "next/link";
import { useState } from "react";

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold text-white tracking-tight">PreMock</Link>
          <div className="hidden md:flex items-center gap-8">
            <Link href="/#features" className="text-sm text-zinc-400 hover:text-white transition-colors">Features</Link>
            <Link href="/#how-it-works" className="text-sm text-zinc-400 hover:text-white transition-colors">How It Works</Link>
            <Link href="/pricing" className="text-sm text-white font-medium">Pricing</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/auth/login" className="text-sm text-zinc-400 hover:text-white transition-colors px-4 py-2">Sign In</Link>
            <Link href="/auth/signup" className="text-sm font-semibold bg-primary hover:bg-primary/90 text-white px-5 py-2.5 rounded-lg transition-all shadow-[0_0_20px_rgba(168,85,247,0.3)]">
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="pt-36 pb-12 px-6 text-center relative">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-primary/10 rounded-full blur-[140px] pointer-events-none" />
        <div className="max-w-3xl mx-auto relative z-10">
          <span className="inline-block text-xs font-semibold uppercase tracking-widest text-primary/80 mb-4 px-3 py-1 rounded-full border border-primary/20 bg-primary/5">
            Transparent Pricing
          </span>
          <h1 className="text-4xl md:text-6xl font-extrabold text-white mb-6 tracking-tight">
            Predictable Pricing for <br />
            <span className="text-gradient">Every Stage of Your Prep</span>
          </h1>
          <p className="text-zinc-400 text-lg max-w-xl mx-auto mb-8">
            Pick a plan that matches your interview timeline. Cancel or pause anytime with one click.
          </p>

          {/* Monthly / Yearly Billing Toggle */}
          <div className="inline-flex items-center gap-3 bg-zinc-900/80 p-1.5 rounded-xl border border-white/10">
            <button
              onClick={() => setBillingCycle("monthly")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                billingCycle === "monthly"
                  ? "bg-primary text-white shadow-md"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Monthly billing
            </button>
            <button
              onClick={() => setBillingCycle("yearly")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5 ${
                billingCycle === "yearly"
                  ? "bg-primary text-white shadow-md"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              Yearly billing
              <span className="text-[10px] uppercase font-bold bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full border border-green-500/30">
                Save 25%
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="px-6 pb-24 max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {/* Free Tier */}
          <div className="glass-panel rounded-2xl p-8 border border-white/10 flex flex-col justify-between hover:border-white/20 transition-all">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Starter</h2>
              <p className="text-xs text-zinc-400 mb-6">Perfect for trying out the platform</p>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-white">$0</span>
                <span className="text-sm text-zinc-400">/ forever</span>
              </div>
              <ul className="space-y-3 text-sm text-zinc-300 mb-8">
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  3 Full AI Mock Interviews
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Resume PDF Parsing
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Basic Performance Summary
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Anti-Cheat Proctoring Check
                </li>
              </ul>
            </div>
            <Link href="/auth/signup" className="w-full text-center py-3 px-4 rounded-xl border border-white/10 hover:bg-white/5 text-white text-sm font-semibold transition-all">
              Get Started Free
            </Link>
          </div>

          {/* Pro Tier (Popular) */}
          <div className="glass-panel rounded-2xl p-8 border-2 border-primary relative flex flex-col justify-between shadow-[0_0_50px_rgba(168,85,247,0.2)] hover:shadow-[0_0_60px_rgba(168,85,247,0.3)] transition-all">
            <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white text-[11px] font-bold uppercase tracking-wider py-1 px-4 rounded-full shadow-lg">
              Most Popular
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Candidate Pro</h2>
              <p className="text-xs text-zinc-400 mb-6">For active job seekers looking for mastery</p>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-white">
                  ${billingCycle === "monthly" ? "19" : "14"}
                </span>
                <span className="text-sm text-zinc-400">/ month</span>
              </div>
              <ul className="space-y-3 text-sm text-zinc-200 mb-8">
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  <strong className="text-white font-semibold">Unlimited</strong> AI Mock Interviews
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Real-Time Emotional & Eye Tracking
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Dynamic Adaptive Follow-up Questions
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Comprehensive Radar Skill Analysis
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Full Historical Trends & PDF Export
                </li>
              </ul>
            </div>
            <Link href="/auth/signup" className="w-full text-center py-3.5 px-4 rounded-xl bg-primary hover:bg-primary/90 text-white text-sm font-bold transition-all shadow-[0_0_25px_rgba(168,85,247,0.4)]">
              Upgrade to Pro
            </Link>
          </div>

          {/* Enterprise Tier */}
          <div className="glass-panel rounded-2xl p-8 border border-white/10 flex flex-col justify-between hover:border-white/20 transition-all">
            <div>
              <h2 className="text-xl font-bold text-white mb-1">Campus & Team</h2>
              <p className="text-xs text-zinc-400 mb-6">For universities, bootcamps & recruiting teams</p>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-white">
                  ${billingCycle === "monthly" ? "99" : "79"}
                </span>
                <span className="text-sm text-zinc-400">/ month</span>
              </div>
              <ul className="space-y-3 text-sm text-zinc-300 mb-8">
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Multi-Seat Student/Team Accounts
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Custom Rubrics & Questions
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Faculty Analytics Dashboard
                </li>
                <li className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-primary shrink-0" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                  Full Integrity & Anti-Cheat Logs
                </li>
              </ul>
            </div>
            <a href="mailto:contact@premock.ai" className="w-full text-center py-3 px-4 rounded-xl border border-white/10 hover:bg-white/5 text-white text-sm font-semibold transition-all">
              Contact Sales
            </a>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="px-6 pb-28 max-w-4xl mx-auto">
        <h2 className="text-3xl font-bold text-white text-center mb-12">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {[
            {
              q: "Can I try before paying anything?",
              a: "Yes! Every account comes with 3 full mock interview sessions completely free, with full AI question generation and feedback."
            },
            {
              q: "How does the webcam emotional tracking work?",
              a: "We process your video feed locally in your browser using computer vision models to estimate eye contact percentage and head pose. Your raw video is never stored or transmitted to our servers."
            },
            {
              q: "Can I cancel my subscription at any time?",
              a: "Absolutely. You can cancel your subscription with a single click in your profile settings, and you will retain access through the end of your billing cycle."
            },
            {
              q: "Do you offer discounts for students or academic institutions?",
              a: "Yes, verified students receive 40% off Pro plans, and universities can contact us for custom campus-wide bulk licensing."
            }
          ].map((item, i) => (
            <div key={i} className="glass-panel p-6 rounded-xl border border-white/10">
              <h3 className="text-white font-semibold text-base mb-2">{item.q}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{item.a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-zinc-500">
          <Link href="/" className="font-bold text-white">PreMock</Link>
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
