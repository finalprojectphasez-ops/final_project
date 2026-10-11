"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { supabase } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: _id } = React.use(params);
    const router = useRouter();
    const [sessionData, setSessionData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!_id) return;
        supabase
            .from("interview_sessions")
            .select("*")
            .eq("id", _id)
            .single()
            .then(({ data, error }) => {
                if (error || !data) {
                    const errStr = error ? `Code: ${error.code}, Message: ${error.message}, Details: ${error.details}` : "No data found";
                    console.error("Error fetching session:", errStr);
                    setSessionData({ _error: errStr });
                } else {
                    setSessionData(data);
                }
                setLoading(false);
            });
    }, [_id]);

    if (loading) {
        return (
            <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
                <div className="flex gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
            </div>
        );
    }

    if (!sessionData || sessionData._error) {
        return (
            <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center space-y-4">
                <h1 className="text-2xl font-bold text-white">Report Not Found</h1>
                {sessionData?._error && <p className="text-red-400 text-sm max-w-lg text-center p-4 bg-red-500/10 border border-red-500/20 rounded-xl">{sessionData._error}</p>}
                <Link href="/dashboard" className="px-4 py-2 bg-white/10 hover:bg-white/15 rounded-xl text-white text-sm transition-colors">
                    Return to Dashboard
                </Link>
            </div>
        );
    }

    const skills = [
        { label: "Technical Depth", score: sessionData.technical_score || 0, color: "bg-blue-500" },
        { label: "Communication", score: sessionData.communication_score || 0, color: "bg-purple-500" },
        { label: "Answer Relevance", score: sessionData.answer_relevance || 0, color: "bg-cyan-500" },
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

    const strengths = sessionData.strengths || [];
    const weaknesses = sessionData.weaknesses || [];
    const improvements = sessionData.improvement_suggestions || [];
    const questionFeedback = sessionData.question_feedback || [];

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
                                <p className="text-zinc-400 mt-1">
                                    {sessionData.role} • {sessionData.difficulty} • {new Date(sessionData.created_at).toLocaleDateString()}
                                </p>
                            </div>
                            <div className="text-right">
                                <p className="text-zinc-500 text-sm mb-1">Overall Score</p>
                                <span className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-400">
                                    {sessionData.overall_score || 0}
                                </span>
                                <span className="text-zinc-500 text-2xl">/100</span>
                            </div>
                        </div>

                        {/* Score Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {[
                                { label: "Technical", score: sessionData.technical_score || 0, icon: "🎯", color: "border-blue-500/30 text-blue-400" },
                                { label: "Communication", score: sessionData.communication_score || 0, icon: "💬", color: "border-purple-500/30 text-purple-400" },
                                { label: "Relevance", score: sessionData.answer_relevance || 0, icon: "💡", color: "border-cyan-500/30 text-cyan-400" },
                                { label: "Violations", score: sessionData.violations || 0, icon: "🛡️", color: "border-zinc-500/30 text-zinc-400" },
                            ].map((c, i) => (
                                <div key={i} className={`glass-panel p-5 rounded-2xl border-t-2 ${c.color.split(" ")[0]}`}>
                                    <div className="text-2xl mb-3">{c.icon}</div>
                                    <div className={`text-2xl font-black ${c.color.split(" ")[1]} mb-1`}>{c.score}{typeof c.score === "number" && c.label !== "Violations" ? "%" : ""}</div>
                                    <div className="text-zinc-400 text-xs">{c.label}</div>
                                </div>
                            ))}
                        </div>

                        {/* 2-Column Grid for Skills and Emotion Analysis */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
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

                            {/* Emotion & Attention Analysis */}
                            <div className="glass-panel rounded-2xl p-8">
                                <h2 className="text-lg font-bold text-white mb-6">Emotion & Attention Analysis</h2>
                                <div className="space-y-6">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                            <div className="text-zinc-400 text-xs mb-1 uppercase tracking-wider font-semibold">Eye Contact</div>
                                            <div className="text-2xl font-bold text-emerald-400">{sessionData.eye_contact != null ? `${sessionData.eye_contact}%` : "N/A"}</div>
                                        </div>
                                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                            <div className="text-zinc-400 text-xs mb-1 uppercase tracking-wider font-semibold">Face Present</div>
                                            <div className="text-2xl font-bold text-blue-400">{sessionData.face_present != null ? `${sessionData.face_present}%` : "N/A"}</div>
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <div className="text-xs uppercase tracking-wider font-semibold text-zinc-500 mb-4">Expression Breakdown</div>
                                        <div className="space-y-3">
                                            {[
                                                { label: "Neutral", value: sessionData.neutral_expr, color: "bg-zinc-400" },
                                                { label: "Happy", value: sessionData.happy_expr, color: "bg-green-400" },
                                                { label: "Sad", value: sessionData.sad_expr, color: "bg-blue-400" },
                                                { label: "Angry", value: sessionData.angry_expr, color: "bg-red-400" },
                                                { label: "Disgust", value: sessionData.disgust_expr, color: "bg-purple-400" },
                                                { label: "Fear", value: sessionData.fear_expr, color: "bg-amber-400" },
                                                { label: "Surprise", value: sessionData.surprise_expr, color: "bg-cyan-400" },
                                            ].map((emo, i) => (
                                                <div key={i} className="flex items-center gap-3">
                                                    <span className="w-24 text-xs font-medium text-zinc-300 truncate">{emo.label}</span>
                                                    <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                        <div className={`h-full ${emo.color} rounded-full`} style={{ width: `${emo.value ?? 0}%` }} />
                                                    </div>
                                                    <span className="w-10 text-right text-xs font-bold text-white">
                                                        {emo.value != null ? `${emo.value}%` : "N/A"}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Feedback */}
                        <div className="glass-panel rounded-2xl p-8">
                            <h2 className="text-lg font-bold text-white mb-6">AI Feedback & Recommendations</h2>
                            
                            <div className="mb-6 pt-2 pb-6 border-b border-white/5 text-sm text-zinc-300 leading-relaxed">
                                <span className="text-white font-semibold text-base mb-2 block">General Feedback:</span>
                                {sessionData.general_feedback || "No general feedback available."}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-3">
                                    <h3 className="text-green-400 font-semibold flex items-center gap-2">✅ Strengths</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        {strengths.length > 0 ? strengths.map((s: string, i: number) => (
                                            <li key={i} className="flex gap-2"><span className="text-green-400 shrink-0">•</span>{s}</li>
                                        )) : <li className="text-zinc-500 italic">No specific strengths recorded.</li>}
                                    </ul>
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-red-400 font-semibold flex items-center gap-2">⚠️ Areas to Improve</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        {weaknesses.length > 0 ? weaknesses.map((w: string, i: number) => (
                                            <li key={i} className="flex gap-2"><span className="text-red-400 shrink-0">•</span>{w}</li>
                                        )) : <li className="text-zinc-500 italic">No specific weaknesses recorded.</li>}
                                    </ul>
                                </div>
                            </div>
                        </div>

                        {/* Detailed Q&A Feedback */}
                        {questionFeedback.length > 0 && (
                            <div className="glass-panel rounded-2xl p-8">
                                <h2 className="text-lg font-bold text-white mb-6">Detailed Q&A Breakdown</h2>
                                <div className="space-y-6">
                                    {questionFeedback.map((qf: any, i: number) => (
                                        <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-5">
                                            <div className="flex justify-between items-start gap-4 mb-3">
                                                <h3 className="text-zinc-200 font-medium leading-relaxed">
                                                    <span className="text-primary font-bold mr-2">Q{i+1}:</span>
                                                    {qf.question}
                                                </h3>
                                                <div className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 border border-white/10">
                                                    <span className="text-xs text-zinc-400">Score:</span>
                                                    {qf.score !== null && qf.score !== undefined ? (
                                                        <span className={`text-sm font-bold ${qf.score >= 80 ? 'text-green-400' : qf.score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                            {qf.score}/100
                                                        </span>
                                                    ) : (
                                                        <span className="text-sm font-bold text-zinc-500">N/A</span>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="mb-4">
                                                <div className="text-xs text-zinc-500 uppercase tracking-wider font-semibold mb-1">Your Answer:</div>
                                                <p className="text-sm text-zinc-400 whitespace-pre-wrap pl-3 border-l-2 border-white/10">{qf.answer || "(No answer recorded)"}</p>
                                            </div>
                                            {qf.score === null || qf.score === undefined ? (
                                                <div className="bg-white/5 border border-white/10 rounded-lg p-4 text-center">
                                                    <p className="text-sm text-zinc-500 italic">Evaluation unavailable</p>
                                                </div>
                                            ) : (
                                                <>
                                                    <div className="bg-primary/10 border border-primary/20 rounded-lg p-3">
                                                        <div className="text-xs text-primary uppercase tracking-wider font-semibold mb-1">Feedback:</div>
                                                        <p className="text-sm text-zinc-300">{qf.feedback}</p>
                                                    </div>
                                            {qf.strengths && qf.strengths.length > 0 && (
                                                <div className="mt-4">
                                                    <div className="text-xs text-green-400 uppercase tracking-wider font-semibold mb-1">Strengths:</div>
                                                    <ul className="text-sm text-zinc-400 space-y-1">
                                                        {qf.strengths.map((s: string, idx: number) => (
                                                            <li key={idx} className="flex gap-2">
                                                                <span className="text-green-400 shrink-0">•</span>{s}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            {qf.improvements && qf.improvements.length > 0 && (
                                                <div className="mt-4">
                                                    <div className="text-xs text-red-400 uppercase tracking-wider font-semibold mb-1">Improvements:</div>
                                                    <ul className="text-sm text-zinc-400 space-y-1">
                                                        {qf.improvements.map((s: string, idx: number) => (
                                                            <li key={idx} className="flex gap-2">
                                                                <span className="text-red-400 shrink-0">•</span>{s}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                                </>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <div className="flex gap-4 pb-8">
                            <Link href="/dashboard" className="flex-1 py-3 text-center glass-panel rounded-xl text-white hover:bg-white/10 transition-colors font-medium">
                                ← Back to Dashboard
                            </Link>
                            <Link href="/interview/new" className="flex-1 py-3 text-center bg-primary hover:bg-primary/90 rounded-xl text-white font-semibold transition-all">
                                Try Another Interview →
                            </Link>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}

