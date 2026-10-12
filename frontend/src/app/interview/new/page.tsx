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
        label: "Easy", apiValue: "beginner", desc: "Fundamentals & small practical examples", tag: "Beginner",
        color: "border-emerald-500/40 bg-emerald-500/5", textColor: "text-emerald-400", dot: "bg-emerald-400",
    },
    {
        label: "Medium", apiValue: "intermediate", desc: "Applied scenarios, debugging & decisions", tag: "Intermediate",
        color: "border-blue-500/40 bg-blue-500/5", textColor: "text-blue-400", dot: "bg-blue-400",
    },
    {
        label: "Hard", apiValue: "advanced", desc: "Architecture, constraints & failure analysis", tag: "Advanced",
        color: "border-rose-500/40 bg-rose-500/5", textColor: "text-rose-400", dot: "bg-rose-400",
    },
];

const durations = [
    { label: "15 min", value: 15, target: "4 questions target", sub: "Quick warm-up" },
    { label: "30 min", value: 30, target: "6 questions target", sub: "Standard session" },
    { label: "45 min", value: 45, target: "8 questions target", sub: "Full interview" },
];

const STEP_LABELS = ["Role & Difficulty", "Resume Upload", "Review & Launch"];

type ExtractedProfile = {
    current_title?: string | null;
    previous_titles?: string[];
    current_company?: string | null;
    previous_companies?: string[];
    years_experience?: number | null;
    seniority?: string | null;
    primary_domain?: string | null;
    industries?: string[];
    core_skills?: string[];
    secondary_skills?: string[];
    tools?: string[];
    leadership_experience?: boolean | null;
    key_achievements?: string[];
    location?: string | null;
    summary?: string | null;
};

