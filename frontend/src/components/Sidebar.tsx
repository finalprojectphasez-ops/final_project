"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";

const NavIcons = {
    dashboard: (
        <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <rect x="3" y="3" width="7" height="7" rx="1.5" />
            <rect x="14" y="3" width="7" height="7" rx="1.5" />
            <rect x="3" y="14" width="7" height="7" rx="1.5" />
            <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
    ),
    interview: (
        <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
        </svg>
    ),
    reports: (
        <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
    ),
    profile: (
        <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
    ),
    logout: (
        <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
        </svg>
    ),
};

export default function Sidebar({ active }: { active: "dashboard" | "interview" | "reports" | "profile" }) {
    const [collapsed, setCollapsed] = useState(false);
    const [userName, setUserName] = useState("User");
    const [userEmail, setUserEmail] = useState("");
    const pathname = usePathname();
    const isOnInterviewPage = pathname?.startsWith("/interview");
    const [interviewOpen, setInterviewOpen] = useState(!!isOnInterviewPage);

    useEffect(() => {
        if (isOnInterviewPage) setInterviewOpen(true);
    }, [isOnInterviewPage]);

    useEffect(() => {
        supabase.auth.getUser().then(({ data }) => {
            const u = data?.user;
            const full: string =
                u?.user_metadata?.full_name ||
                u?.user_metadata?.name ||
                u?.email?.split("@")[0] ||
                "User";
            setUserName(full);
            setUserEmail(u?.email ?? "");
        });
    }, []);

    const router = useRouter();

    const handleLogout = async () => {
        await supabase.auth.signOut();
        router.push("/auth/login");
    };

    const isInterviewActive = active === "interview";

    return (
        <>
            {/* Sidebar */}
            <aside
                className="h-screen fixed left-0 top-0 border-r border-white/10 bg-black/40 backdrop-blur-xl flex flex-col z-40 transition-all duration-300 ease-in-out"
                style={{ width: collapsed ? "72px" : "256px" }}
            >
                {/* Top: Logo + Toggle */}
                <div className={`flex items-center border-b border-white/8 shrink-0 h-16 px-4 ${collapsed ? "justify-center" : "justify-between"}`}>
                    {!collapsed && (
                        <Link href="/" className="text-lg font-bold text-white tracking-tight truncate">
                            PreMock
                        </Link>
                    )}
                    <button
                        onClick={() => setCollapsed(v => !v)}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-500 hover:text-white hover:bg-white/8 border border-transparent hover:border-white/10 transition-all shrink-0"
                        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                    >
                        {collapsed ? (
                            // Chevron right (expand)
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                            </svg>
                        ) : (
                            // Chevron left (collapse)
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                            </svg>
                        )}
                    </button>
                </div>

                {/* Nav */}
                <nav className="flex flex-col gap-1 flex-1 p-3 pt-4">
                    {/* Dashboard */}
                    <Link
                        href="/dashboard"
                        title={collapsed ? "Dashboard" : undefined}
                        className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${collapsed ? "justify-center" : ""} ${
                            active === "dashboard"
                                ? "bg-primary/15 text-white border border-primary/25 shadow-[0_0_12px_rgba(109,40,217,0.1)]"
                                : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
                        }`}
                    >
                        <span className={active === "dashboard" ? "text-primary" : "text-zinc-500"}>
                            {NavIcons.dashboard}
                        </span>
                        {!collapsed && <span className="truncate transition-all duration-200">Dashboard</span>}
                    </Link>

                    {/* Interview (expandable) */}
                    <div>
                        <button
                            onClick={() => {
                                if (collapsed) {
                                    router.push("/interview/new");
                                } else {
                                    setInterviewOpen(v => !v);
                                }
                            }}
                            title={collapsed ? "Interview" : undefined}
                            className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${collapsed ? "justify-center" : ""} ${
                                isInterviewActive
                                    ? "bg-primary/15 text-white border border-primary/25 shadow-[0_0_12px_rgba(109,40,217,0.1)]"
                                    : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
                            }`}
                        >
                            <span className={isInterviewActive ? "text-primary" : "text-zinc-500"}>
                                {NavIcons.interview}
                            </span>
                            {!collapsed && (
                                <>
                                    <span className="truncate transition-all duration-200 flex-1 text-left">Interview</span>
                                    <svg
                                        className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${interviewOpen ? "rotate-180" : ""} ${isInterviewActive ? "text-primary" : "text-zinc-600"}`}
                                        fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                                    </svg>
                                </>
                            )}
                        </button>

                        {/* Submenu */}
                        {!collapsed && interviewOpen && (
                            <div className="mt-1 ml-4 pl-3 border-l border-white/10 flex flex-col gap-0.5">
                                <Link
                                    href="/interview/new"
                                    className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                                        pathname === "/interview/new"
                                            ? "text-white bg-primary/10 border border-primary/20"
                                            : "text-zinc-500 hover:text-white hover:bg-white/5 border border-transparent"
                                    }`}
                                >
                                    <svg className={`w-3.5 h-3.5 shrink-0 ${pathname === "/interview/new" ? "text-primary" : "text-zinc-600"}`} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                                    </svg>
                                    New Interview
                                </Link>
                                <Link
                                    href="/interview/take"
                                    className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                                        pathname === "/interview/take"
                                            ? "text-white bg-primary/10 border border-primary/20"
                                            : "text-zinc-500 hover:text-white hover:bg-white/5 border border-transparent"
                                    }`}
                                >
                                    <svg className={`w-3.5 h-3.5 shrink-0 ${pathname === "/interview/take" ? "text-primary" : "text-zinc-600"}`} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
                                    </svg>
                                    Take Interview
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Reports */}
                    <Link
                        href="/dashboard"
                        title={collapsed ? "Reports" : undefined}
                        className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${collapsed ? "justify-center" : ""} ${
                            active === "reports"
                                ? "bg-primary/15 text-white border border-primary/25 shadow-[0_0_12px_rgba(109,40,217,0.1)]"
                                : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
                        }`}
                    >
                        <span className={active === "reports" ? "text-primary" : "text-zinc-500"}>
                            {NavIcons.reports}
                        </span>
                        {!collapsed && <span className="truncate transition-all duration-200">Reports</span>}
                    </Link>

                    {/* Profile */}
                    <Link
                        href="/profile"
                        title={collapsed ? "Profile" : undefined}
                        className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${collapsed ? "justify-center" : ""} ${
                            active === "profile"
                                ? "bg-primary/15 text-white border border-primary/25 shadow-[0_0_12px_rgba(109,40,217,0.1)]"
                                : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
                        }`}
                    >
                        <span className={active === "profile" ? "text-primary" : "text-zinc-500"}>
                            {NavIcons.profile}
                        </span>
                        {!collapsed && <span className="truncate transition-all duration-200">Profile</span>}
                    </Link>
                </nav>

                {/* Footer */}
                <div className={`pt-4 pb-4 border-t border-white/10 px-3 space-y-2`}>
                    {!collapsed && (
                        <div className="flex items-center gap-3 px-2 pb-1">
                            <div className="w-7 h-7 rounded-full bg-primary/30 flex items-center justify-center text-white font-bold text-xs shrink-0">
                                {userName[0]?.toUpperCase() ?? "U"}
                            </div>
                            <div className="min-w-0">
                                <p className="text-white text-sm font-medium truncate">{userName}</p>
                                <p className="text-zinc-600 text-xs truncate">{userEmail || "Free Plan"}</p>
                            </div>
                        </div>
                    )}
                    <button
                        onClick={handleLogout}
                        title={collapsed ? "Sign Out" : undefined}
                        className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-red-500/8 border border-transparent hover:border-red-500/15 transition-all ${collapsed ? "justify-center" : ""}`}
                    >
                        {NavIcons.logout}
                        {!collapsed && <span>Sign Out</span>}
                    </button>
                </div>
            </aside>

            {/* Spacer so page content shifts with sidebar */}
            <div
                className="shrink-0 transition-all duration-300"
                style={{ width: collapsed ? "72px" : "256px" }}
            />
        </>
    );
}
