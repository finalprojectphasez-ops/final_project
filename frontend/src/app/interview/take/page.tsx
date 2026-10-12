"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { safeSessionStorage } from "@/lib/storage";

const builtInInterviews = [
    {
        id: "frontend",
        role: "Frontend Developer",
        type: "Technical",
        difficulty: "Medium",
        duration: 30,
        desc: "Focuses on React, JavaScript, DOM manipulation, CSS, and general frontend architecture.",
        icon: <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" /></svg>,
        bg: "bg-blue-500/10",
        border: "border-blue-500/20"
    },
    {
        id: "backend",
        role: "Backend Developer",
        type: "Technical",
        difficulty: "Medium",
        duration: 30,
        desc: "Covers API design, database modeling, distributed systems, and backend optimization.",
        icon: <svg className="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z" /></svg>,
        bg: "bg-emerald-500/10",
        border: "border-emerald-500/20"
    },
    {
        id: "fullstack",
        role: "Full Stack Developer",
        type: "Mixed",
        difficulty: "Medium",
        duration: 30,
        desc: "End-to-end knowledge check spanning both frontend interfaces and backend APIs.",
        icon: <svg className="w-8 h-8 text-violet-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M14.25 9.75L16.5 12l-2.25 2.25m-4.5 0L7.5 12l2.25-2.25M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z" /></svg>,
        bg: "bg-violet-500/10",
        border: "border-violet-500/20"
    },
    {
        id: "java",
        role: "Java Developer",
        type: "Technical",
        difficulty: "Medium",
        duration: 30,
        desc: "Core Java, JVM internals, Spring Boot, multithreading, and design patterns.",
        icon: <svg className="w-8 h-8 text-orange-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" /><path strokeLinecap="round" strokeLinejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z" /></svg>,
        bg: "bg-orange-500/10",
        border: "border-orange-500/20"
    },
    {
        id: "python",
        role: "Python Developer",
        type: "Technical",
        difficulty: "Medium",
        duration: 30,
        desc: "Pythonic principles, data structures, algorithms, generators, and async programming.",
        icon: <svg className="w-8 h-8 text-yellow-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" /></svg>,
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/20"
    },
    {
        id: "mobile",
        role: "Mobile Developer",
        type: "Technical",
        difficulty: "Medium",
        duration: 30,
        desc: "Mobile app architecture, UI/UX performance, state management, and platform specifics.",
        icon: <svg className="w-8 h-8 text-pink-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" /></svg>,
        bg: "bg-pink-500/10",
        border: "border-pink-500/20"
    },
];

export default function TakeInterviewPage() {
    const router = useRouter();
    const [loadingId, setLoadingId] = useState<string | null>(null);

    const handleTakeInterview = (interview: typeof builtInInterviews[0]) => {
        setLoadingId(interview.id);
        
        // Save session context so the interview page can pick it up
        safeSessionStorage.setItem("interviewContext", JSON.stringify({
            role: interview.role,
            difficulty: interview.difficulty,
            duration: interview.duration,
            resumeText: "", // Empty for built-in interviews
        }));
        
        const sessionId = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
                const r = (Math.random() * 16) | 0;
                return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
            });
        router.push("/interview/" + sessionId);
    };

    return (
        <div className="min-h-screen bg-background px-6 py-12 relative overflow-hidden">
            {/* Ambient glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />

            <div className="max-w-6xl mx-auto relative z-10">
                {/* Header */}
                <div className="mb-10">
                    <h1 className="text-3xl font-bold text-white tracking-tight">Available Interviews</h1>
                    <p className="text-zinc-500 mt-2 text-sm max-w-2xl">
                        Select a pre-configured interview to jump straight into action. These sessions are tailored to standard industry requirements.
                    </p>
                </div>

                {/* Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {builtInInterviews.map((interview) => (
                        <div 
                            key={interview.id} 
                            className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden hover:bg-white/[0.04] hover:border-white/20 transition-all flex flex-col h-full"
                        >
                            <div className="p-6 flex-1 flex flex-col">
                                <div className="flex justify-between items-start mb-4">
                                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${interview.bg} border ${interview.border}`}>
                                        {interview.icon}
                                    </div>
                                    <div className="flex gap-2">
                                        <span className="px-2.5 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
                                            {interview.type}
                                        </span>
                                        <span className="px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] font-semibold text-blue-400 uppercase tracking-wider">
                                            {interview.difficulty}
                                        </span>
                                    </div>
                                </div>
                                
                                <h3 className="text-lg font-bold text-white mb-2">{interview.role}</h3>
                                <p className="text-zinc-500 text-sm flex-1 leading-relaxed">{interview.desc}</p>
                            </div>
                            
                            <div className="p-6 pt-0 mt-auto">
                                <button 
                                    onClick={() => handleTakeInterview(interview)}
                                    disabled={loadingId === interview.id}
                                    className="w-full py-3 bg-white/5 hover:bg-primary/90 hover:text-white hover:border-primary/50 text-zinc-300 font-semibold rounded-xl border border-white/10 transition-all text-sm flex items-center justify-center gap-2 group"
                                >
                                    {loadingId === interview.id ? (
                                        <>
                                            <svg className="w-4 h-4 animate-spin text-primary group-hover:text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                                            Starting...
                                        </>
                                    ) : (
                                        <>
                                            Take Interview
                                            <svg className="w-4 h-4 text-zinc-500 group-hover:text-white transition-colors" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" /></svg>
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
