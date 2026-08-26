"use client";

import { useEffect, useState, useRef, useCallback } from "react";

const BACKEND = "http://localhost:8000";

type Message = { role: "ai" | "user"; text: string };

type SessionContext = { role: string; difficulty: string; duration: number; resumeText: string };

export default function InterviewProctorPage({ params }: { params: { id: string } }) {
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [violations, setViolations] = useState(0);
    const [terminated, setTerminated] = useState(false);
    const [terminationReason, setTerminationReason] = useState("");
    const [micOn, setMicOn] = useState(true);
    const [camOn, setCamOn] = useState(true);
    const [camError, setCamError] = useState("");
    const [bars, setBars] = useState<number[]>(Array(40).fill(4));

    // --- AI Q&A state ---
    const [messages, setMessages] = useState<Message[]>([]);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [context, setContext] = useState<SessionContext | null>(null);
    const [aiLoading, setAiLoading] = useState(true);
    const [aiError, setAiError] = useState("");
    const [userInput, setUserInput] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const MAX_VIOLATIONS = 4;

    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const animFrameRef = useRef<number>(0);
    const lastViolationTime = useRef<number>(0);
    const violationCountRef = useRef<number>(0);

    // --- Load session context + call /api/setup ---
    const initSession = useCallback(async () => {
        setAiLoading(true);
        setAiError("");
        try {
            const raw = sessionStorage.getItem("interviewContext");
            const ctx: SessionContext = raw ? JSON.parse(raw) : { role: "Software Engineer", difficulty: "Medium", duration: 30, resumeText: "" };
            setContext(ctx);
            const res = await fetch(`${BACKEND}/api/setup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role: ctx.role, difficulty: ctx.difficulty, resume_text: ctx.resumeText }),
            });
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            const data = await res.json();
            setSessionId(data.session_id);
            setMessages([{ role: "ai", text: data.first_question }]);
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setAiError("Could not connect to AI backend. Make sure the Python server is running on port 8000.\n" + msg);
        } finally {
            setAiLoading(false);
        }
    }, []);

    useEffect(() => { initSession(); }, [initSession]);

    // Auto-scroll chat
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

    // Submit user answer → get next question
    const handleSubmitAnswer = async () => {
        if (!userInput.trim() || !sessionId || submitting) return;
        const answer = userInput.trim();
        setUserInput("");
        setMessages(prev => [...prev, { role: "user", text: answer }]);
        setSubmitting(true);
        try {
            const res = await fetch(`${BACKEND}/api/answer`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_id: sessionId, answer }),
            });
            const data = await res.json();
            setMessages(prev => [...prev, { role: "ai", text: data.next_question }]);
        } catch {
            setMessages(prev => [...prev, { role: "ai", text: "⚠️ Could not reach backend. Check that the Python server is running." }]);
        } finally {
            setSubmitting(false);
        }
    };

    // Carefully log a violation with 3-second cooldown to avoid double-fires
    const logViolation = (reason: string) => {
        const now = Date.now();
        if (now - lastViolationTime.current < 3000) return; // cooldown
        lastViolationTime.current = now;
        violationCountRef.current += 1;
        const count = violationCountRef.current;
        setViolations(count);
        if (count >= MAX_VIOLATIONS) {
            // Stop all tracks
            streamRef.current?.getTracks().forEach(t => t.stop());
            // Exit fullscreen
            if (document.fullscreenElement) document.exitFullscreen().catch(() => { });
            setTerminationReason(reason);
            setTerminated(true);
        }
    };

    // --- Start webcam + mic ---
    useEffect(() => {
        async function initMedia() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                streamRef.current = stream;
                // NOTE: videoRef may not exist yet (gated behind fullscreen)
                // srcObject is attached in the fullscreen useEffect below
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                }
                // Audio analyser for waveform
                const audioCtx = new AudioContext();
                const source = audioCtx.createMediaStreamSource(stream);
                const analyser = audioCtx.createAnalyser();
                analyser.fftSize = 128;
                source.connect(analyser);
                analyserRef.current = analyser;

                const dataArray = new Uint8Array(analyser.frequencyBinCount);
                const draw = () => {
                    analyser.getByteFrequencyData(dataArray);
                    const newBars = Array.from({ length: 40 }, (_, i) => {
                        const idx = Math.floor((i / 40) * dataArray.length);
                        return Math.max(4, (dataArray[idx] / 255) * 100);
                    });
                    setBars(newBars);
                    animFrameRef.current = requestAnimationFrame(draw);
                };
                draw();
            } catch (err) {
                setCamError("Camera/mic permission denied. Please allow access and refresh.");
            }
        }
        initMedia();
        return () => {
            streamRef.current?.getTracks().forEach(t => t.stop());
            cancelAnimationFrame(animFrameRef.current);
        };
    }, []);

    // Re-attach stream to video element once fullscreen is active
    // (the <video> element is only rendered inside the fullscreen view)
    useEffect(() => {
        if (isFullscreen && streamRef.current && videoRef.current) {
            videoRef.current.srcObject = streamRef.current;
            videoRef.current.play().catch(() => { });
        }
    }, [isFullscreen]);


    // Toggle camera track
    const toggleCam = () => {
        const track = streamRef.current?.getVideoTracks()[0];
        if (track) { track.enabled = !track.enabled; setCamOn(v => !v); }
    };

    // Toggle mic track
    const toggleMic = () => {
        const track = streamRef.current?.getAudioTracks()[0];
        if (track) { track.enabled = !track.enabled; setMicOn(v => !v); }
    };

    // --- Anti-Cheating Engine ---
    useEffect(() => {
        const handleFullscreenChange = () => {
            const inFs = !!document.fullscreenElement;
            setIsFullscreen(inFs);
            if (!inFs && violationCountRef.current < MAX_VIOLATIONS) {
                logViolation("Exited fullscreen mode");
            }
        };
        const handleVisibilityChange = () => {
            if (document.visibilityState === "hidden") {
                logViolation("Switched tab or minimized window");
            }
        };

        document.addEventListener("fullscreenchange", handleFullscreenChange);
        document.addEventListener("visibilitychange", handleVisibilityChange);
        return () => {
            document.removeEventListener("fullscreenchange", handleFullscreenChange);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const requestFullscreen = async () => {
        if (document.documentElement.requestFullscreen) {
            await document.documentElement.requestFullscreen();
        }
    };

    // --- Termination Screen ---
    if (terminated) {
        return (
            <div className="fixed inset-0 bg-black flex flex-col items-center justify-center p-6 z-[999]">
                <div className="absolute inset-0 bg-red-950/30" />
                <div className="relative z-10 max-w-md w-full text-center space-y-6">
                    <div className="w-20 h-20 rounded-full bg-red-500/15 border border-red-500/40 flex items-center justify-center mx-auto">
                        <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2">Session Terminated</h1>
                        <p className="text-red-400 font-medium">Interview ended due to proctoring violations</p>
                    </div>
                    <div className="rounded-xl bg-white/5 border border-white/10 p-5 text-left space-y-3">
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-500">Total Violations</span>
                            <span className="text-red-400 font-bold">{MAX_VIOLATIONS} / {MAX_VIOLATIONS}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-500">Final Violation</span>
                            <span className="text-white">{terminationReason}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-500">Session Score</span>
                            <span className="text-zinc-400">Invalidated</span>
                        </div>
                    </div>
                    <p className="text-zinc-600 text-sm">This session has been flagged. You may start a new session from the dashboard.</p>
                    <a href="/dashboard"
                        className="block w-full py-3.5 bg-white/10 hover:bg-white/15 border border-white/15 text-white font-semibold rounded-xl transition-all text-sm">
                        Return to Dashboard
                    </a>
                </div>
            </div>
        );
    }

    if (!isFullscreen) {
        return (
            <div className="fixed inset-0 bg-background flex flex-col items-center justify-center p-6 z-50">
                {camError && (
                    <div className="mb-6 px-5 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm max-w-md text-center">
                        {camError}
                    </div>
                )}
                <div className="glass-panel p-8 max-w-md w-full rounded-2xl text-center shadow-[0_0_50px_rgba(255,0,0,0.1)] border border-red-500/20">
                    <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6">
                        <svg className="w-7 h-7 text-amber-400" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Proctored Session</h2>
                    <p className="text-zinc-400 mb-2 text-sm">This interview requires fullscreen mode.</p>
                    <p className="text-zinc-600 text-xs mb-8">Exiting fullscreen or switching tabs will be logged as a violation. <span className="text-red-400">4 violations = auto-termination.</span></p>
                    <button
                        onClick={requestFullscreen}
                        className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl bg-primary text-white font-bold hover:bg-primary/90 transition-colors"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" /></svg>
                        Start Proctored Session
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
            {/* Top Bar */}
            <header className="h-16 flex justify-between items-center px-6 border-b border-white/10 shrink-0 bg-black/60 backdrop-blur-xl">
                <div className="flex items-center gap-2 text-white font-bold text-lg">PreMock</div>
                <div className="flex items-center gap-6">
                    <div className={`flex items-center gap-2 px-3 py-1 rounded border text-sm font-mono ${violations >= 3 ? "bg-red-500/20 border-red-500/40 text-red-400" : violations >= 2 ? "bg-orange-500/15 border-orange-500/30 text-orange-400" : "bg-white/5 border-white/10 text-zinc-400"}`}>
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>
                        Violations: {violations}/{MAX_VIOLATIONS}
                    </div>
                    <div className="animate-pulse flex items-center gap-2 text-red-500 text-sm font-semibold">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div> LIVE
                    </div>
                </div>
            </header>

            {/* Main Grid */}
            <div className="flex-1 flex gap-6 p-6 min-h-0">
                {/* Left Col */}
                <div className="w-1/3 flex flex-col gap-4 h-full">

                    {/* Live Webcam */}
                    <div className="relative bg-zinc-900 rounded-2xl border border-white/10 overflow-hidden flex-shrink-0" style={{ height: "44%" }}>
                        {camError ? (
                            <div className="absolute inset-0 flex items-center justify-center text-center p-4">
                                <p className="text-red-400 text-sm">{camError}</p>
                            </div>
                        ) : (
                            <video
                                ref={videoRef}
                                autoPlay
                                muted
                                playsInline
                                className={`w-full h-full object-cover ${camOn ? "opacity-100" : "opacity-0"} transition-opacity`}
                            />
                        )}
                        {!camOn && (
                            <div className="absolute inset-0 flex items-center justify-center bg-zinc-900">
                                <span className="text-5xl">🚫</span>
                            </div>
                        )}
                        {/* Emotion badges */}
                        <div className="absolute inset-x-0 top-0 p-3 flex justify-between">
                            <span className="px-2 py-1 bg-black/60 backdrop-blur rounded text-green-400 text-xs">Eye Contact: 88%</span>
                            <span className="px-2 py-1 bg-black/60 backdrop-blur rounded text-blue-400 text-xs">Stress: Low</span>
                        </div>
                        {/* Controls */}
                        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
                            <button onClick={toggleMic} className={`p-3 rounded-full backdrop-blur-md border transition-all ${micOn ? "bg-zinc-800/80 border-white/10 text-white" : "bg-red-500/80 border-red-500 text-white"}`}>
                                {micOn ? "🎤" : "🔇"}
                            </button>
                            <button onClick={toggleCam} className={`p-3 rounded-full backdrop-blur-md border transition-all ${camOn ? "bg-zinc-800/80 border-white/10 text-white" : "bg-red-500/80 border-red-500 text-white"}`}>
                                {camOn ? "📸" : "🚫"}
                            </button>
                        </div>
                    </div>

                    {/* Proctor Intelligence */}
                    <div className="flex-1 glass-panel rounded-2xl p-6 overflow-y-auto">
                        <h3 className="font-bold text-white mb-4">Proctor Intelligence</h3>
                        <ul className="space-y-4">
                            <li className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm text-zinc-300">
                                <span className="text-yellow-400 font-semibold block mb-1">Pacing Check</span>
                                You are speaking slightly fast (140 WPM). Slow down.
                            </li>
                            <li className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm text-zinc-300">
                                <span className="text-blue-400 font-semibold block mb-1">Current Focus</span>
                                Software Architecture & Scale
                            </li>
                            <li className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm text-zinc-300">
                                <span className="text-green-400 font-semibold block mb-1">Eye Contact</span>
                                Maintain eye contact with the camera, not the screen.
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Right Col - Chat */}
                <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden">

                    {/* Chat messages */}
                    <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col">

                        {aiLoading && (
                            <div className="flex gap-4">
                                <div className="w-10 h-10 shrink-0 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">AI</div>
                                <div className="flex-1 pt-1">
                                    <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 text-zinc-400 text-sm inline-flex items-center gap-3">
                                        <span className="flex gap-1 items-center">
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                                        </span>
                                        Connecting to AI engine...
                                    </div>
                                </div>
                            </div>
                        )}

                        {aiError && (
                            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm whitespace-pre-wrap">
                                {aiError}
                                <button onClick={initSession} className="mt-3 block px-4 py-1.5 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-xs font-semibold transition-colors">Retry</button>
                            </div>
                        )}

                        {messages.map((msg, i) => (
                            <div key={i} className={`flex gap-4 ${msg.role === "user" ? "self-end flex-row-reverse max-w-[82%]" : ""}`}>
                                <div className={`w-10 h-10 shrink-0 rounded-full flex items-center justify-center font-bold text-sm ${msg.role === "ai" ? "bg-primary/20 text-primary" : "bg-blue-500/20 text-blue-400"
                                    }`}>{msg.role === "ai" ? "AI" : "ME"}</div>
                                <div className="flex-1 pt-1">
                                    <div className={`p-4 rounded-xl text-sm leading-relaxed ${msg.role === "ai"
                                            ? "bg-primary/10 border border-primary/20 text-zinc-200"
                                            : "bg-white/5 border border-white/10 text-zinc-300"
                                        }`}>{msg.text}</div>
                                </div>
                            </div>
                        ))}

                        {submitting && (
                            <div className="flex gap-4">
                                <div className="w-10 h-10 shrink-0 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">AI</div>
                                <div className="flex-1 pt-1">
                                    <div className="p-4 rounded-xl bg-primary/10 border border-primary/20 text-zinc-400 text-sm inline-flex items-center gap-2">
                                        <span className="flex gap-1 items-center">
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                                        </span>
                                        Thinking...
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={chatEndRef} />
                    </div>

                    {/* Input area */}
                    <div className="border-t border-white/10 bg-black/40 p-4 shrink-0">
                        {/* Session info */}
                        {context && (
                            <div className="flex items-center gap-3 mb-3 text-xs text-zinc-600">
                                <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.role}</span>
                                <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.difficulty}</span>
                                <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.duration} min</span>
                                {/* Waveform */}
                                <div className="flex-1 h-6 flex items-end gap-[2px] overflow-hidden ml-2">
                                    {bars.slice(0, 24).map((h, i) => (
                                        <div key={i} className="flex-1 rounded-full transition-all duration-75"
                                            style={{ height: `${micOn ? h : 4}%`, background: micOn ? `hsl(${270 + i * 2}, 70%, 60%)` : "rgba(255,255,255,0.08)", minHeight: "2px" }} />
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="flex gap-3">
                            <textarea
                                value={userInput}
                                onChange={e => setUserInput(e.target.value)}
                                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmitAnswer(); } }}
                                placeholder={aiLoading ? "Waiting for AI question..." : "Type your answer here... (Enter to send, Shift+Enter for new line)"}
                                disabled={aiLoading || submitting || !!aiError}
                                rows={3}
                                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-primary/40 focus:bg-white/8 transition-all disabled:opacity-40"
                            />
                            <div className="flex flex-col gap-2">
                                <button
                                    onClick={handleSubmitAnswer}
                                    disabled={!userInput.trim() || aiLoading || submitting || !!aiError}
                                    className="px-5 py-3 bg-primary hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm flex-1 flex items-center justify-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" /></svg>
                                    Send
                                </button>
                                <button
                                    onClick={() => { streamRef.current?.getTracks().forEach(t => t.stop()); window.location.href = "/dashboard"; }}
                                    className="px-4 py-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/40 text-red-400 font-medium transition-all text-xs"
                                >
                                    End
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
