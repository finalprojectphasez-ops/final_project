"use client";

import React from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = React.use(params);
    const skills = [
        { label: "Technical Depth", score: 85, color: "bg-blue-500" },
        { label: "Communication", score: 80, color: "bg-purple-500" },
        { label: "Confidence", score: 88, color: "bg-green-500" },
        { label: "Problem Solving", score: 76, color: "bg-orange-500" },
        { label: "Clarity", score: 82, color: "bg-cyan-500" },
    ];

    const timeline = [
        { time: "0:00", confidence: 60, stress: 45 },
        { time: "2:00", confidence: 70, stress: 50 },
        { time: "4:00", confidence: 65, stress: 60 },
        { time: "6:00", confidence: 80, stress: 40 },
        { time: "8:00", confidence: 85, stress: 35 },
        { time: "10:00", confidence: 75, stress: 55 },
        { time: "12:00", confidence: 90, stress: 30 },
    ];

    return (
        <div className="min-h-screen bg-background text-foreground">
            <div className="flex">
                <Sidebar active="reports" />

                <main className="flex-1 p-8">
                    <div className="max-w-5xl mx-auto space-y-8">

                        {/* Header */}
                        <div className="flex justify-between items-end pb-6 border-b border-white/10">
                            <div>
                                <Link href="/dashboard" className="text-sm text-zinc-500 hover:text-white transition-colors mb-3 block">← Back to Dashboard</Link>
                                <h1 className="text-3xl font-bold text-white">Interview Report</h1>
                                <p className="text-zinc-400 mt-1">Full Stack Engineer • Hard • Aug 16, 2026</p>
                            </div>
                            <div className="text-right">
                                <p className="text-zinc-500 text-sm mb-1">Overall Score</p>
                                <span className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">88</span>
                                <span className="text-zinc-500 text-2xl">/100</span>
                            </div>
                        </div>

                        {/* Score Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {[
                                { label: "Technical", score: 85, icon: "🎯", color: "border-blue-500/30 text-blue-400" },
                                { label: "Communication", score: 80, icon: "💬", color: "border-purple-500/30 text-purple-400" },
                                { label: "Confidence", score: "High", icon: "💪", color: "border-green-500/30 text-green-400" },
                                { label: "Violations", score: 0, icon: "🛡️", color: "border-zinc-500/30 text-zinc-400" },
                            ].map((c, i) => (
                                <div key={i} className={`glass-panel p-5 rounded-2xl border-t-2 ${c.color.split(" ")[0]}`}>
                                    <div className="text-2xl mb-3">{c.icon}</div>
                                    <div className={`text-2xl font-black ${c.color.split(" ")[1]} mb-1`}>{c.score}{typeof c.score === "number" && c.label !== "Violations" ? "%" : ""}</div>
                                    <div className="text-zinc-400 text-xs">{c.label}</div>
                                </div>
                            ))}
                        </div>

                        {/* Skill Bars */}
                        <div className="glass-panel rounded-2xl p-8">
                            <h2 className="text-lg font-bold text-white mb-6">Skill Breakdown</h2>
                            <div className="space-y-5">
                                {skills.map((s, i) => (
                                    <div key={i}>
                                        <div className="flex justify-between text-sm mb-2">
                                            <span className="text-zinc-300 font-medium">{s.label}</span>
                                            <span className="text-white font-bold">{s.score}%</span>
                                        </div>
                                        <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden">
                                            <div className={`h-full ${s.color} rounded-full transition-all`} style={{ width: `${s.score}%` }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Confidence Timeline (CSS-based) */}
                        <div className="glass-panel rounded-2xl p-8">
                            <h2 className="text-lg font-bold text-white mb-6">Confidence vs Stress Timeline</h2>
                            <div className="flex items-end gap-3 h-32">
                                {timeline.map((t, i) => (
                                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                                        <div className="w-full flex gap-0.5 items-end" style={{ height: "80px" }}>
                                            <div className="flex-1 bg-primary/60 rounded-t transition-all" style={{ height: `${t.confidence}%` }} title={`Confidence: ${t.confidence}%`} />
                                            <div className="flex-1 bg-red-500/50 rounded-t transition-all" style={{ height: `${t.stress}%` }} title={`Stress: ${t.stress}%`} />
                                        </div>
                                        <span className="text-zinc-600 text-xs">{t.time}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="flex gap-4 mt-4">
                                <div className="flex items-center gap-2 text-xs text-zinc-400"><div className="w-3 h-3 rounded-sm bg-primary/60" /> Confidence</div>
                                <div className="flex items-center gap-2 text-xs text-zinc-400"><div className="w-3 h-3 rounded-sm bg-red-500/50" /> Stress</div>
                            </div>
                        </div>

                        {/* Feedback */}
                        <div className="glass-panel rounded-2xl p-8">
                            <h2 className="text-lg font-bold text-white mb-6">AI Feedback & Recommendations</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-3">
                                    <h3 className="text-green-400 font-semibold flex items-center gap-2">✅ Strengths</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        <li className="flex gap-2"><span className="text-green-400 shrink-0">•</span>Excellent Zustand vs Context API trade-off explanation.</li>
                                        <li className="flex gap-2"><span className="text-green-400 shrink-0">•</span>Maintained consistent eye contact, strong presence.</li>
                                        <li className="flex gap-2"><span className="text-green-400 shrink-0">•</span>Confident articulation on cloud deployment strategies.</li>
                                    </ul>
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-red-400 font-semibold flex items-center gap-2">⚠️ Areas to Improve</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        <li className="flex gap-2"><span className="text-red-400 shrink-0">•</span>Filler word usage slightly above benchmark (3/min avg).</li>
                                        <li className="flex gap-2"><span className="text-red-400 shrink-0">•</span>Pacing dropped during the database sharding question.</li>
                                        <li className="flex gap-2"><span className="text-red-400 shrink-0">•</span>Lacked depth on Postgres partitioning vs manual sharding.</li>
                                    </ul>
                                </div>
                            </div>
                            <div className="mt-6 pt-6 border-t border-white/5 text-sm text-zinc-400">
                                <span className="text-white font-semibold">Verdict: </span>
                                Strong candidate with exceptional frontend knowledge. Minor gaps in advanced DB architecture theory. Overall pass threshold achieved — well done!
                            </div>
                        </div>

                        <div className="flex gap-4 pb-8">
                            <Link href="/dashboard" className="flex-1 py-3 text-center glass-panel rounded-xl text-white hover:bg-white/10 transition-colors font-medium">
                                ← Back to Dashboard
                            </Link>
                            <Link href="/interview/new" className="flex-1 py-3 text-center bg-primary hover:bg-primary/90 rounded-xl text-white font-semibold transition-all">
                                Retry Interview →
                            </Link>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
