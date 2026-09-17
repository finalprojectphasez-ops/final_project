"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { safeSessionStorage } from "@/lib/storage";

const roles = [
    { label: "Full Stack Engineer", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75L16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" /></svg> },
    { label: "Frontend Developer", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" /></svg> },
    { label: "Backend Engineer", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg> },
    { label: "DevOps / SRE", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" /></svg> },
    { label: "ML Engineer", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg> },
    { label: "Data Analyst", icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg> },
];

const difficulties = [
    {
        label: "Easy", desc: "Conceptual & beginner-friendly", tag: "< 2 YOE",
        color: "border-emerald-500/40 bg-emerald-500/5", textColor: "text-emerald-400", dot: "bg-emerald-400",
    },
    {
        label: "Medium", desc: "Real interview standard", tag: "2–5 YOE",
        color: "border-blue-500/40 bg-blue-500/5", textColor: "text-blue-400", dot: "bg-blue-400",
    },
    {
        label: "Hard", desc: "FAANG / senior-level grilling", tag: "5+ YOE",
        color: "border-rose-500/40 bg-rose-500/5", textColor: "text-rose-400", dot: "bg-rose-400",
    },
];

const durations = [
    { label: "15 min", sub: "Quick warm-up" },
    { label: "30 min", sub: "Standard session" },
    { label: "45 min", sub: "Full interview" },
];

const STEP_LABELS = ["Role & Difficulty", "Resume Upload", "Review & Launch"];

export default function NewInterviewPage() {
    const router = useRouter();
    const fileRef = useRef<HTMLInputElement>(null);
    const [step, setStep] = useState(1);
    const [role, setRole] = useState("Full Stack Engineer");
    const [difficulty, setDifficulty] = useState("Medium");
    const [duration, setDuration] = useState("30 min");
    const [fileName, setFileName] = useState("");
    const [dragOver, setDragOver] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleFile = (file: File | null | undefined) => {
        if (file && file.name.endsWith(".pdf")) setFileName(file.name);
    };

    const handleStart = async () => {
        setLoading(true);
        // Read the PDF as base64 text for the backend
        let resumeText = "";
        const inputEl = fileRef.current;
        if (inputEl?.files?.[0]) {
            try {
                resumeText = await inputEl.files[0].text();
            } catch {
                resumeText = fileName; // fallback to filename only
            }
        }
        // Save session context so the interview page can pick it up
        safeSessionStorage.setItem("interviewContext", JSON.stringify({
            role,
            difficulty,
            duration: parseInt(duration, 10),
            resumeText: resumeText.slice(0, 3000),
        }));
        const sessionId = "session-" + Date.now();
        router.push("/interview/" + sessionId);
    };

    const difficultyObj = difficulties.find(d => d.label === difficulty)!;

    return (
        <div className="min-h-screen bg-background flex items-center justify-center px-6 py-12 relative overflow-hidden">
            {/* Ambient glow */}
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-primary/8 rounded-full blur-[160px] pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-blue-500/5 rounded-full blur-[120px] pointer-events-none" />

            <div className="w-full max-w-xl z-10">
                {/* Back link */}
                <a href="/dashboard" className="inline-flex items-center gap-2 text-zinc-500 hover:text-white text-sm mb-8 transition-colors group">
                    <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
                    Back to Dashboard
                </a>

                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-white tracking-tight">New Interview Session</h1>
                    <p className="text-zinc-500 mt-1 text-sm">Set up your personalised AI-proctored interview in 3 steps.</p>
                </div>

                {/* Step Indicators */}
                <div className="flex items-center mb-8">
                    {STEP_LABELS.map((s, i) => (
                        <div key={i} className="flex items-center flex-1 last:flex-none">
                            <div className="flex items-center gap-2.5">
                                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all duration-300 ${step > i + 1
                                    ? "bg-emerald-500 text-white"
                                    : step === i + 1
                                        ? "bg-primary text-white ring-4 ring-primary/20"
                                        : "bg-white/8 text-zinc-600 border border-white/10"
                                    }`}>
                                    {step > i + 1
                                        ? <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                                        : i + 1}
                                </div>
                                <span className={`text-xs font-medium hidden sm:block ${step === i + 1 ? "text-white" : step > i + 1 ? "text-emerald-400" : "text-zinc-600"}`}>{s}</span>
                            </div>
                            {i < 2 && <div className={`flex-1 h-px mx-3 transition-colors duration-500 ${step > i + 1 ? "bg-emerald-500/40" : "bg-white/8"}`} />}
                        </div>
                    ))}
                </div>

                {/* Card */}
                <div className="rounded-2xl border border-white/8 overflow-hidden" style={{ background: "rgba(10,10,14,0.85)", backdropFilter: "blur(20px)" }}>

                    {/* ── STEP 1 ── */}
                    {step === 1 && (
                        <div className="p-7 space-y-7">
                            {/* Role */}
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Target Role</label>
                                <div className="grid grid-cols-2 gap-2.5">
                                    {roles.map(r => (
                                        <button key={r.label} onClick={() => setRole(r.label)}
                                            className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-left transition-all border ${role === r.label
                                                ? "border-primary/60 bg-primary/10 text-white"
                                                : "border-white/8 bg-white/[0.03] text-zinc-400 hover:border-white/20 hover:text-zinc-200"
                                                }`}>
                                            <span className={`${role === r.label ? "text-primary" : "text-zinc-600"} transition-colors`}>{r.icon}</span>
                                            {r.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Difficulty */}
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Difficulty</label>
                                <div className="grid grid-cols-3 gap-2.5">
                                    {difficulties.map(d => (
                                        <button key={d.label} onClick={() => setDifficulty(d.label)}
                                            className={`p-4 rounded-xl border text-left transition-all ${difficulty === d.label ? d.color : "border-white/8 bg-white/[0.03]"
                                                }`}>
                                            <div className="flex items-center gap-2 mb-1.5">
                                                <div className={`w-2 h-2 rounded-full ${difficulty === d.label ? d.dot : "bg-zinc-700"}`} />
                                                <span className={`font-bold text-sm ${difficulty === d.label ? d.textColor : "text-zinc-500"}`}>{d.label}</span>
                                            </div>
                                            <div className={`text-xs leading-tight ${difficulty === d.label ? "text-zinc-300" : "text-zinc-600"}`}>{d.desc}</div>
                                            <div className={`text-xs mt-1.5 font-mono ${difficulty === d.label ? d.textColor : "text-zinc-700"}`}>{d.tag}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Duration */}
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Session Duration</label>
                                <div className="grid grid-cols-3 gap-2.5">
                                    {durations.map(d => (
                                        <button key={d.label} onClick={() => setDuration(d.label)}
                                            className={`py-3 px-4 rounded-xl border text-left transition-all ${duration === d.label
                                                ? "border-primary/50 bg-primary/8 text-white"
                                                : "border-white/8 bg-white/[0.03] text-zinc-500 hover:border-white/15"
                                                }`}>
                                            <div className="font-bold text-sm">{d.label}</div>
                                            <div className="text-xs text-zinc-600 mt-0.5">{d.sub}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button onClick={() => setStep(2)}
                                className="w-full py-3.5 bg-primary hover:bg-primary/90 text-white font-semibold rounded-xl transition-all text-sm flex items-center justify-center gap-2">
                                Continue to Resume Upload
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
                            </button>
                        </div>
                    )}

                    {/* ── STEP 2 ── */}
                    {step === 2 && (
                        <div className="p-7 space-y-6">
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">Upload Resume</label>
                                <p className="text-zinc-600 text-xs mb-4">PDF only · max 5 MB · <span className="text-amber-400 font-medium">Required to proceed</span></p>

                                {/* Drop zone */}
                                <div
                                    onClick={() => fileRef.current?.click()}
                                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                    onDragLeave={() => setDragOver(false)}
                                    onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
                                    className={`relative rounded-xl border-2 border-dashed p-10 flex flex-col items-center text-center cursor-pointer transition-all duration-200 ${dragOver
                                        ? "border-primary/60 bg-primary/5"
                                        : fileName
                                            ? "border-emerald-500/40 bg-emerald-500/5"
                                            : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                                        }`}>
                                    <input ref={fileRef} type="file" accept=".pdf" onChange={e => handleFile(e.target.files?.[0])} className="hidden" />

                                    {fileName ? (
                                        <>
                                            <div className="w-12 h-12 rounded-xl bg-emerald-500/15 flex items-center justify-center mb-4">
                                                <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                                            </div>
                                            <p className="text-white font-medium text-sm">{fileName}</p>
                                            <p className="text-emerald-400 text-xs mt-1">✓ Ready to parse</p>
                                            <button onClick={e => { e.stopPropagation(); setFileName(""); }} className="mt-3 text-xs text-zinc-600 hover:text-red-400 transition-colors">Remove</button>
                                        </>
                                    ) : (
                                        <>
                                            <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                                                <svg className="w-6 h-6 text-zinc-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>
                                            </div>
                                            <p className="text-white text-sm font-medium">Drop your PDF here</p>
                                            <p className="text-zinc-600 text-xs mt-1">or click to browse files</p>
                                        </>
                                    )}
                                </div>

                                {/* Session summary */}
                                <div className="mt-4 p-3.5 rounded-xl bg-white/[0.03] border border-white/8 flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                                        <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                                    </div>
                                    <p className="text-zinc-500 text-xs leading-relaxed">
                                        Questions will be tailored for <span className="text-white font-medium">{role}</span> at <span className={`font-medium ${difficultyObj.textColor}`}>{difficulty}</span> difficulty • <span className="text-white font-medium">{duration}</span> session
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-3">
                                <button onClick={() => setStep(1)} className="py-3 px-5 rounded-xl border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all text-sm font-medium">
                                    ← Back
                                </button>
                                <button
                                    onClick={() => setStep(3)}
                                    disabled={!fileName}
                                    className="flex-1 py-3 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm flex items-center justify-center gap-2"
                                >
                                    {fileName ? (
                                        <>
                                            Continue to Review
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
                                        </>
                                    ) : (
                                        "Upload a PDF to continue"
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── STEP 3 ── */}
                    {step === 3 && (
                        <div className="p-7 space-y-5">
                            <div>
                                <h2 className="text-lg font-bold text-white mb-1">Review & Launch</h2>
                                <p className="text-zinc-600 text-xs">Confirm your session settings before going live.</p>
                            </div>

                            {/* Summary cards */}
                            <div className="space-y-2">
                                {[
                                    {
                                        label: "Role",
                                        value: role,
                                        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" /></svg>,
                                    },
                                    {
                                        label: "Difficulty",
                                        value: difficulty,
                                        valueClass: difficultyObj.textColor,
                                        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg>,
                                    },
                                    {
                                        label: "Duration",
                                        value: duration,
                                        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
                                    },
                                    {
                                        label: "Resume",
                                        value: fileName || "None (generic questions)",
                                        valueClass: fileName ? "text-emerald-400" : "text-zinc-500",
                                        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>,
                                    },
                                ].map((r, i) => (
                                    <div key={i} className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.03] border border-white/8">
                                        <div className="flex items-center gap-2.5 text-zinc-500">
                                            {r.icon}
                                            <span className="text-sm">{r.label}</span>
                                        </div>
                                        <span className={`text-sm font-medium truncate max-w-[55%] text-right ${r.valueClass || "text-white"}`}>{r.value}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Warning */}
                            <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 flex gap-3">
                                <svg className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
                                <p className="text-amber-300/80 text-xs leading-relaxed">
                                    Session will be <strong className="text-amber-300">fullscreen locked</strong>. Tab switching, focus loss, and camera/mic refusals are logged as violations. <strong className="text-amber-300">4 violations terminate the session.</strong>
                                </p>
                            </div>

                            <div className="flex gap-3 pt-1">
                                <button onClick={() => setStep(2)} className="py-3 px-5 rounded-xl border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all text-sm font-medium">
                                    ← Back
                                </button>
                                <button onClick={handleStart} disabled={loading}
                                    className="flex-1 py-3.5 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-bold rounded-xl transition-all text-sm flex items-center justify-center gap-2">
                                    {loading ? (
                                        <>
                                            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                                            Starting session...
                                        </>
                                    ) : (
                                        <>
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" /></svg>
                                            Begin Interview
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                <p className="text-center text-zinc-700 text-xs mt-5">Your session is encrypted and never stored permanently.</p>
            </div>
        </div>
    );
}
