"use client";

import Link from "next/link";
import { useState } from "react";
import { supabase } from "@/lib/supabase/client";

export default function SignUpPage() {
    const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "" });
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [error, setError] = useState("");

    const handleGoogleSignIn = async () => {
        setGoogleLoading(true);
        setError("");
        const { error } = await supabase.auth.signInWithOAuth({
            provider: "google",
            options: {
                redirectTo: `${window.location.origin}/auth/callback`,
            },
        });
        if (error) { setError(error.message); setGoogleLoading(false); }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        if (form.password !== form.confirm) { setError("Passwords do not match."); return; }
        setLoading(true);
        const { error } = await supabase.auth.signUp({
            email: form.email,
            password: form.password,
            options: { data: { full_name: form.name } },
        });
        if (error) setError(error.message);
        else alert("Check your email to confirm your account!");
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-background flex items-center justify-center px-6 py-12">
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="w-full max-w-md z-10">
                <div className="text-center mb-8">
                    <Link href="/" className="inline-block text-2xl font-bold text-white tracking-tight hover:opacity-80 transition-opacity">
                        PreMock
                    </Link>
                    <p className="text-zinc-400 mt-2 text-sm">Create your free account</p>
                </div>

                <div className="glass-panel rounded-2xl p-8 shadow-2xl border border-white/10">
                    <h1 className="text-xl font-bold text-white mb-6">Get started for free</h1>

                    {/* Google OAuth Button */}
                    <button
                        onClick={handleGoogleSignIn}
                        disabled={googleLoading}
                        className="w-full flex items-center justify-center gap-3 py-3 px-6 bg-white hover:bg-zinc-100 disabled:opacity-60 text-zinc-900 font-semibold rounded-lg transition-all mb-6"
                    >
                        <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        {googleLoading ? "Redirecting to Google..." : "Continue with Google"}
                    </button>

                    {/* Divider */}
                    <div className="flex items-center gap-4 mb-6">
                        <div className="flex-1 h-px bg-white/10"></div>
                        <span className="text-zinc-500 text-xs uppercase tracking-widest">or</span>
                        <div className="flex-1 h-px bg-white/10"></div>
                    </div>

                    {error && (
                        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1.5">Full Name</label>
                            <input type="text" required placeholder="Jane Doe" value={form.name}
                                onChange={e => setForm({ ...form, name: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1.5">Email Address</label>
                            <input type="email" required placeholder="jane@example.com" value={form.email}
                                onChange={e => setForm({ ...form, email: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1.5">Password</label>
                            <input type="password" required placeholder="Min. 8 characters" value={form.password}
                                onChange={e => setForm({ ...form, password: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-zinc-400 mb-1.5">Confirm Password</label>
                            <input type="password" required placeholder="Repeat password" value={form.confirm}
                                onChange={e => setForm({ ...form, confirm: e.target.value })}
                                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all" />
                        </div>
                        <button type="submit" disabled={loading}
                            className="w-full mt-2 py-3 px-6 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-semibold rounded-lg transition-all shadow-[0_0_30px_rgba(168,85,247,0.3)] hover:shadow-[0_0_40px_rgba(168,85,247,0.5)]">
                            {loading ? "Creating account..." : "Create Account →"}
                        </button>
                    </form>

                    <p className="text-center text-zinc-500 text-sm mt-6">
                        Already have an account?{" "}
                        <Link href="/auth/login" className="text-primary hover:text-primary/80 font-medium transition-colors">Sign In</Link>
                    </p>
                </div>
                <p className="text-center text-zinc-600 text-xs mt-6">By signing up you agree to our Terms of Service and Privacy Policy.</p>
            </div>
        </div>
    );
}
