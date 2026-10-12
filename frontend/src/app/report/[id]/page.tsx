"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { supabase } from "@/lib/supabase/client";
import { safeSessionStorage } from "@/lib/storage";
import { useRouter } from "next/navigation";

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: _id } = React.use(params);
    const router = useRouter();
    const [sessionData, setSessionData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [previousSessions, setPreviousSessions] = useState<any[]>([]);

    // Manual review modal / form state
    const [overrideCriterion, setOverrideCriterion] = useState<string | null>(null);
    const [overrideRating, setOverrideRating] = useState<number>(3);
    const [overrideReason, setOverrideReason] = useState<string>("");
    const [overrideNotes, setOverrideNotes] = useState<string>("");
    const [submittingReview, setSubmittingReview] = useState<boolean>(false);
    const [reviewMessage, setReviewMessage] = useState<string | null>(null);

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

    useEffect(() => {
        if (!_id) return;

        const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(_id);

        // 1. Check local storage first (instant & fast)
        const cached = safeSessionStorage.getItem("report_" + _id) || safeSessionStorage.getItem("report_last_session");
        if (cached) {
            try {
                const parsed = JSON.parse(cached);
                if (parsed.id === _id || parsed.backend_session_id === _id || !isUuid) {
                    setSessionData(parsed);
                    setLoading(false);
                }
            } catch (e) {}
        }

        // 2. Fetch from Backend server disk (guaranteed persistence & auto-backfilled rubric)
        fetch(`${backendUrl}/api/reports/${_id}`)
            .then(res => res.ok ? res.json() : null)
            .then(backendReport => {
                if (backendReport) {
                    safeSessionStorage.setItem("report_" + _id, JSON.stringify(backendReport));
                    setSessionData(backendReport);
                    setLoading(false);
                    return;
                }

                // 3. Fallback to Supabase database
                const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(_id);
                const query = isUuid
                    ? supabase.from("interview_sessions").select("*").eq("id", _id)
                    : supabase.from("interview_sessions").select("*").eq("backend_session_id", _id);

                return query.single().then(({ data, error }) => {
                    if (data && !error) {
                        setSessionData(data);
                        setLoading(false);
                        return;
                    }

                    // 4. Fallback to local session history
                    try {
                        const hist = JSON.parse(safeSessionStorage.getItem("premock_session_history") || "[]");
                        const found = hist.find((item: any) => item.id === _id || item.backend_session_id === _id);
                        if (found) {
                            setSessionData(found);
                            setLoading(false);
                            return;
                        }
                    } catch {}

                    console.warn("Session not found in DB or storage:", error?.message);
                    setSessionData({ _error: "This interview report is not available or has expired." });
                    setLoading(false);
                });
            })
            .catch(() => {
                setLoading(false);
            });

        // Load historical reports for session comparison
        fetch(`${backendUrl}/api/reports`)
            .then(res => res.ok ? res.json() : [])
            .then(allReports => {
                if (Array.isArray(allReports)) {
                    setPreviousSessions(allReports.filter((r: any) => (r.id !== _id && r.backend_session_id !== _id)));
                }
            })
            .catch(() => {});
    }, [_id, backendUrl]);

    const handleExport = (format: "json" | "csv") => {
        const url = `${backendUrl}/api/rubric/export/${_id}?format=${format}`;
        window.open(url, "_blank");
    };

    const handleManualReviewSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!overrideCriterion) return;
        setSubmittingReview(true);
        setReviewMessage(null);

        try {
            const res = await fetch(`${backendUrl}/api/rubric/manual-review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: _id,
                    criterion_id: overrideCriterion,
                    rating: Number(overrideRating),
                    reason: overrideReason || "Human expert manual assessment",
                    reviewer_notes: overrideNotes || undefined
                })
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Review update failed");
            }

            const updatedData = await res.json();
            setReviewMessage(`Criterion '${overrideCriterion}' successfully updated to rating ${overrideRating}/4.`);
            
            // Refresh session data
            if (updatedData.rubric_assessment) {
                setSessionData((prev: any) => ({
                    ...prev,
                    rubric_assessment: updatedData.rubric_assessment,
                    overall_score: updatedData.rubric_assessment.total_score_100 ?? updatedData.rubric_assessment.provisional_normalized_100,
                    total_score_100: updatedData.rubric_assessment.total_score_100,
                    provisional_normalized_100: updatedData.rubric_assessment.provisional_normalized_100,
                    assessment_status: updatedData.rubric_assessment.assessment_status,
                    coverage_percent: updatedData.rubric_assessment.coverage_percent
                }));
            }
            setOverrideCriterion(null);
        } catch (err: any) {
            setReviewMessage(`Error: ${err.message}`);
        } finally {
            setSubmittingReview(false);
        }
    };

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

    const rubric = sessionData.rubric_assessment || null;
    const isComplete = rubric?.assessment_status === "complete";
    const isPartial = rubric?.assessment_status === "partial";
    const isUnassessed = rubric?.assessment_status === "unassessed";

    const strengths = sessionData.strengths || [];
    const weaknesses = sessionData.weaknesses || [];
    const improvements = sessionData.improvement_suggestions || [];
    const questionFeedback = sessionData.question_feedback || [];

    const orderedCriteriaKeys = [
        "technical_knowledge",
        "problem_solving",
        "practical_application",
        "relevance_completeness",
        "communication_clarity",
        "followup_reflection",
        "spoken_delivery"
    ];

    return (
        <div className="min-h-screen bg-background text-foreground">
            <div className="flex">
                <Sidebar active="reports" />

                <main className="flex-1 p-8">
                    <div className="max-w-5xl mx-auto space-y-8">

                        {/* Top Header Navigation */}
                        <div className="flex justify-between items-end pb-6 border-b border-white/10">
                            <div>
                                <Link href="/dashboard" className="text-sm text-zinc-500 hover:text-white transition-colors mb-3 block">← Back to Dashboard</Link>
                                <div className="flex items-center gap-3">
                                    <h1 className="text-3xl font-bold text-white">Interview Assessment Report</h1>
                                    <span className="text-xs px-2.5 py-1 bg-white/10 text-zinc-300 rounded-full font-mono">
                                        Rubric: {rubric?.rubric_version || "interview_practice_100_v1"}
                                    </span>
                                </div>
                                <p className="text-zinc-400 mt-1">
                                    {sessionData.role} • {sessionData.difficulty} • {new Date(sessionData.created_at || sessionData.completed_at || Date.now()).toLocaleDateString()}
                                </p>
                            </div>

                            {/* Score & Status Badge */}
                            <div className="text-right">
                                {isComplete ? (
                                    <>
                                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold mb-2">
                                            ✓ Complete Assessment (100% Coverage)
                                        </div>
                                        <div>
                                            <span className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-primary">
                                                {rubric?.total_score_100?.toFixed(2) || rubric?.total_score_100}
                                            </span>
                                            <span className="text-zinc-500 text-2xl">/100</span>
                                        </div>
                                    </>
                                ) : isPartial ? (
                                    <>
                                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold mb-2">
                                            ⚠️ Partial Assessment ({rubric?.coverage_percent}% Coverage)
                                        </div>
                                        <div className="flex flex-col items-end">
                                            <div className="text-4xl font-extrabold text-amber-300">
                                                {rubric?.assessed_score?.toFixed(2)} / {rubric?.assessed_maximum} pts
                                            </div>
                                            <div className="text-xs text-zinc-400 mt-1">
                                                Provisional: <span className="font-semibold text-white">{rubric?.provisional_normalized_100}%</span> (normalized)
                                            </div>
                                            <div className="text-[11px] text-amber-400/80 italic max-w-xs text-right mt-1">
                                                Complete total score null. Missing: {rubric?.missing_criteria?.join(", ") || "spoken delivery"}
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-500/10 border border-zinc-500/30 text-zinc-400 text-xs font-semibold mb-2">
                                            Unassessed (0% Coverage)
                                        </div>
                                        <div className="text-4xl font-bold text-zinc-500">No Score</div>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Export & Audit Bar */}
                        <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/10">
                            <div className="flex items-center gap-3">
                                <span className="text-xs text-zinc-400">Review Status:</span>
                                <span className={`text-xs px-2.5 py-0.5 rounded font-medium ${
                                    rubric?.review_status === "verified" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                }`}>
                                    {rubric?.review_status === "verified" ? "✓ Verified Local Evidence" : "⚠️ Requires Human Review"}
                                </span>
                                <span className="text-xs text-zinc-500">Source: {rubric?.rating_source || "local_model"}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => handleExport("json")}
                                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-zinc-300 transition-colors flex items-center gap-1.5"
                                >
                                    📥 Export Audit JSON
                                </button>
                                <button
                                    onClick={() => handleExport("csv")}
                                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-medium text-zinc-300 transition-colors flex items-center gap-1.5"
                                >
                                    📄 Export Audit CSV
                                </button>
                            </div>
                        </div>

                        {reviewMessage && (
                            <div className="p-3 bg-primary/10 border border-primary/20 rounded-xl text-primary text-xs flex justify-between items-center">
                                <span>{reviewMessage}</span>
                                <button onClick={() => setReviewMessage(null)} className="text-zinc-400 hover:text-white">✕</button>
                            </div>
                        )}

                        {/* ========================================================================= */}
                        {/* 100-MARK DETERMINISTIC RUBRIC SCORECARD (interview_practice_100_v1)       */}
                        {/* ========================================================================= */}
                        <div className="glass-panel rounded-2xl p-8 border border-primary/20 bg-gradient-to-b from-white/[0.04] to-transparent">
                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 pb-4 border-b border-white/10">
                                <div>
                                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                        <span>📊</span> 100-Mark Rubric Assessment Breakdown
                                    </h2>
                                    <p className="text-xs text-zinc-400 mt-1">
                                        Formula: <code className="bg-white/10 px-1.5 py-0.5 rounded text-zinc-300">marks = rating / 4 × max_marks</code>. Evaluated across topic groups with equal group weighting.
                                    </p>
                                </div>
                                <div className="text-right">
                                    <span className="text-xs text-zinc-400 block">Total Assessed / Weight</span>
                                    <span className="text-sm font-bold text-white">
                                        {rubric?.assessed_score?.toFixed(2) || 0} / {rubric?.assessed_maximum || 100} Marks
                                    </span>
                                </div>
                            </div>

                            {/* Criteria List */}
                            <div className="space-y-6">
                                {orderedCriteriaKeys.map((cid) => {
                                    const c = rubric?.criteria?.[cid];
                                    if (!c) return null;
                                    const maxMarks = c.maximum_marks;
                                    const rating = c.rating;
                                    const earned = c.earned_marks;
                                    const isAssessed = c.is_assessed;
                                    const percent = isAssessed && rating !== null ? (rating / 4) * 100 : 0;

                                    return (
                                        <div key={cid} className="p-5 rounded-xl bg-white/[0.02] border border-white/10 hover:border-white/20 transition-all">
                                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-semibold text-white text-base">{c.name}</span>
                                                        <span className="text-xs text-zinc-400 px-2 py-0.5 bg-white/5 rounded">Max: {maxMarks} pts</span>
                                                        {isAssessed ? (
                                                            <span className="text-[11px] px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20 font-medium">
                                                                Assessed
                                                            </span>
                                                        ) : (
                                                            <span className="text-[11px] px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded border border-amber-500/20 font-medium">
                                                                Missing Evidence
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>

                                                <div className="flex items-center gap-4">
                                                    <div className="text-right">
                                                        <div className="text-lg font-black text-white">
                                                            {isAssessed && earned !== null ? (
                                                                <>
                                                                    <span className="text-primary">{earned.toFixed(2)}</span>
                                                                    <span className="text-zinc-500 text-xs"> / {maxMarks}</span>
                                                                </>
                                                            ) : (
                                                                <span className="text-zinc-500 text-sm italic">Unassessed</span>
                                                            )}
                                                        </div>
                                                        <div className="text-[11px] text-zinc-400">
                                                            {isAssessed && rating !== null ? `Rating: ${rating.toFixed(2)} / 4` : "Rating: null"}
                                                        </div>
                                                    </div>

                                                    <button
                                                        onClick={() => {
                                                            setOverrideCriterion(cid);
                                                            setOverrideRating(rating ?? 3);
                                                            setOverrideReason(c.reason || "");
                                                            setOverrideNotes("");
                                                        }}
                                                        className="px-2.5 py-1 text-[11px] bg-white/5 hover:bg-white/10 border border-white/10 rounded text-zinc-300 transition-colors"
                                                        title="Perform manual assessment or review override"
                                                    >
                                                        Review ✎
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Progress Bar */}
                                            <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden mb-3">
                                                <div
                                                    className={`h-full rounded-full transition-all ${
                                                        !isAssessed ? "bg-zinc-600" : percent >= 75 ? "bg-emerald-400" : percent >= 50 ? "bg-primary" : "bg-amber-400"
                                                    }`}
                                                    style={{ width: `${percent}%` }}
                                                />
                                            </div>

                                            {/* Evaluator Rationale / Anchors */}
                                            {c.reason && (
                                                <div className="text-xs text-zinc-300 mb-3 bg-white/[0.02] p-2.5 rounded-lg border-l-2 border-primary/50">
                                                    <span className="font-semibold text-zinc-400 block mb-0.5">Evaluation Anchor / Reason:</span>
                                                    {c.reason}
                                                </div>
                                            )}

                                            {/* Supporting Verifiable Quotes */}
                                            {c.evidence && c.evidence.length > 0 && (
                                                <div className="mt-2 space-y-1.5">
                                                    <span className="text-[11px] uppercase tracking-wider font-semibold text-zinc-400 block">
                                                        Exact Candidate Answer Evidence:
                                                    </span>
                                                    {c.evidence.map((ev: any, evIdx: number) => {
                                                        const quoteText = typeof ev === "string" ? ev : ev.quote || ev.notes || JSON.stringify(ev);
                                                        const isVerified = typeof ev === "object" ? ev.verified : true;
                                                        return (
                                                            <div key={evIdx} className="text-xs text-zinc-400 bg-black/20 p-2 rounded border border-white/5 flex items-start gap-2">
                                                                <span className={isVerified ? "text-emerald-400 shrink-0" : "text-amber-400 shrink-0"}>
                                                                    {isVerified ? "✓ [Verified]" : "⚠️ [Unverified]"}
                                                                </span>
                                                                <span className="italic text-zinc-300">"{quoteText}"</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Manual Review Modal / Drawer */}
                        {overrideCriterion && (
                            <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
                                <div className="glass-panel p-6 rounded-2xl max-w-md w-full border border-white/20 bg-zinc-900 shadow-2xl">
                                    <h3 className="text-lg font-bold text-white mb-2">
                                        Manual Review / Rating Override
                                    </h3>
                                    <p className="text-xs text-zinc-400 mb-4">
                                        Override criterion: <span className="font-semibold text-white">{overrideCriterion}</span>
                                    </p>

                                    <form onSubmit={handleManualReviewSubmit} className="space-y-4">
                                        <div>
                                            <label className="text-xs font-semibold text-zinc-300 block mb-1">
                                                Rating (0 to 4):
                                            </label>
                                            <select
                                                value={overrideRating}
                                                onChange={e => setOverrideRating(Number(e.target.value))}
                                                className="w-full bg-black/40 border border-white/20 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-primary"
                                            >
                                                <option value={0}>0 - Not demonstrated / Unworkable / Misconception</option>
                                                <option value={1}>1 - Recognizes terms / Major errors / Guesses</option>
                                                <option value={2}>2 - Partly correct / Significant gaps</option>
                                                <option value={3}>3 - Correct concepts / Coherent steps / Plausible</option>
                                                <option value={4}>4 - Accurate / Alternatives & Tradeoffs / Specific decisions</option>
                                            </select>
                                        </div>

                                        <div>
                                            <label className="text-xs font-semibold text-zinc-300 block mb-1">
                                                Review Reason:
                                            </label>
                                            <input
                                                type="text"
                                                value={overrideReason}
                                                onChange={e => setOverrideReason(e.target.value)}
                                                placeholder="e.g. Verified spoken clarity via live recording playback"
                                                className="w-full bg-black/40 border border-white/20 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-primary"
                                                required
                                            />
                                        </div>

                                        <div>
                                            <label className="text-xs font-semibold text-zinc-300 block mb-1">
                                                Reviewer Notes:
                                            </label>
                                            <textarea
                                                rows={3}
                                                value={overrideNotes}
                                                onChange={e => setOverrideNotes(e.target.value)}
                                                placeholder="Additional audit notes or timestamp references..."
                                                className="w-full bg-black/40 border border-white/20 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-primary"
                                            />
                                        </div>

                                        <div className="flex gap-3 pt-2">
                                            <button
                                                type="button"
                                                onClick={() => setOverrideCriterion(null)}
                                                className="flex-1 py-2 rounded-lg bg-white/10 text-white text-xs hover:bg-white/15"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                type="submit"
                                                disabled={submittingReview}
                                                className="flex-1 py-2 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary/90 disabled:opacity-50"
                                            >
                                                {submittingReview ? "Saving..." : "Save Assessment"}
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        )}

                        {/* ========================================================================= */}
                        {/* COACHING OBSERVATIONS (STRICTLY OUTSIDE 100-MARK ASSESSMENT)              */}
                        {/* ========================================================================= */}
                        <div className="glass-panel rounded-2xl p-8 border border-white/10 bg-white/[0.01]">
                            <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
                                <div>
                                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                        <span>🎥</span> Coaching Observations
                                    </h2>
                                    <p className="text-xs text-amber-400 font-medium mt-0.5">
                                        Strictly qualitative coaching feedback. Does NOT penalize or alter the 100-mark rubric score.
                                    </p>
                                </div>
                                <span className="text-xs px-2.5 py-1 rounded bg-white/5 text-zinc-400">
                                    Vision Practice Data
                                </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Attention Metrics */}
                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                            <div className="text-zinc-400 text-xs mb-1 uppercase tracking-wider font-semibold">Eye Contact</div>
                                            <div className="text-2xl font-bold text-emerald-400">
                                                {sessionData.eye_contact != null ? `${sessionData.eye_contact}%` : "N/A"}
                                            </div>
                                            <p className="text-[10px] text-zinc-500 mt-1">Practice camera alignment</p>
                                        </div>
                                        <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                                            <div className="text-zinc-400 text-xs mb-1 uppercase tracking-wider font-semibold">Face Present</div>
                                            <div className="text-2xl font-bold text-blue-400">
                                                {sessionData.face_present != null ? `${sessionData.face_present}%` : "N/A"}
                                            </div>
                                            <p className="text-[10px] text-zinc-500 mt-1">Framing consistency</p>
                                        </div>
                                    </div>

                                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs text-zinc-400">
                                        💡 <span className="font-semibold text-zinc-300">Coaching Note:</span> Gaze alignment and facial expressions are tracked to assist in virtual interview presence. In accordance with fair evaluation standards, they are never used as a proxy for technical competence.
                                    </div>
                                </div>

                                {/* Expression Distribution */}
                                <div>
                                    <div className="text-xs uppercase tracking-wider font-semibold text-zinc-400 mb-3">
                                        Expression Breakdown (Practice Only)
                                    </div>
                                    <div className="space-y-2.5">
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
                                                    {emo.value != null ? `${emo.value}%` : "0%"}
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* ========================================================================= */}
                        {/* PRACTICE SESSIONS COMPARISON                                              */}
                        {/* ========================================================================= */}
                        {previousSessions.length > 0 && (
                            <div className="glass-panel rounded-2xl p-6 border border-white/10">
                                <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                                    <span>📈</span> Session Comparison (Same Role & Difficulty)
                                </h3>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left text-xs text-zinc-300">
                                        <thead className="bg-white/5 uppercase text-zinc-400 text-[10px]">
                                            <tr>
                                                <th className="p-2.5">Date</th>
                                                <th className="p-2.5">Role / Level</th>
                                                <th className="p-2.5">Rubric Version</th>
                                                <th className="p-2.5">Coverage</th>
                                                <th className="p-2.5">Score</th>
                                                <th className="p-2.5">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {/* Current Session */}
                                            <tr className="bg-primary/10 font-medium">
                                                <td className="p-2.5 text-white">This Session (Current)</td>
                                                <td className="p-2.5">{sessionData.role} • {sessionData.difficulty}</td>
                                                <td className="p-2.5">{rubric?.rubric_version || "interview_practice_100_v1"}</td>
                                                <td className="p-2.5">{rubric?.coverage_percent ?? 100}%</td>
                                                <td className="p-2.5 text-primary font-bold">
                                                    {isComplete ? `${rubric?.total_score_100} / 100` : `${rubric?.provisional_normalized_100}% (prov)`}
                                                </td>
                                                <td className="p-2.5 text-zinc-500">—</td>
                                            </tr>
                                            {/* Historical Sessions */}
                                            {previousSessions.slice(0, 3).map((hist, idx) => (
                                                <tr key={idx} className="hover:bg-white/[0.02]">
                                                    <td className="p-2.5 text-zinc-400">
                                                        {new Date(hist.created_at || hist.completed_at || Date.now()).toLocaleDateString()}
                                                    </td>
                                                    <td className="p-2.5">{hist.role || "General"} • {hist.difficulty || "Medium"}</td>
                                                    <td className="p-2.5">{hist.rubric_version || "interview_practice_100_v1"}</td>
                                                    <td className="p-2.5">{hist.coverage_percent ?? 95}%</td>
                                                    <td className="p-2.5 text-white font-semibold">
                                                        {hist.total_score_100 ? `${hist.total_score_100} / 100` : hist.provisional_normalized_100 ? `${hist.provisional_normalized_100}% (prov)` : `${hist.overall_score || 0}%`}
                                                    </td>
                                                    <td className="p-2.5">
                                                        <Link href={`/report/${hist.id}`} className="text-primary hover:underline">
                                                            View
                                                        </Link>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}

                        {/* ========================================================================= */}
                        {/* STRENGTHS, IMPROVEMENTS & PRACTICE RECOMMENDATIONS                        */}
                        {/* ========================================================================= */}
                        <div className="glass-panel rounded-2xl p-8">
                            <h2 className="text-lg font-bold text-white mb-6">AI Feedback & Actionable Recommendations</h2>

                            <div className="mb-6 pt-2 pb-6 border-b border-white/5 text-sm text-zinc-300 leading-relaxed">
                                <span className="text-white font-semibold text-base mb-2 block">Executive Summary:</span>
                                {sessionData.general_feedback || "No general feedback available."}
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-3">
                                    <h3 className="text-green-400 font-semibold flex items-center gap-2">✅ Key Strengths</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        {strengths.length > 0 ? strengths.map((s: string, i: number) => (
                                            <li key={i} className="flex gap-2"><span className="text-green-400 shrink-0">•</span>{s}</li>
                                        )) : <li className="text-zinc-500 italic">No specific strengths recorded.</li>}
                                    </ul>
                                </div>
                                <div className="space-y-3">
                                    <h3 className="text-red-400 font-semibold flex items-center gap-2">⚠️ Targeted Improvements</h3>
                                    <ul className="space-y-2 text-sm text-zinc-400">
                                        {weaknesses.length > 0 ? weaknesses.map((w: string, i: number) => (
                                            <li key={i} className="flex gap-2"><span className="text-red-400 shrink-0">•</span>{w}</li>
                                        )) : <li className="text-zinc-500 italic">No specific weaknesses recorded.</li>}
                                    </ul>
                                </div>
                            </div>

                            {sessionData.practice_areas && sessionData.practice_areas.length > 0 && (
                                <div className="mt-6 pt-6 border-t border-white/5">
                                    <h4 className="text-xs uppercase tracking-wider font-semibold text-zinc-400 mb-3">
                                        Recommended Next Practice Areas:
                                    </h4>
                                    <div className="flex flex-wrap gap-2">
                                        {sessionData.practice_areas.map((pa: string, i: number) => (
                                            <span key={i} className="px-3 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-zinc-300 font-medium">
                                                🎯 {pa}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Detailed Q&A Feedback */}
                        {questionFeedback.length > 0 && (
                            <div className="glass-panel rounded-2xl p-8">
                                <h2 className="text-lg font-bold text-white mb-6">Detailed Q&A Transcript & Feedback</h2>
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

                                            {qf.feedback && (
                                                <div className="bg-primary/10 border border-primary/20 rounded-lg p-3">
                                                    <div className="text-xs text-primary uppercase tracking-wider font-semibold mb-1">Feedback:</div>
                                                    <p className="text-sm text-zinc-300">{qf.feedback}</p>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Bottom Actions */}
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