export default function NewInterviewPage() {
    const router = useRouter();
    const fileRef = useRef<HTMLInputElement>(null);
    const [step, setStep] = useState(1);
    const [role, setRole] = useState("Full Stack Engineer");
    const [difficulty, setDifficulty] = useState("Medium");
    const [durationMinutes, setDurationMinutes] = useState(30);
    
    // File upload & extraction state
    const [fileName, setFileName] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [dragOver, setDragOver] = useState(false);
    const [extracting, setExtracting] = useState(false);
    const [extractionError, setExtractionError] = useState("");
    const [rawResumeText, setRawResumeText] = useState("");
    
    // Editable Profile state
    const [profile, setProfile] = useState<ExtractedProfile | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [editYears, setEditYears] = useState("");
    const [editSeniority, setEditSeniority] = useState("");
    const [editSkills, setEditSkills] = useState("");
    const [editTools, setEditTools] = useState("");
    const [editSummary, setEditSummary] = useState("");

    // Launch loading state
    const [launching, setLaunching] = useState(false);
    const [launchError, setLaunchError] = useState("");

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

    const handleFileSelect = async (selectedFile: File | null | undefined) => {
        if (!selectedFile) return;
        const name = selectedFile.name.toLowerCase();
        const valid = name.endsWith(".pdf") || name.endsWith(".docx") || name.endsWith(".doc") || name.endsWith(".txt") || name.endsWith(".text");
        if (!valid) {
            setExtractionError("Supported file formats are PDF, DOCX, and TXT.");
            return;
        }

        setFileName(selectedFile.name);
        setFile(selectedFile);
        setExtractionError("");
        setExtracting(true);

        try {
            const formData = new FormData();
            formData.append("file", selectedFile);
            const res = await fetch(`${backendUrl}/api/resume/upload`, {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (!res.ok || !data.success) {
                const errDetail = data?.error || data?.detail || "Failed to extract resume text.";
                setExtractionError(errDetail);
                setProfile(null);
            } else {
                setRawResumeText(data.text || "");
                if (data.profile) {
                    setProfile(data.profile);
                    setEditTitle(data.profile.current_title || "");
                    setEditYears(data.profile.years_experience ? String(data.profile.years_experience) : "");
                    setEditSeniority(data.profile.seniority || "");
                    setEditSkills((data.profile.core_skills || []).join(", "));
                    setEditTools((data.profile.tools || []).join(", "));
                    setEditSummary(data.profile.summary || "");
                }
            }
        } catch (err: any) {
            setExtractionError(err?.message || "Failed to process resume file locally.");
            setProfile(null);
        } finally {
            setExtracting(false);
        }
    };

    const handleStartInterview = async () => {
        setLaunching(true);
        setLaunchError("");

        // Construct confirmed profile with candidate review edits
        let confirmedProfile: ExtractedProfile | null = null;
        if (profile) {
            confirmedProfile = {
                ...profile,
                current_title: editTitle.trim() || null,
                years_experience: editYears ? parseFloat(editYears) : null,
                seniority: editSeniority.trim() || null,
                core_skills: editSkills ? editSkills.split(",").map(s => s.trim()).filter(Boolean) : [],
                tools: editTools ? editTools.split(",").map(t => t.trim()).filter(Boolean) : [],
                summary: editSummary.trim() || null
            };
        }

        try {
            // Call session creation on backend
            // Selected role & difficulty remain strictly authoritative
            const res = await fetch(`${backendUrl}/api/interview/session/create`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    role: role,
                    difficulty: difficulty,
                    duration_minutes: durationMinutes,
                    resume_profile: confirmedProfile,
                    resume_text: rawResumeText
                })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData?.detail || `Server returned HTTP ${res.status}`);
            }

            const sessionData = await res.json();
            const sessionId = sessionData.session_id;

            // Save interview context so page can mount seamlessly
            safeSessionStorage.setItem("interviewContext", JSON.stringify({
                role: sessionData.role,
                difficulty: sessionData.difficulty,
                duration: sessionData.duration_minutes,
                resumeText: rawResumeText,
                profile: confirmedProfile,
                firstQuestion: sessionData.question?.question,
                firstTopic: sessionData.question?.topic,
                plannedTopics: sessionData.planned_topics,
                deadlineTimestamp: sessionData.deadline_timestamp
            }));

            // Launch session
            router.push(`/interview/${sessionId}`);
        } catch (err: any) {
            console.error("Session launch error:", err);
            setLaunchError(err?.message || "Could not launch session. Please try again.");
            setLaunching(false);
        }
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

                    {/* ── STEP 1: Role, Difficulty, Duration ── */}
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
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-3">Session Duration & Planning Target</label>
                                <div className="grid grid-cols-3 gap-2.5">
                                    {durations.map(d => (
                                        <button key={d.label} onClick={() => setDurationMinutes(d.value)}
                                            className={`py-3 px-4 rounded-xl border text-left transition-all ${durationMinutes === d.value
                                                ? "border-primary/50 bg-primary/8 text-white"
                                                : "border-white/8 bg-white/[0.03] text-zinc-500 hover:border-white/15"
                                                }`}>
                                            <div className="font-bold text-sm">{d.label}</div>
                                            <div className="text-xs text-primary/80 mt-0.5">{d.target}</div>
                                            <div className="text-[11px] text-zinc-600 mt-0.5">{d.sub}</div>
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

                    {/* ── STEP 2: Resume Upload & Editable Profile Review ── */}
                    {step === 2 && (
                        <div className="p-7 space-y-6">
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-1">Upload Resume (Optional)</label>
                                <p className="text-zinc-400 text-xs mb-4">Supported formats: PDF, DOCX, TXT · max 5 MB</p>

                                {/* Drop zone */}
                                <div
                                    onClick={() => fileRef.current?.click()}
                                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                    onDragLeave={() => setDragOver(false)}
                                    onDrop={e => { e.preventDefault(); setDragOver(false); handleFileSelect(e.dataTransfer.files[0]); }}
                                    className={`relative rounded-xl border-2 border-dashed p-8 flex flex-col items-center text-center cursor-pointer transition-all duration-200 ${dragOver
                                        ? "border-primary/60 bg-primary/5"
                                        : fileName && profile
                                            ? "border-emerald-500/40 bg-emerald-500/5"
                                            : extractionError
                                                ? "border-rose-500/40 bg-rose-500/5"
                                                : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
                                        }`}>
                                    <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt,.text" onChange={e => handleFileSelect(e.target.files?.[0])} className="hidden" />

                                    {extracting ? (
                                        <div className="flex flex-col items-center py-4">
                                            <svg className="w-8 h-8 animate-spin text-primary mb-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                                            <p className="text-white text-sm font-medium">Extracting professional information...</p>
                                            <p className="text-zinc-500 text-xs mt-1">Processing locally using shared local language model</p>
                                        </div>
                                    ) : fileName && profile ? (
                                        <>
                                            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center mb-3">
                                                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                            </div>
                                            <p className="text-white font-medium text-sm">{fileName}</p>
                                            <p className="text-emerald-400 text-xs mt-1">✓ Professional profile successfully extracted</p>
                                            <button onClick={e => { e.stopPropagation(); setFileName(""); setFile(null); setProfile(null); }} className="mt-2 text-xs text-zinc-500 hover:text-rose-400 transition-colors">Replace / Remove</button>
                                        </>
                                    ) : (
                                        <>
                                            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-3">
                                                <svg className="w-5 h-5 text-zinc-500" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" /></svg>
                                            </div>
                                            <p className="text-white text-sm font-medium">Drop your PDF, DOCX or TXT file here</p>
                                            <p className="text-zinc-500 text-xs mt-1">or click to browse files</p>
                                        </>
                                    )}
                                </div>

                                {/* Extraction Error Display */}
                                {extractionError && (
                                    <div className="mt-3 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-2.5 text-xs text-rose-300">
                                        <svg className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
                                        <div>
                                            <span className="font-semibold block mb-0.5">Extraction Error:</span>
                                            {extractionError}
                                        </div>
                                    </div>
                                )}

                                {/* Editable Extracted Profile Review Form */}
                                {profile && (
                                    <div className="mt-5 p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-3.5 animate-in fade-in">
                                        <div className="flex items-center justify-between border-b border-white/5 pb-2">
                                            <span className="text-xs font-semibold text-white uppercase tracking-wider">Review & Edit Extracted Profile</span>
                                            <span className="text-[11px] text-zinc-500">15-field profile contract</span>
                                        </div>

                                        <div className="grid grid-cols-2 gap-3 text-xs">
                                            <div>
                                                <label className="text-zinc-500 block mb-1">Current Title</label>
                                                <input
                                                    type="text"
                                                    value={editTitle}
                                                    onChange={e => setEditTitle(e.target.value)}
                                                    placeholder="e.g. Senior Software Engineer"
                                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/50"
                                                />
                                            </div>
                                            <div>
                                                <label className="text-zinc-500 block mb-1">Years of Experience</label>
                                                <input
                                                    type="number"
                                                    value={editYears}
                                                    onChange={e => setEditYears(e.target.value)}
                                                    placeholder="e.g. 5"
                                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/50"
                                                />
                                            </div>
                                        </div>

                                        <div className="text-xs">
                                            <label className="text-zinc-500 block mb-1">Core Technical Skills (comma separated)</label>
                                            <input
                                                type="text"
                                                value={editSkills}
                                                onChange={e => setEditSkills(e.target.value)}
                                                placeholder="React, TypeScript, Node.js, PostgreSQL"
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/50"
                                            />
                                        </div>

                                        <div className="text-xs">
                                            <label className="text-zinc-500 block mb-1">Tools & Platforms</label>
                                            <input
                                                type="text"
                                                value={editTools}
                                                onChange={e => setEditTools(e.target.value)}
                                                placeholder="Docker, Git, AWS, Kubernetes"
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/50"
                                            />
                                        </div>

                                        <div className="text-xs">
                                            <label className="text-zinc-500 block mb-1">Professional Summary</label>
                                            <textarea
                                                rows={2}
                                                value={editSummary}
                                                onChange={e => setEditSummary(e.target.value)}
                                                placeholder="Brief grounded professional summary..."
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-primary/50"
                                            />
                                        </div>
                                    </div>
                                )}

                                {!profile && (
                                    <div className="mt-4 p-3.5 rounded-xl bg-white/[0.03] border border-white/8 flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                                            <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                                        </div>
                                        <p className="text-zinc-500 text-xs leading-relaxed">
                                            No resume? You can proceed to a standard <strong className="text-white">Role-Only Interview</strong> with hypothetical scenarios.
                                        </p>
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-3">
                                <button onClick={() => setStep(1)} className="py-3 px-5 rounded-xl border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all text-sm font-medium">
                                    ← Back
                                </button>
                                <button
                                    onClick={() => setStep(3)}
                                    className="flex-1 py-3 bg-primary hover:bg-primary/90 text-white font-semibold rounded-xl transition-all text-sm flex items-center justify-center gap-2"
                                >
                                    Continue to Review
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── STEP 3: Review & Launch ── */}
                    {step === 3 && (
                        <div className="p-7 space-y-5">
                            <div>
                                <h2 className="text-lg font-bold text-white mb-1">Review & Launch</h2>
                                <p className="text-zinc-400 text-xs">Confirm your session settings. The selected role and difficulty remain authoritative.</p>
                            </div>

                            {/* Summary cards */}
                            <div className="space-y-2.5">
                                <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.03] border border-white/8">
                                    <div className="flex items-center gap-2.5 text-zinc-400">
                                        <span className="text-xs font-semibold uppercase tracking-wider">Authoritative Role</span>
                                    </div>
                                    <span className="text-sm font-bold text-white">{role}</span>
                                </div>

                                <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.03] border border-white/8">
                                    <div className="flex items-center gap-2.5 text-zinc-400">
                                        <span className="text-xs font-semibold uppercase tracking-wider">Difficulty Level</span>
                                    </div>
                                    <span className={`text-sm font-bold ${difficultyObj.textColor}`}>{difficulty} ({difficultyObj.tag})</span>
                                </div>

                                <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.03] border border-white/8">
                                    <div className="flex items-center gap-2.5 text-zinc-400">
                                        <span className="text-xs font-semibold uppercase tracking-wider">Duration & Targets</span>
                                    </div>
                                    <span className="text-sm font-medium text-white">{durationMinutes} min ({durationMinutes === 15 ? 4 : durationMinutes === 30 ? 6 : 8} main questions, max 2 follow-ups)</span>
                                </div>

                                <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-white/[0.03] border border-white/8">
                                    <div className="flex items-center gap-2.5 text-zinc-400">
                                        <span className="text-xs font-semibold uppercase tracking-wider">Candidate Profile</span>
                                    </div>
                                    <span className={`text-sm font-medium truncate max-w-[55%] text-right ${profile ? "text-emerald-400" : "text-zinc-500"}`}>
                                        {profile ? (editTitle || "Extracted Profile Attached") : "Role-Only (No Resume)"}
                                    </span>
                                </div>

                                {profile && editSkills && (
                                    <div className="py-2.5 px-4 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-zinc-400">
                                        <span className="text-zinc-500 block mb-0.5">Resume Grounding Skills:</span>
                                        <span className="text-zinc-200">{editSkills}</span>
                                    </div>
                                )}
                            </div>

                            {/* Authoritative Guard Notice */}
                            <div className="p-3.5 rounded-xl bg-blue-500/5 border border-blue-500/20 text-xs text-blue-300/90 leading-relaxed">
                                <strong>System Note:</strong> Selected job role and difficulty remain strictly authoritative. Resume background personalizes technical context but will never override your selected role or difficulty.
                            </div>

                            {launchError && (
                                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                                    {launchError}
                                </div>
                            )}

                            <div className="flex gap-3 pt-1">
                                <button onClick={() => setStep(2)} className="py-3 px-5 rounded-xl border border-white/10 text-zinc-400 hover:text-white hover:border-white/20 transition-all text-sm font-medium">
                                    ← Back
                                </button>
                                <button onClick={handleStartInterview} disabled={launching}
                                    className="flex-1 py-3.5 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-bold rounded-xl transition-all text-sm flex items-center justify-center gap-2">
                                    {launching ? (
                                        <>
                                            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                                            Starting session...
                                        </>
                                    ) : (
                                        <>
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" /></svg>
                                            Launch Interview Session
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                <p className="text-center text-zinc-700 text-xs mt-5">Session timer begins upon launch after review.</p>
            </div>
        </div>
    );
}
