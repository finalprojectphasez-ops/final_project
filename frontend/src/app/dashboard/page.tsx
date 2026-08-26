"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { supabase } from "@/lib/supabase/client";

const stats = [
    {
        label: "Interviews Done", value: "12", color: "text-violet-400", iconColor: "text-violet-400",
        icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" /></svg>,
    },
    {
        label: "Avg Score", value: "85", color: "text-blue-400", iconColor: "text-blue-400",
        icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg>,
    },
    {
        label: "Best Score", value: "94", color: "text-amber-400", iconColor: "text-amber-400",
        icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0" /></svg>,
    },
    {
        label: "Hours Practiced", value: "8.4", color: "text-emerald-400", iconColor: "text-emerald-400",
        icon: <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    },
];

const history = [
    { role: "Full Stack Engineer", date: "Aug 15, 2026", score: 88, status: "completed", id: "1" },
    { role: "Frontend React Dev", date: "Aug 10, 2026", score: 72, status: "terminated", id: "2" },
    { role: "Backend Python Dev", date: "Aug 5, 2026", score: 91, status: "completed", id: "3" },
    { role: "DevOps Engineer", date: "Jul 28, 2026", score: 79, status: "completed", id: "4" },
];

export default function DashboardPage() {
    const [firstName, setFirstName] = useState("");

    useEffect(() => {
        supabase.auth.getUser().then(({ data }) => {
            const fullName: string =
                data?.user?.user_metadata?.full_name ||
                data?.user?.user_metadata?.name ||
                data?.user?.email?.split("@")[0] ||
                "";
            setFirstName(fullName.split(" ")[0]);
        });
    }, []);

    return (
        <div className="min-h-screen bg-background text-foreground">
            <div className="flex">
                <Sidebar active="dashboard" />
                <main className="flex-1 p-8">
                    <div className="max-w-5xl mx-auto space-y-8">

                        {/* Header */}
                        <div className="flex justify-between items-center">
                            <div>
                                <h1 className="text-3xl font-bold text-white">
                                    Welcome back{firstName ? `, ${firstName}` : ""} 👋
                                </h1>
                                <p className="text-zinc-400 mt-1">Here&apos;s where you left off. Ready for your next session?</p>
                            </div>
                            <Link
                                href="/interview/new"
                                className="flex items-center gap-2 px-5 py-3 bg-primary hover:bg-primary/90 text-white font-semibold rounded-xl transition-all shadow-[0_0_30px_rgba(168,85,247,0.3)]"
                            >
                                + Start Interview
                            </Link>
                        </div>

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {stats.map((s) => (
                                <div key={s.label} className="glass-panel rounded-2xl p-5 hover:-translate-y-1 transition-transform">
                                    <div className={`w-9 h-9 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center mb-4 ${s.iconColor}`}>
                                        {s.icon}
                                    </div>
                                    <div className={`text-3xl font-black ${s.color} mb-1`}>{s.value}</div>
                                    <div className="text-zinc-400 text-sm">{s.label}</div>
                                </div>
                            ))}
                        </div>

                        {/* Quick Start Card */}
                        <div className="glass-panel rounded-2xl p-8 border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                            <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                                <div>
                                    <h2 className="text-2xl font-bold text-white mb-2">Start a Proctored Interview</h2>
                                    <p className="text-zinc-400 max-w-lg">Upload your resume, select a role and difficulty, and get grilled by our AI in a live, proctored session with full emotion tracking.</p>
                                </div>
                                <Link
                                    href="/interview/new"
                                    className="shrink-0 px-8 py-4 bg-primary hover:bg-primary/90 text-white font-bold rounded-xl transition-all text-lg shadow-[0_0_40px_rgba(168,85,247,0.4)]"
                                >
                                    Begin Now
                                </Link>
                            </div>
                        </div>

                        {/* History Table */}
                        <div>
                            <div className="flex justify-between items-center mb-4">
                                <h2 className="text-xl font-bold text-white">Interview History</h2>
                                <span className="text-zinc-500 text-sm">{history.length} sessions</span>
                            </div>
                            <div className="glass-panel rounded-2xl overflow-hidden">
                                <table className="w-full text-left">
                                    <thead>
                                        <tr className="border-b border-white/10 text-zinc-500 text-xs uppercase tracking-wider">
                                            <th className="px-6 py-4 font-medium">Role</th>
                                            <th className="px-6 py-4 font-medium">Date</th>
                                            <th className="px-6 py-4 font-medium">Score</th>
                                            <th className="px-6 py-4 font-medium">Status</th>
                                            <th className="px-6 py-4 font-medium">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {history.map((item, i) => (
                                            <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                                <td className="px-6 py-4 text-white font-medium">{item.role}</td>
                                                <td className="px-6 py-4 text-zinc-400 text-sm">{item.date}</td>
                                                <td className="px-6 py-4">
                                                    <span className={`text-lg font-black ${item.score >= 80 ? "text-green-400" : "text-yellow-400"}`}>
                                                        {item.score}
                                                        <span className="text-zinc-600 text-sm font-normal">/100</span>
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    {item.status === "completed" ? (
                                                        <span className="px-2.5 py-1 rounded-full bg-green-500/15 text-green-400 border border-green-500/30 text-xs font-medium">✓ Completed</span>
                                                    ) : (
                                                        <span className="px-2.5 py-1 rounded-full bg-red-500/15 text-red-400 border border-red-500/30 text-xs font-medium">✕ Terminated</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <Link href={`/report/${item.id}`} className="text-primary text-sm hover:underline">
                                                        View Report →
                                                    </Link>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
