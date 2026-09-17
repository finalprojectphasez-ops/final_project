"use client";

import Image from "next/image";
import Sidebar from "@/components/Sidebar";
import { supabase } from "@/lib/supabase/client";
import { useState, useRef, useEffect } from "react";

const ROLES = ["Full Stack Engineer", "Frontend Developer", "Backend Engineer", "DevOps / SRE", "Machine Learning Engineer"];

// Custom dark-themed dropdown
function RoleDropdown({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, []);

    return (
        <div ref={ref} className="relative">
            <button type="button" onClick={() => setOpen(o => !o)}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white text-left flex justify-between items-center focus:outline-none focus:border-primary/60 hover:border-white/20 transition-all">
                <span>{value}</span>
                <span className={`text-zinc-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}>▾</span>
            </button>
            {open && (
                <div className="absolute z-50 mt-2 w-full bg-zinc-900/95 backdrop-blur-xl border border-white/10 rounded-xl overflow-hidden shadow-[0_8px_32px_rgba(0,0,0,0.5)]">
                    {ROLES.map(r => (
                        <button key={r} type="button"
                            onClick={() => { onChange(r); setOpen(false); }}
                            className={`w-full text-left px-4 py-3 text-sm transition-all ${r === value ? "bg-primary/20 text-white font-semibold border-l-2 border-primary" : "text-zinc-300 hover:bg-white/5 hover:text-white"}`}>
                            {r}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function ProfilePage() {
    const photoInputRef = useRef<HTMLInputElement>(null);
    const resumeInputRef = useRef<HTMLInputElement>(null);

    const [firstName, setFirstName] = useState("User");
    const [lastName, setLastName] = useState("");
    const [email, setEmail] = useState("user@example.com");
    const [role, setRole] = useState("Full Stack Engineer");
    const [resumeFile, setResumeFile] = useState<File | null>(null);
    const [photoPreview, setPhotoPreview] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState<{ msg: string; type: "success" | "error" } | null>(null);

    // Load user from Supabase on mount
    useEffect(() => {
        supabase.auth.getUser().then(({ data }) => {
            if (data.user) {
                setEmail(data.user.email ?? "");
                const meta = data.user.user_metadata;
                if (meta?.full_name) {
                    const parts = (meta.full_name as string).split(" ");
                    setFirstName(parts[0] ?? "");
                    setLastName(parts.slice(1).join(" ") ?? "");
                }
                if (meta?.target_role) setRole(meta.target_role as string);
                if (meta?.avatar_url) setPhotoPreview(meta.avatar_url as string);
            }
        });
    }, []);

    const showToast = (msg: string, type: "success" | "error") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const url = URL.createObjectURL(file);
        setPhotoPreview(url);
    };

    const handleResumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) setResumeFile(file);
    };

    const handleSave = async () => {
        setSaving(true);
        const { error } = await supabase.auth.updateUser({
            data: {
                full_name: `${firstName} ${lastName}`.trim(),
                target_role: role,
            },
        });
        setSaving(false);
        if (error) showToast("Failed to save: " + error.message, "error");
        else showToast("Profile saved successfully!", "success");
    };



    const initials = `${firstName.charAt(0)}${lastName.charAt(0) || ""}`.toUpperCase() || "U";

    return (
        <div className="min-h-screen bg-background text-foreground">

            {/* Toast */}
            {toast && (
                <div className={`fixed top-6 right-6 z-50 px-5 py-3 rounded-xl text-sm font-medium shadow-xl border transition-all ${toast.type === "success" ? "bg-green-500/20 border-green-500/40 text-green-300" : "bg-red-500/20 border-red-500/40 text-red-300"}`}>
                    {toast.type === "success" ? "✓" : "✕"} {toast.msg}
                </div>
            )}

            <div className="flex">
                <Sidebar active="profile" />

                <main className="flex-1 p-8">
                    <div className="max-w-3xl mx-auto space-y-8">
                        <div>
                            <h1 className="text-3xl font-bold text-white">Profile & Settings</h1>
                            <p className="text-zinc-400 mt-1">Manage your account details and interview preferences.</p>
                        </div>

                        {/* Avatar Section */}
                        <div className="glass-panel rounded-2xl p-8 flex items-center gap-6">
                            {photoPreview ? (
                                <Image src={photoPreview} alt="Avatar" width={80} height={80} className="w-20 h-20 rounded-full object-cover shrink-0 border-2 border-primary/40" />
                            ) : (
                                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary to-blue-500 flex items-center justify-center text-white text-3xl font-black shrink-0">
                                    {initials}
                                </div>
                            )}
                            <div>
                                <h2 className="text-xl font-bold text-white">{firstName} {lastName}</h2>
                                <p className="text-zinc-400 text-sm">{email}</p>
                                <div className="flex gap-2 mt-3">
                                    <span className="px-2.5 py-1 rounded-full text-xs bg-primary/20 text-primary border border-primary/30 font-medium">Free Plan</span>
                                    <span className="px-2.5 py-1 rounded-full text-xs bg-green-500/20 text-green-400 border border-green-500/30 font-medium">✓ Verified</span>
                                </div>
                            </div>
                            <button onClick={() => photoInputRef.current?.click()}
                                className="ml-auto px-5 py-2.5 glass-panel text-white text-sm rounded-lg hover:bg-white/10 transition-colors">
                                Change Photo
                            </button>
                            <input ref={photoInputRef} type="file" accept="image/*" onChange={handlePhotoChange} className="hidden" />
                        </div>

                        {/* Personal Info */}
                        <div className="glass-panel rounded-2xl p-8 space-y-5">
                            <h2 className="text-lg font-bold text-white border-b border-white/10 pb-4">Personal Information</h2>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1.5">First Name</label>
                                    <input type="text" value={firstName} onChange={e => setFirstName(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/30 transition-all" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1.5">Last Name</label>
                                    <input type="text" value={lastName} onChange={e => setLastName(e.target.value)} placeholder="Doe"
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-primary/60 transition-all" />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Email Address</label>
                                <input type="email" disabled value={email}
                                    className="w-full bg-black/20 border border-white/5 rounded-lg px-4 py-3 text-zinc-500 cursor-not-allowed" />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Target Role</label>
                                <RoleDropdown value={role} onChange={setRole} />
                            </div>
                        </div>

                        {/* Resume Upload */}
                        <div className="glass-panel rounded-2xl p-8 space-y-5">
                            <h2 className="text-lg font-bold text-white border-b border-white/10 pb-4">Resume</h2>
                            <div onClick={() => resumeInputRef.current?.click()}
                                className="border-2 border-dashed border-white/20 rounded-xl p-8 flex flex-col items-center justify-center text-center hover:border-primary/50 transition-colors cursor-pointer bg-white/[0.02]">
                                <div className="text-4xl mb-3">{resumeFile ? "📄" : "📂"}</div>
                                {resumeFile ? (
                                    <>
                                        <p className="text-white font-medium">{resumeFile.name}</p>
                                        <p className="text-green-400 text-sm mt-1">✓ Ready to use</p>
                                    </>
                                ) : (
                                    <>
                                        <p className="text-white font-medium">Click to upload or drag & drop</p>
                                        <p className="text-sm text-zinc-500">PDF only, max 5MB</p>
                                    </>
                                )}
                                <button onClick={e => { e.stopPropagation(); resumeInputRef.current?.click(); }}
                                    className="mt-4 px-5 py-2.5 glass-panel text-white text-sm rounded-lg hover:bg-white/10 transition-colors">
                                    {resumeFile ? "Change File" : "Browse Files"}
                                </button>
                            </div>
                            <input ref={resumeInputRef} type="file" accept=".pdf" onChange={handleResumeChange} className="hidden" />
                            <p className="text-zinc-500 text-sm">Your resume is used to generate targeted interview questions specific to your experience.</p>
                        </div>

                        {/* Save Button */}
                        <div className="flex justify-end pb-8">
                            <button onClick={handleSave} disabled={saving}
                                className="px-8 py-3 bg-primary hover:bg-primary/90 disabled:opacity-60 text-white font-bold rounded-xl transition-all shadow-[0_0_30px_rgba(168,85,247,0.3)] flex items-center gap-2">
                                {saving ? (
                                    <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Saving...</>
                                ) : "Save Changes"}
                            </button>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
