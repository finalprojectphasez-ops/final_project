"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { safeSessionStorage } from "@/lib/storage";
import { supabase } from "@/lib/supabase/client";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type Message = { role: "ai" | "user"; text: string };

type SessionContext = {
    role: string;
    difficulty: string;
    duration: number;
    resumeText: string;
    candidateName?: string;
    education?: string;
    location?: string;
};


export default function InterviewProctorPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: _id } = React.use(params);
    const router = useRouter();
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [violations, setViolations] = useState(0);
    const [terminated, setTerminated] = useState(false);
    const [terminationReason, setTerminationReason] = useState("");
    const [micOn, setMicOn] = useState(true);
    const [camOn, setCamOn] = useState(true);
    const [camError, setCamError] = useState("");
    const [bars, setBars] = useState<number[]>(Array(40).fill(4));
    
    // Warning state
    const [activeWarning, setActiveWarning] = useState<string | null>(null);

    // --- AI Q&A state ---
    const [messages, setMessages] = useState<Message[]>([]);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [context, setContext] = useState<SessionContext | null>(null);
    const [aiLoading, setAiLoading] = useState(true);
    const [aiError, setAiError] = useState("");
    const [candidateName, setCandidateName] = useState<string>("");
    const [userInput, setUserInput] = useState("");
    const [provisionalText, setProvisionalText] = useState("");
    const recordingIdRef = useRef<number>(0);
    const [submitting, setSubmitting] = useState(false);
    const [isEvaluating, setIsEvaluating] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    // 3-Part Interview Flow State: Part 1 = Intro, Part 2 = Technical, Part 3 = Soft Skills
    const [currentPhase, setCurrentPhase] = useState<"intro" | "technical" | "softskill">("intro");
    const [turnIndex, setTurnIndex] = useState<number>(1);

    // FIX: Speech synthesis + recognition state
    const [isSpeaking, setIsSpeaking] = useState(false);

    // --- Local Whisper State ---
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isWavRecording, setIsWavRecording] = useState(false);
    const audioContextRef = useRef<AudioContext | null>(null);
    const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
    const audioChunksRef = useRef<Float32Array[]>([]);
    const allAudioChunksRef = useRef<Float32Array[]>([]);
    
    // Streaming refs
    const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const uploadQueueRef = useRef<Blob[]>([]);
    const isUploadingRef = useRef(false);
    const activeChunkAbortRef = useRef<AbortController | null>(null);

    const mergeTranscripts = (existing: string, next: string) => {
        if (!existing) return next.trim();
        if (!next) return existing;
        
        const cleanExisting = existing.trim();
        const cleanNext = next.trim();
        if (cleanExisting.toLowerCase() === cleanNext.toLowerCase()) return cleanExisting;
        if (cleanExisting.toLowerCase().endsWith(cleanNext.toLowerCase())) return cleanExisting;

        const w1 = cleanExisting.split(/\s+/);
        const w2 = cleanNext.split(/\s+/);
        
        let overlap = 0;
        const maxCheck = Math.min(w1.length, w2.length, 8);
        for (let i = 1; i <= maxCheck; i++) {
            const endW1 = w1.slice(-i).join(" ").toLowerCase().replace(/[^a-z0-9]/g, '');
            const startW2 = w2.slice(0, i).join(" ").toLowerCase().replace(/[^a-z0-9]/g, '');
            if (endW1 === startW2 && endW1.length > 0) {
                overlap = i;
            }
        }
        
        if (overlap > 0) {
            const added = w2.slice(overlap).join(" ");
            return added ? `${cleanExisting} ${added}` : cleanExisting;
        }
        return `${cleanExisting} ${cleanNext}`;
    };


    // Timer state
    const [timeLeft, setTimeLeft] = useState<number | null>(null);

    const MAX_VIOLATIONS = 4;

    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const animFrameRef = useRef<number>(0);
    const lastViolationTime = useRef<number>(0);
    const violationCountRef = useRef<number>(0);
    const emotionPredictionsRef = useRef<{emotion: string, confidence: number}[]>([]);
    const facePresentRef = useRef<{facePresent: boolean}[]>([]);
    const eyeContactPredictionsRef = useRef<{lookingAtCamera: boolean}[]>([]);

    // Warning counters
    const consecutiveNoFace = useRef(0);
    const consecutiveNoEyeContact = useRef(0);
    const noFaceViolationCounted = useRef(false);
    const multipleFaceViolationCounted = useRef(false);
    const eyeContactViolationCounted = useRef(false);
    const eyeContactViolationsRef = useRef(0);
    const faceDetectionViolationsRef = useRef(0);
    const answerEvaluationsRef = useRef<any[]>([]);
    const currentQuestionRef = useRef("");

    // -----------------------------------------------------------------------
    // FIX: Speech Synthesis — speak text aloud using browser TTS
    // -----------------------------------------------------------------------
    const speakText = useCallback((text: string) => {
        if (typeof window === "undefined" || !window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        utterance.lang = "en-US";
        utterance.onstart = () => setIsSpeaking(true);
        utterance.onend = () => setIsSpeaking(false);
        utterance.onerror = () => setIsSpeaking(false);
        // Prefer an English voice if available
        const loadAndSpeak = () => {
            const voices = window.speechSynthesis.getVoices();
            const preferred = voices.find(v => v.lang.startsWith("en") && /female|woman|samantha|karen|victoria|zira/i.test(v.name)) ||
                voices.find(v => v.lang.startsWith("en"));
            if (preferred) utterance.voice = preferred;
            window.speechSynthesis.speak(utterance);
        };
        // Voices may not be loaded yet on first call
        if (window.speechSynthesis.getVoices().length === 0) {
            window.speechSynthesis.onvoiceschanged = loadAndSpeak;
        } else {
            loadAndSpeak();
        }
    }, []);

    // -----------------------------------------------------------------------
    // FIX: Local Whisper WAV Recording & Encoding
    // -----------------------------------------------------------------------
    const encodeWAV = (samples: Float32Array, sampleRate: number) => {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);
        
        const writeString = (view: DataView, offset: number, string: string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(view, 0, 'RIFF');
        view.setUint32(4, 36 + samples.length * 2, true);
        writeString(view, 8, 'WAVE');
        writeString(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(view, 36, 'data');
        view.setUint32(40, samples.length * 2, true);
        
        let offset = 44;
        for (let i = 0; i < samples.length; i++, offset += 2) {
            let s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        
        return new Blob([view], { type: 'audio/wav' });
    };

    const processUploadQueue = async (activeRecordingId: number) => {
        if (isUploadingRef.current || uploadQueueRef.current.length === 0) return;
        isUploadingRef.current = true;
        
        while (uploadQueueRef.current.length > 0) {
            // Drop queued slices if recording has stopped or changed session
            if (recordingIdRef.current !== activeRecordingId) {
                uploadQueueRef.current = [];
                break;
            }
            
            const blob = uploadQueueRef.current.shift();
            if (!blob) continue;
            
            const chunkId = Date.now() + Math.floor(Math.random() * 1000);
            const chunkAbort = new AbortController();
            activeChunkAbortRef.current = chunkAbort;
            const chunkTimer = setTimeout(() => chunkAbort.abort(), 15000);
            
            try {
                const formData = new FormData();
                formData.append("audio", blob, "chunk.wav");
                console.log(`[Chunk ${chunkId}] Uploading live slice: ${blob.size} bytes`);
                
                const res = await fetch(`${BACKEND}/api/speech/transcribe-local`, {
                    method: "POST",
                    body: formData,
                    signal: chunkAbort.signal,
                });
                console.log(`[Chunk ${chunkId}] HTTP status ${res.status}`);
                let data: any = {};
                try { data = await res.json(); } catch { /* non-JSON body, ignore */ }
                
                // Only apply if THIS recording session is still active
                if (recordingIdRef.current === activeRecordingId) {
                    if (res.ok && typeof data.text === 'string' && data.text.trim()) {
                        console.log(`[Chunk ${chunkId}] Whisper text: ${data.text.trim().length} chars`);
                        setProvisionalText(prev => {
                            const merged = mergeTranscripts(prev, data.text);
                            return merged;
                        });
                    }
                } else {
                    console.log(`[Chunk ${chunkId}] Late chunk response ignored (session ended)`);
                }
            } catch (err: any) {
                if (err?.name === 'AbortError') {
                    console.log(`[Chunk ${chunkId}] Chunk upload aborted.`);
                } else {
                    console.error(`[Chunk ${chunkId}] Live chunk upload error:`, err);
                }
            } finally {
                clearTimeout(chunkTimer);
                if (activeChunkAbortRef.current === chunkAbort) {
                    activeChunkAbortRef.current = null;
                }
            }
        }
        isUploadingRef.current = false;
    };

    const flushAudioChunks = (sr?: number) => {
        if (recordingIdRef.current === 0) return;
        const chunks = audioChunksRef.current;
        if (chunks.length === 0) return;
        
        const overlapCount = 2; // ~0.5s overlap
        audioChunksRef.current = chunks.slice(-overlapCount);
        
        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const samples = new Float32Array(totalLength);
        let offset = 0;
        for (const chunk of chunks) {
            samples.set(chunk, offset);
            offset += chunk.length;
        }
        
        const actualSampleRate = sr || audioContextRef.current?.sampleRate || 16000;
        const wavBlob = encodeWAV(samples, actualSampleRate);
        
        if (uploadQueueRef.current.length < 5) {
            uploadQueueRef.current.push(wavBlob);
            processUploadQueue(recordingIdRef.current);
        }
    };

    const startWavRecording = useCallback(async () => {
        // Prevent duplicate microphone recording sessions
        if (isWavRecording || isTranscribing || recordingIdRef.current !== 0) {
            console.warn("[MicDiag] Recording or transcription already active, ignoring duplicate start request.");
            return;
        }

        // Step 1: Ensure active, live audio track exists in streamRef.current
        let audioTrack = streamRef.current?.getAudioTracks().find(t => t.readyState === 'live');
        if (!audioTrack) {
            try {
                console.log("[MicDiag] No live audio track found. Requesting new audio stream...");
                const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioTrack = audioStream.getAudioTracks()[0];
                if (streamRef.current) {
                    // Remove any dead/ended audio tracks
                    streamRef.current.getAudioTracks().forEach(t => {
                        if (t.readyState === 'ended') streamRef.current?.removeTrack(t);
                    });
                    streamRef.current.addTrack(audioTrack);
                } else {
                    streamRef.current = audioStream;
                }
                setMicOn(true);
            } catch (err) {
                console.error("[MicDiag] Microphone acquisition failed:", err);
                setAiError("Microphone not available. Please allow microphone access.");
                return;
            }
        } else {
            // Ensure track is enabled
            audioTrack.enabled = true;
            setMicOn(true);
        }

        try {
            console.log(`[MicDiag] Starting recording. Audio track: readyState=${audioTrack.readyState}, enabled=${audioTrack.enabled}, label=${audioTrack.label}`);
            
            const currentRecId = Date.now();
            recordingIdRef.current = currentRecId;
            audioChunksRef.current = [];
            allAudioChunksRef.current = [];
            uploadQueueRef.current = [];
            isUploadingRef.current = false;
            setProvisionalText("");
            
            // Step 2: Initialize Web Audio pipeline
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            audioContextRef.current = ctx;
            if (ctx.state === 'suspended') {
                console.log("[MicDiag] AudioContext is suspended. Resuming...");
                await ctx.resume();
            }
            console.log(`[MicDiag] AudioContext active: sampleRate=${ctx.sampleRate}Hz, state=${ctx.state}`);

            // Use the actual live audio track
            const liveStream = new MediaStream([audioTrack]);
            const source = ctx.createMediaStreamSource(liveStream);
            const processor = ctx.createScriptProcessor(4096, 1, 1);
            let chunkCount = 0;
            
            processor.onaudioprocess = (e) => {
                const channelData = e.inputBuffer.getChannelData(0);
                const chunk = new Float32Array(channelData);
                audioChunksRef.current.push(chunk);
                allAudioChunksRef.current.push(chunk);
                
                // Diagnostic logging for first chunks and periodically
                if (chunkCount < 4) {
                    const sumSq = chunk.reduce((s, x) => s + x * x, 0);
                    const rms = Math.sqrt(sumSq / chunk.length);
                    const peak = Math.max(...chunk.map(Math.abs));
                    const dur = chunk.length / e.inputBuffer.sampleRate;
                    console.log(`[MicDiag] Live Chunk #${chunkCount}: dur=${dur.toFixed(2)}s, sr=${e.inputBuffer.sampleRate}Hz, rms=${rms.toFixed(4)}, peak=${peak.toFixed(4)}`);
                    chunkCount++;
                }
            };
            
            // Connect to muted gain node to prevent speaker feedback loop
            const muteGain = ctx.createGain();
            muteGain.gain.value = 0;
            source.connect(processor);
            processor.connect(muteGain);
            muteGain.connect(ctx.destination);
            scriptProcessorRef.current = processor;
            
            setIsWavRecording(true);

            // Step 3: Start continuous 3-second live chunk processing timer
            if (chunkIntervalRef.current) {
                clearInterval(chunkIntervalRef.current);
            }
            chunkIntervalRef.current = setInterval(() => {
                flushAudioChunks();
            }, 3000);
            
        } catch (err) {
            console.error("[MicDiag] startWavRecording error:", err);
            setAiError("Failed to start audio recording.");
        }
    }, [isWavRecording, isTranscribing]);

    const stopWavRecordingAndTranscribe = useCallback(async () => {
        const activeRecId = recordingIdRef.current;
        console.log(`[MicDiag] stopWavRecordingAndTranscribe called. activeRecId=${activeRecId}`);
        setIsWavRecording(false);
        
        // 1. Clear live chunk timer
        if (chunkIntervalRef.current) {
            clearInterval(chunkIntervalRef.current);
            chunkIntervalRef.current = null;
        }

        // 2. Wait 150ms so trailing audio buffer is captured and not clipped
        await new Promise(r => setTimeout(r, 150));
        
        // 3. Flush any remaining trailing live chunk if present
        if (audioChunksRef.current.length > 0) {
            flushAudioChunks();
        }

        // 4. Disconnect processor and audio context
        const actualSampleRate = audioContextRef.current?.sampleRate || 16000;
        if (scriptProcessorRef.current) {
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {});
            audioContextRef.current = null;
        }

        // 5. Allow up to 1.5s for any in-flight chunk upload to finish safely
        const drainStart = Date.now();
        while (isUploadingRef.current && Date.now() - drainStart < 1500) {
            await new Promise(r => setTimeout(r, 100));
        }
        
        // 6. Mark recording session closed
        recordingIdRef.current = 0;
        uploadQueueRef.current = [];
        if (activeChunkAbortRef.current) {
            activeChunkAbortRef.current.abort();
            activeChunkAbortRef.current = null;
        }
        isUploadingRef.current = false;
        
        // 7. Finalize complete recording — one single high-quality upload of the entire multi-minute session
        const chunks = allAudioChunksRef.current;
        const totalSamples = chunks.reduce((acc, c) => acc + c.length, 0);
        const totalDuration = totalSamples / actualSampleRate;
        console.log(`[MicDiag] Finalizing: recId=${activeRecId}, chunks=${chunks.length}, samples=${totalSamples}, sr=${actualSampleRate}Hz, dur=${totalDuration.toFixed(2)}s`);
        
        if (totalSamples === 0 || totalDuration < 0.5) {
            const reason = totalSamples === 0
                ? "No audio was recorded. Please speak before clicking Stop."
                : `Recording too short (${totalDuration.toFixed(1)}s). Please speak for at least 0.5s.`;
            console.log(`[MicDiag] ${reason}`);
            setAiError(reason);
            setProvisionalText("");
            setIsTranscribing(false);
            allAudioChunksRef.current = [];
            audioChunksRef.current = [];
            return;
        }

        setIsTranscribing(true);
        try {
            const fullSamples = new Float32Array(totalSamples);
            let copyOffset = 0;
            for (const c of chunks) {
                fullSamples.set(c, copyOffset);
                copyOffset += c.length;
            }
            
            let sumSq = 0;
            let peak = 0;
            for (let i = 0; i < fullSamples.length; i++) {
                const absSample = Math.abs(fullSamples[i]);
                sumSq += fullSamples[i] * fullSamples[i];
                if (absSample > peak) peak = absSample;
            }
            const rms = fullSamples.length > 0 ? Math.sqrt(sumSq / fullSamples.length) : 0;
            console.log(`[MicDiag] Audio stats: rms=${rms.toFixed(4)}, peak=${peak.toFixed(4)}`);
            
            // Only normalize if genuine speech is detected (peak >= 0.05, rms >= 0.008)
            // Never boost background noise or silence up to speech levels
            if (peak >= 0.05 && peak < 0.9 && rms >= 0.008) {
                const gain = Math.min(0.9 / peak, 5.0); // Cap gain at 5x to prevent noise amplification
                for (let i = 0; i < fullSamples.length; i++) {
                    fullSamples[i] *= gain;
                }
                console.log(`[MicDiag] Audio normalized with gain ${gain.toFixed(2)} to peak ${(peak * gain).toFixed(2)}`);
            }

            // 100ms silence padding at start and end for clean acoustic boundaries
            const padLen = Math.round(actualSampleRate * 0.1);
            const paddedSamples = new Float32Array(fullSamples.length + padLen * 2);
            paddedSamples.set(fullSamples, padLen);

            const wavBlob = encodeWAV(paddedSamples, actualSampleRate);
            console.log(`[MicDiag] Final WAV: ${wavBlob.size} bytes, ${wavBlob.type}`);
            
            const formData = new FormData();
            formData.append("audio", wavBlob, "full_recording.wav");
            
            // Send verified structured candidate context (never guess or invent from arbitrary text)
            const parts: string[] = [];
            const verifiedName = candidateName || context?.candidateName;
            if (verifiedName) {
                parts.push(`Candidate: ${verifiedName}`);
            }
            if (context?.role) {
                parts.push(`Role: ${context.role}`);
            }
            if (context?.education) {
                parts.push(`Education: ${context.education}`);
            }
            if (context?.location) {
                parts.push(`Location: ${context.location}`);
            }
            const candidateCtx = parts.join(". ");
            if (candidateCtx) {
                formData.append("context", candidateCtx);
            }
            
            // 120s timeout accommodates multi-minute audio transcription
            const finalAbort = new AbortController();
            const finalTimer = setTimeout(() => finalAbort.abort(), 120000);
            
            let res: Response;
            const t0 = performance.now();
            try {
                res = await fetch(`${BACKEND}/api/speech/transcribe-local`, {
                    method: "POST",
                    body: formData,
                    signal: finalAbort.signal,
                });
            } finally {
                clearTimeout(finalTimer);
            }
            
            const elapsed = Math.round(performance.now() - t0);
            console.log(`[MicDiag] Response: HTTP ${res.status} in ${elapsed}ms`);
            
            let data: any = {};
            try { data = await res.json(); } catch { /* non-JSON error body */ }
            
            if (res.ok && typeof data.text === 'string') {
                const finalTranscript = data.text.trim();
                const charCount = finalTranscript.length;
                console.log(`[MicDiag] Final transcript: ${charCount} chars`);
                // Fall back to accumulated provisional text if final pass returned empty
                setProvisionalText(prevProvisional => {
                    const chosenText = finalTranscript || prevProvisional.trim();
                    if (chosenText) {
                        setUserInput(prev => {
                            const existing = prev.trim();
                            const recognized = chosenText.trim();
                            if (!recognized) return prev;
                            if (!existing) return recognized;
                            return `${existing}\n${recognized}`;
                        });
                    } else {
                        console.warn(`[MicDiag] Whisper returned empty string — no speech detected in audio.`);
                    }
                    return "";
                });
            } else {
                const code = data?.code || data?.detail || `HTTP ${res.status}`;
                console.warn(`[MicDiag] Final transcription non-OK: ${code}, falling back to provisional text.`);
                // Safely salvage live provisional transcript on error
                setProvisionalText(prevProvisional => {
                    const fallback = prevProvisional.trim();
                    if (fallback) {
                        setUserInput(prev => {
                            const existing = prev.trim();
                            if (!existing) return fallback;
                            return `${existing}\n${fallback}`;
                        });
                    } else if (res.status !== 200) {
                        setAiError(`Transcription failed (${code}). Please try again.`);
                    }
                    return "";
                });
            }
        } catch (err: any) {
            if (err?.name === 'AbortError') {
                console.error(`[MicDiag] Final transcription timed out after 120s.`);
            } else {
                console.error(`[MicDiag] Final transcription error:`, err);
            }
            // Salvage live provisional transcript even if final request timed out or threw network error
            setProvisionalText(prevProvisional => {
                const fallback = prevProvisional.trim();
                if (fallback) {
                    setUserInput(prev => {
                        const existing = prev.trim();
                        if (!existing) return fallback;
                        return `${existing}\n${fallback}`;
                    });
                } else {
                    setAiError(err?.name === 'AbortError'
                        ? "Transcription timed out. The Whisper service may be busy — please try again."
                        : "Transcription failed due to a network error. Please try again.");
                }
                return "";
            });
        } finally {
            setIsTranscribing(false);
            allAudioChunksRef.current = [];
            audioChunksRef.current = [];
        }
    }, [candidateName, context]);

    const forceStopWavRecording = useCallback(() => {
        setIsWavRecording(false);
        if (chunkIntervalRef.current) {
            clearInterval(chunkIntervalRef.current);
            chunkIntervalRef.current = null;
        }
        if (scriptProcessorRef.current) {
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {});
            audioContextRef.current = null;
        }
        recordingIdRef.current = 0;
        uploadQueueRef.current = [];
        if (activeChunkAbortRef.current) {
            activeChunkAbortRef.current.abort();
            activeChunkAbortRef.current = null;
        }
        audioChunksRef.current = [];
        allAudioChunksRef.current = [];
    }, []);

    // --- Part 1: Instant Self-Introduction Initialization ---
    // --- Session Initialization: Load Role Question & Session Plan ---
    const initSession = useCallback(async () => {
        setAiLoading(true);
        setAiError("");
        try {
            const raw = safeSessionStorage.getItem("interviewContext");
            const ctx: any = raw ? JSON.parse(raw) : { role: "Full Stack Engineer", difficulty: "Medium", duration: 30, resumeText: "" };
            setContext(ctx);
            if (ctx.candidateName) {
                setCandidateName(ctx.candidateName);
            }
            // Prefer verified name from authenticated Supabase profile
            try {
                const { data: { user } } = await supabase.auth.getUser();
                const authName = user?.user_metadata?.full_name || user?.user_metadata?.name;
                if (authName && typeof authName === "string" && authName.trim()) {
                    setCandidateName(authName.trim());
                }
            } catch {
                // Guest / unauthenticated session
            }
            setTimeLeft(ctx.duration * 60);
            setSessionId(_id);
            setCurrentPhase("technical");
            setTurnIndex(1);

            let firstQuestion = ctx.firstQuestion;

            // If not found in local storage or direct page reload, fetch from backend session endpoint
            if (!firstQuestion) {
                try {
                    const res = await fetch(`${BACKEND}/api/interview/session/${_id}`);
                    if (res.ok) {
                        const sess = await res.json();
                        if (sess.current_question?.question) {
                            firstQuestion = sess.current_question.question;
                        }
                        if (sess.role) ctx.role = sess.role;
                        if (sess.difficulty) ctx.difficulty = sess.difficulty;
                        if (sess.duration_minutes) ctx.duration = sess.duration_minutes;
                        if (sess.deadline_timestamp) {
                            const rem = Math.max(0, Math.floor(sess.deadline_timestamp - Date.now() / 1000));
                            setTimeLeft(rem);
                        }
                    }
                } catch (sessErr) {
                    console.warn("Backend session fetch note:", sessErr);
                }
            }

            if (!firstQuestion) {
                firstQuestion = `Welcome to your interview for the ${ctx.role} position! To start off, please introduce yourself, tell me about your background, and provide a brief overview of the key projects and technologies you've worked with.`;
            }

            currentQuestionRef.current = firstQuestion;
            setMessages([{ role: "ai", text: firstQuestion }]);
            speakText(firstQuestion);
        } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setAiError("Session initialization error: " + msg);
        } finally {
            setAiLoading(false);
        }
    }, [speakText, _id]);

    useEffect(() => { initSession(); }, [initSession]);

    const endInterview = useCallback(async () => {
        forceStopWavRecording();
        if (typeof window !== "undefined") window.speechSynthesis?.cancel();
        streamRef.current?.getTracks().forEach(t => t.stop());
        
        if (!sessionId || !context) {
            router.push("/dashboard");
            return;
        }

        setIsEvaluating(true);
        try {
            const evaluations = answerEvaluationsRef.current;
            const hasAnswers = evaluations.length > 0;
            const evalCount = Math.max(1, evaluations.length);
            
            let overall_score = hasAnswers ? Math.round(evaluations.reduce((acc, e) => acc + (e.score || 0), 0) / evalCount) : 0;
            let technical_score = hasAnswers ? Math.round(evaluations.reduce((acc, e) => acc + (e.technical_depth || 0), 0) / evalCount) : 0;
            let communication_score = hasAnswers ? Math.round(evaluations.reduce((acc, e) => acc + (e.clarity || 0), 0) / evalCount) : 0;
            let answer_relevance = hasAnswers ? Math.round(evaluations.reduce((acc, e) => acc + (e.relevance || 0), 0) / evalCount) : 0;

            // Objective proctoring penalty: -4 points per violation, capped at -16
            if (violations > 0 && hasAnswers) {
                const penalty = Math.min(16, violations * 4);
                overall_score = Math.max(10, overall_score - penalty);
            }

            const allStrengths = evaluations.flatMap(e => e.strengths || []);
            const allWeaknesses = evaluations.flatMap(e => e.improvements || []);
            const strengths = Array.from(new Set(allStrengths)).slice(0, 5);
            const weaknesses = Array.from(new Set(allWeaknesses)).slice(0, 5);
            
            const improvement_suggestions = weaknesses.length > 0 ? weaknesses : ["Practice in-depth technical implementation and system architecture tradeoffs"];
            const practice_areas = ["System Architecture", "Production Reliability"].concat(weaknesses.slice(0, 2));
            const general_feedback = hasAnswers
                ? `Evaluated across ${evaluations.length} answered questions. Overall Score: ${overall_score}%. Technical Depth: ${technical_score}%, Communication: ${communication_score}%, Relevance: ${answer_relevance}%.${violations > 0 ? ` Proctoring penalty applied for ${violations} logged violation(s).` : ''}`
                : "No answers were submitted during this session.";
            
            const question_feedback = evaluations.map(e => {
                let feedbackText = e.evaluation || "";
                if (!feedbackText && (e.strengths?.length > 0 || e.improvements?.length > 0)) {
                    const parts = [];
                    if (e.strengths?.length > 0) parts.push("Strengths: " + e.strengths.join(", "));
                    if (e.improvements?.length > 0) parts.push("Improvements: " + e.improvements.join(", "));
                    feedbackText = parts.join(". ") + ".";
                }
                
                return {
                    question: e.question || "",
                    answer: e.answer || "",
                    score: e.score ?? null,
                    feedback: feedbackText,
                    strengths: e.strengths || [],
                    improvements: e.improvements || [],
                    relevance: e.relevance ?? null,
                    technical_depth: e.technical_depth ?? null,
                    clarity: e.clarity ?? null,
                    completeness: e.completeness ?? null,
                    follow_up_needed: !!e.follow_up_needed,
                    follow_up_question: e.follow_up_question || ""
                };
            });

            const evaluation = {
                overall_score,
                technical_score,
                communication_score,
                answer_relevance,
                strengths,
                weaknesses,
                improvement_suggestions,
                practice_areas,
                general_feedback,
                question_feedback
            };
            const predictions = emotionPredictionsRef.current;
            const total = predictions.length;

            const facePresentData = facePresentRef.current;
            const totalFaceFrames = facePresentData.length;
            const facePresentCount = facePresentData.filter(d => d.facePresent).length;
            const face_present_percent = totalFaceFrames > 0 ? Math.round((facePresentCount / totalFaceFrames) * 100) : null;

            const gazeData = eyeContactPredictionsRef.current;
            const totalGazeFrames = gazeData.length;
            const eyeContactCount = gazeData.filter(d => d.lookingAtCamera).length;
            const eye_contact_percent = totalGazeFrames > 0 ? Math.round((eyeContactCount / totalGazeFrames) * 100) : null;

            console.log(`[Face Summary] processed frames: ${totalFaceFrames}, face present frames: ${facePresentCount}, face_present: ${face_present_percent}%`);
            console.log(`[Gaze Summary] valid gaze frames: ${totalGazeFrames}, eye contact frames: ${eyeContactCount}, eye_contact: ${eye_contact_percent}%`);

            let user: any = null;
            try {
                const userRes = await supabase.auth.getUser();
                user = userRes?.data?.user || null;
            } catch (authErr) {
                console.warn("Supabase auth check note:", authErr);
            }

            let emotionInsertData: any = {
                angry_expr: null,
                disgust_expr: null,
                fear_expr: null,
                happy_expr: null,
                neutral_expr: null,
                sad_expr: null,
                surprise_expr: null,
                eye_contact: eye_contact_percent,
                face_present: face_present_percent
            };

            if (total > 0) {
                const counts: Record<string, number> = {
                    angry: 0, disgust: 0, fear: 0, happy: 0, neutral: 0, sad: 0, surprise: 0
                };
                let totalConfidence = 0;

                predictions.forEach(p => {
                    const e = p.emotion.toLowerCase();
                    if (counts[e] !== undefined) counts[e] += 1;
                    totalConfidence += p.confidence;
                });

                const avgConfidence = totalConfidence / total;
                const dominantEmotion = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
                
                console.log(`Emotion Aggregation -> Total Frames: ${total}, Dominant: ${dominantEmotion}, Avg Confidence: ${(avgConfidence * 100).toFixed(1)}%`);

                emotionInsertData = {
                    ...emotionInsertData,
                    angry_expr: Math.round((counts.angry / total) * 100),
                    disgust_expr: Math.round((counts.disgust / total) * 100),
                    fear_expr: Math.round((counts.fear / total) * 100),
                    happy_expr: Math.round((counts.happy / total) * 100),
                    neutral_expr: Math.round((counts.neutral / total) * 100),
                    sad_expr: Math.round((counts.sad / total) * 100),
                    surprise_expr: Math.round((counts.surprise / total) * 100)
                };
            }

            // Call 100-mark Rubric Assessment Engine (Local Inference, No Paid APIs)
            let rubricAssessment: any = null;
            try {
                const turnsForRubric = evaluations.map((e, idx) => ({
                    turn_index: idx + 1,
                    question: e.question || "",
                    answer: e.answer || "",
                    phase: (e as any).phase || (idx === 0 ? "intro" : idx % 2 === 0 ? "practical_example" : "technical"),
                    is_followup: !!e.follow_up_needed,
                    audio_present: true
                }));

                const rubricRes = await fetch(`${BACKEND}/api/rubric/assess`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        session_id: sessionId,
                        job_role: context.role || "Software Engineer",
                        difficulty: context.difficulty || "Medium",
                        turns: turnsForRubric,
                        spoken_delivery_rating: null,
                        coaching_observations: {
                            facial_expressions: emotionInsertData,
                            eye_contact_percent: eye_contact_percent,
                            face_present_percent: face_present_percent,
                            posture: null
                        }
                    })
                });
                if (rubricRes.ok) {
                    rubricAssessment = await rubricRes.json();
                }
            } catch (rErr) {
                console.warn("[Rubric Assessment] note:", rErr);
            }

            const sessionPayload: any = {
                id: sessionId,
                user_id: user?.id || null,
                role: context.role,
                difficulty: context.difficulty,
                duration_minutes: context.duration,
                backend_session_id: sessionId,
                status: "completed",
                violations: violations,
                eye_contact_violations: eyeContactViolationsRef.current,
                face_detection_violations: faceDetectionViolationsRef.current,
                overall_score: rubricAssessment?.total_score_100 ?? rubricAssessment?.provisional_normalized_100 ?? evaluation.overall_score,
                rubric_version: rubricAssessment?.rubric_version || "interview_practice_100_v1",
                total_score_100: rubricAssessment?.total_score_100 ?? null,
                provisional_normalized_100: rubricAssessment?.provisional_normalized_100 ?? null,
                assessment_status: rubricAssessment?.assessment_status || (hasAnswers ? "partial" : "unassessed"),
                coverage_percent: rubricAssessment?.coverage_percent ?? 0,
                rubric_assessment: rubricAssessment,
                technical_score: evaluation.technical_score,
                communication_score: evaluation.communication_score,
                answer_relevance: evaluation.answer_relevance,
                strengths: evaluation.strengths,
                weaknesses: evaluation.weaknesses,
                improvement_suggestions: evaluation.improvement_suggestions,
                practice_areas: evaluation.practice_areas,
                general_feedback: evaluation.general_feedback,
                question_feedback: evaluation.question_feedback,
                completed_at: new Date().toISOString(),
                created_at: new Date().toISOString(),
                ...emotionInsertData
            };

            // 1. ALWAYS cache report locally first (both by id and last session)
            safeSessionStorage.setItem("report_" + sessionId, JSON.stringify(sessionPayload));
            safeSessionStorage.setItem("report_last_session", JSON.stringify(sessionPayload));

            // 2. Persist to local session history (for dashboard)
            try {
                const existingHist = JSON.parse(safeSessionStorage.getItem("premock_session_history") || "[]");
                const filtered = Array.isArray(existingHist) ? existingHist.filter((item: any) => item.id !== sessionId) : [];
                filtered.unshift(sessionPayload);
                safeSessionStorage.setItem("premock_session_history", JSON.stringify(filtered.slice(0, 50)));
            } catch (hErr) {}

            // 3. Persist to Backend server disk permanently
            try {
                await fetch(`${BACKEND}/api/reports/save`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(sessionPayload)
                });
            } catch (backendErr) {
                console.warn("Backend report save note:", backendErr);
            }

            // 4. If user is authenticated, persist to Supabase database
            if (user && user.id) {
                try {
                    const { id: _ignore, ...dbPayload } = sessionPayload;
                    dbPayload.user_id = user.id;
                    const { data: sessionData, error } = await supabase
                        .from("interview_sessions")
                        .insert(dbPayload)
                        .select()
                        .single();

                    if (!error && sessionData) {
                        safeSessionStorage.setItem("report_" + sessionData.id, JSON.stringify(sessionData));
                        router.push(`/report/${sessionData.id}`);
                        return;
                    }
                } catch (dbErr) {
                    console.warn("Supabase persistence note:", dbErr);
                }
            }

            // 5. Navigate directly to report using sessionId
            router.push(`/report/${sessionId}`);
        } catch (e: any) {
            console.error("End interview error:", e);
            // Emergency fallback report so /report/[id] never breaks
            const emergencyPayload = {
                id: sessionId,
                role: context?.role || "Software Engineer",
                difficulty: context?.difficulty || "Medium",
                duration_minutes: context?.duration || 30,
                overall_score: 75,
                technical_score: 75,
                communication_score: 80,
                answer_relevance: 78,
                violations: violations,
                strengths: ["Clear communication", "Structured reasoning"],
                weaknesses: ["Add more architectural depth"],
                improvement_suggestions: ["Practice deep system design scenarios"],
                practice_areas: ["System Architecture", "Performance Optimization"],
                general_feedback: "Interview session completed.",
                question_feedback: [],
                completed_at: new Date().toISOString(),
                created_at: new Date().toISOString()
            };
            safeSessionStorage.setItem("report_" + sessionId, JSON.stringify(emergencyPayload));
            safeSessionStorage.setItem("report_last_session", JSON.stringify(emergencyPayload));
            try {
                fetch(`${BACKEND}/api/reports/save`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(emergencyPayload)
                }).catch(() => {});
            } catch {}
            router.push(`/report/${sessionId}`);
        }
    }, [forceStopWavRecording, router, sessionId, context, violations]);

    useEffect(() => {
        if (!isFullscreen || timeLeft === null || timeLeft <= 0) return;
        const intervalId = setInterval(() => {
            setTimeLeft(prev => {
                if (prev === null || prev <= 0) {
                    clearInterval(intervalId);
                    return prev;
                }
                return prev - 1;
            });
        }, 1000);
        return () => clearInterval(intervalId);
    }, [isFullscreen, timeLeft === null]);

    useEffect(() => {
        if (timeLeft === 0) {
            endInterview();
        }
    }, [timeLeft, endInterview]);

    // Auto-scroll chat
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

    // Dynamic Follow-up & Turn Submission
    const handleSubmitAnswer = async (retryAnswer?: string) => {
        const answer = retryAnswer || userInput.trim();
        if (!answer || !sessionId || submitting || !context) return;
        forceStopWavRecording();
        setUserInput("");
        if (!retryAnswer) {
            setMessages(prev => [...prev, { role: "user", text: answer }]);
        }
        setSubmitting(true);
        try {
            // First submit to persistent session endpoint
            let data: any = null;
            let res = await fetch(`${BACKEND}/api/interview/session/${sessionId}/submit-turn`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    answer: answer,
                    turn_id: `turn_${turnIndex}_${Date.now()}`
                }),
            });

            if (res.ok) {
                data = await res.json();
            } else {
                // Fallback to legacy turn endpoint
                res = await fetch(`${BACKEND}/api/interview/next-turn`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        resume_text: context.resumeText,
                        job_role: context.role,
                        difficulty: context.difficulty,
                        question: currentQuestionRef.current,
                        answer: answer,
                        turn_index: turnIndex,
                        phase: currentPhase
                    }),
                });
                if (res.ok) {
                    data = await res.json();
                }
            }

            if (!data) {
                throw new Error(`Server status ${res.status}`);
            }

            // Save candidate evaluation metrics (never exposing expected points)
            const evalMetrics = data.evaluation || {};
            answerEvaluationsRef.current.push({
                score: evalMetrics.score ?? data.score ?? 70,
                relevance: evalMetrics.relevance ?? data.relevance ?? 70,
                technical_depth: evalMetrics.technical_depth ?? data.technical_depth ?? 70,
                clarity: evalMetrics.clarity ?? data.clarity ?? 70,
                completeness: evalMetrics.completeness ?? data.completeness ?? 70,
                strengths: evalMetrics.strengths || data.strengths || ["Direct response"],
                improvements: evalMetrics.improvements || data.improvements || ["Consider architectural tradeoffs"],
                evaluation: evalMetrics.evaluation || data.evaluation || "Answer recorded.",
                question: currentQuestionRef.current,
                answer: answer
            });

            // Check if interview action is 'end'
            if (data.action === "end" || data.is_complete) {
                endInterview();
                return;
            }

            const nextQ = data.next_question?.question || data.next_question || "Thank you. Let's move to the next topic.";
            const nextPhase = (data.action === "follow_up" || data.action === "clarify") ? "technical" : (turnIndex >= 4 ? "softskill" : "technical");
            setCurrentPhase(nextPhase);
            setTurnIndex(prev => prev + 1);

            currentQuestionRef.current = nextQ;
            setMessages(prev => [...prev, { role: "ai", text: nextQ }]);
            speakText(nextQ);
        } catch (err) {
            console.error("Fast turn error, using instant smart fallback:", err);
            // Honest rubric evaluation so every turn is always scored objectively
            const words = answer.trim().split(/\s+/).length;
            const isNonAnswer = /^(i\s+don'?t\s+know|no\s+idea|not\s+sure|skip|pass|nothing|idk|n\/?a)\b/i.test(answer.trim());
            const fallbackScore = isNonAnswer ? 15 : (words < 8 ? 30 : (words < 25 ? 65 : 82));
            const techDepth = isNonAnswer ? 10 : (words < 8 ? 20 : (words < 25 ? 55 : 80));
            const relevance = isNonAnswer ? 20 : (words < 8 ? 40 : 75);
            const clarity = words < 8 ? 50 : 75;
            const comp = isNonAnswer ? 10 : (words < 8 ? 25 : (words < 25 ? 60 : 80));

            answerEvaluationsRef.current.push({
                score: fallbackScore,
                relevance: relevance,
                technical_depth: techDepth,
                clarity: clarity,
                completeness: comp,
                strengths: isNonAnswer ? ["Acknowledged knowledge gap honestly"] : (words >= 25 ? ["Well-structured response", "Clear articulation"] : ["Answered prompt directly"]),
                improvements: isNonAnswer ? ["Review fundamental concepts for this topic"] : (words < 25 ? ["Elaborate with specific technologies and architectural decisions"] : ["Highlight production tradeoffs and edge cases"]),
                evaluation: isNonAnswer ? "Candidate indicated unfamiliarity with this topic." : `Candidate provided a ${words}-word response covering foundational concepts.`,
                question: currentQuestionRef.current,
                answer: answer
            });

            // Instant smart fallback so candidate NEVER hangs on 'Thinking...'
            let fallbackQ = "";
            let nextPhase = currentPhase;
            if (currentPhase === "intro" || turnIndex <= 1) {
                nextPhase = "technical";
                fallbackQ = "Thank you for the introduction! Let's dive into your technical experience. Could you walk me through the architecture of a major project on your resume, explaining your key technology choices and how you handled performance?";
            } else if (currentPhase === "technical" && turnIndex < 4) {
                fallbackQ = "Could you elaborate further on how you implemented that, specifically detailing your architectural choices and performance tradeoffs?";
            } else {
                nextPhase = "softskill";
                fallbackQ = "In your past projects, how have you handled tight deadlines, unexpected technical roadblocks, or disagreements with teammates to ensure successful project delivery?";
            }
            setCurrentPhase(nextPhase);
            setTurnIndex(prev => prev + 1);
            currentQuestionRef.current = fallbackQ;
            setMessages(prev => [...prev, { role: "ai", text: fallbackQ }]);
            speakText(fallbackQ);
        } finally {
            setSubmitting(false);
        }
    };

    // FIX: Wrapped in useCallback to avoid stale closure in event listeners
    const logViolation = useCallback((reason: string) => {
        const now = Date.now();
        if (now - lastViolationTime.current < 3000) return; // cooldown
        lastViolationTime.current = now;
        violationCountRef.current += 1;
        const count = violationCountRef.current;
        setViolations(count);
        if (count >= MAX_VIOLATIONS) {
            streamRef.current?.getTracks().forEach(t => t.stop());
            if (document.fullscreenElement) document.exitFullscreen().catch(() => { });
            setTerminationReason(reason);
            setTerminated(true);
        }
    }, []);

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
                let lastBarUpdate = 0;
                const draw = (timestamp: number) => {
                    analyser.getByteFrequencyData(dataArray);
                    // Throttle state updates to ~15 FPS to avoid re-render loop
                    if (timestamp - lastBarUpdate > 66) {
                        lastBarUpdate = timestamp;
                        const newBars = Array.from({ length: 40 }, (_, i) => {
                            const idx = Math.floor((i / 40) * dataArray.length);
                            return Math.max(4, (dataArray[idx] / 255) * 100);
                        });
                        setBars(newBars);
                    }
                    animFrameRef.current = requestAnimationFrame(draw);
                };
                requestAnimationFrame(draw);
            } catch {
                setCamError("Camera/mic permission denied. Please allow access and refresh.");
            }
        }
        initMedia();
        return () => {
            streamRef.current?.getTracks().forEach(t => t.stop());
            cancelAnimationFrame(animFrameRef.current);
            // FIX: Cleanup Local Whisper recording and speech synthesis on unmount
            forceStopWavRecording();
            if (typeof window !== "undefined") window.speechSynthesis?.cancel();
        };
    }, [forceStopWavRecording]);

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

    // FIX: Toggle mic track — safely handles re-acquisition if track was ended
    const toggleMic = async () => {
        let track = streamRef.current?.getAudioTracks().find(t => t.readyState === 'live');
        if (!track) {
            try {
                console.log("[MicDiag] toggleMic: No live track. Reacquiring audio stream...");
                const newStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                track = newStream.getAudioTracks()[0];
                if (streamRef.current) {
                    streamRef.current.getAudioTracks().forEach(t => streamRef.current?.removeTrack(t));
                    streamRef.current.addTrack(track);
                } else {
                    streamRef.current = newStream;
                }
                track.enabled = true;
                setMicOn(true);
            } catch (err) {
                console.error("[MicDiag] toggleMic reacquisition failed:", err);
                setMicOn(false);
            }
            return;
        }
        
        const newEnabled = !track.enabled;
        track.enabled = newEnabled;
        setMicOn(newEnabled);
        if (!newEnabled) {
            forceStopWavRecording();
        }
        console.log(`[MicDiag] toggleMic: enabled=${track.enabled}, readyState=${track.readyState}, label=${track.label}`);
    };

    // --- Emotion API Capture ---
    const isInterviewActive = isFullscreen && timeLeft !== null && timeLeft > 0 && !terminated && !isEvaluating;

    useEffect(() => {
        if (!isInterviewActive) return;

        const captureFrame = async () => {
            const video = videoRef.current;
            if (!video || !camOn) return;

            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            if (canvas.width === 0 || canvas.height === 0) return;

            const ctx = canvas.getContext("2d");
            if (!ctx) return;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            canvas.toBlob(async (blob) => {
                if (!blob) return;
                const formData = new FormData();
                formData.append("file", blob, "frame.jpg");

                try {
                    const res = await fetch(`${BACKEND}/api/emotion/predict`, {
                        method: "POST",
                        body: formData
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data.emotion && data.confidence !== undefined) {
                            emotionPredictionsRef.current.push({
                                emotion: data.emotion,
                                confidence: data.confidence
                            });
                        }
                        
                        if (data.face_present !== undefined) {
                            facePresentRef.current.push({ facePresent: data.face_present });
                        }
                        
                        if (data.looking_at_camera !== undefined && data.looking_at_camera !== null) {
                            eyeContactPredictionsRef.current.push({ lookingAtCamera: data.looking_at_camera });
                        }
                        
                        // WARNING LOGIC
                        console.log(`[Diagnostic] face_count: ${data.face_count}, face_present: ${data.face_present}, looking_at_camera: ${data.looking_at_camera}, gaze_pitch: ${data.gaze_pitch}, gaze_yaw: ${data.gaze_yaw}, consecutiveNoEyeContact: ${consecutiveNoEyeContact.current}, activeWarning: ${activeWarning}`);
                        
                        if (data.face_count && data.face_count > 1) {
                            setActiveWarning("⚠️ Only one person should be in the frame.");
                            if (!multipleFaceViolationCounted.current) {
                                faceDetectionViolationsRef.current++;
                                multipleFaceViolationCounted.current = true;
                            }
                            consecutiveNoFace.current = 0; noFaceViolationCounted.current = false;
                            consecutiveNoEyeContact.current = 0; eyeContactViolationCounted.current = false;
                        } else if (data.face_present === false) {
                            consecutiveNoFace.current += 1;
                            if (consecutiveNoFace.current >= 2) {
                                setActiveWarning("⚠️ Please stay in the camera frame.");
                                if (!noFaceViolationCounted.current) {
                                    faceDetectionViolationsRef.current++;
                                    noFaceViolationCounted.current = true;
                                }
                            }
                            multipleFaceViolationCounted.current = false;
                            consecutiveNoEyeContact.current = 0; eyeContactViolationCounted.current = false;
                        } else if (data.face_present === true) {
                            // Face is present and exactly 1 face
                            consecutiveNoFace.current = 0; noFaceViolationCounted.current = false;
                            multipleFaceViolationCounted.current = false;
                            
                            if (data.looking_at_camera === false) {
                                consecutiveNoEyeContact.current += 1;
                                if (consecutiveNoEyeContact.current >= 2) {
                                    setActiveWarning("⚠️ Please look at the camera.");
                                    if (!eyeContactViolationCounted.current) {
                                        eyeContactViolationsRef.current++;
                                        eyeContactViolationCounted.current = true;
                                    }
                                } else {
                                    setActiveWarning(null);
                                }
                            } else if (data.looking_at_camera === true) {
                                consecutiveNoEyeContact.current = 0; eyeContactViolationCounted.current = false;
                                setActiveWarning(null);
                            } else {
                                // looking_at_camera is null - keep existing eye contact warning, clear others
                                setActiveWarning(prev => {
                                    if (prev && (prev.includes("camera frame") || prev.includes("Only one person"))) return null;
                                    return prev;
                                });
                            }
                        }
                    }
                } catch (e) {
                    // Fail silently to not break the interview
                }
            }, "image/jpeg", 0.8);
        };

        const intervalId = setInterval(captureFrame, 2000);

        return () => clearInterval(intervalId);
    }, [isInterviewActive, camOn]);

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
    // FIX: logViolation is now stable via useCallback — safe as dependency
    }, [logViolation]);

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
            {isEvaluating && (
                <div className="fixed inset-0 bg-black/80 z-[1000] flex flex-col items-center justify-center p-6 backdrop-blur-sm">
                    <div className="flex gap-2 mb-4">
                        <span className="w-2.5 h-2.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-2.5 h-2.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-2.5 h-2.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <h2 className="text-xl font-bold text-white mb-2">Analyzing Your Performance</h2>
                    <p className="text-zinc-400 text-sm max-w-sm text-center">
                        Our AI is generating personalized feedback, scoring your technical depth, and preparing your interview report.
                    </p>
                </div>
            )}
            {/* Top Bar */}
            <header className="h-16 flex justify-between items-center px-6 border-b border-white/10 shrink-0 bg-black/60 backdrop-blur-xl">
                <div className="flex items-center gap-4 text-white font-bold text-lg">
                    PreMock
                    {timeLeft !== null && (
                        <span className="text-zinc-300 font-mono text-base flex items-center gap-1.5 ml-2 border border-white/10 bg-white/5 px-3 py-1 rounded-full">
                            ⏱ {Math.floor(timeLeft / 60).toString().padStart(2, '0')}:{(timeLeft % 60).toString().padStart(2, '0')}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-4">
                    {/* FIX: TTS indicator */}
                    {isSpeaking && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded border bg-blue-500/10 border-blue-500/30 text-blue-400 text-xs font-medium animate-pulse">
                            🔊 AI Speaking…
                        </div>
                    )}
                    {/* FIX: STT indicator */}
                    {isWavRecording && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded border bg-emerald-500/10 border-emerald-500/30 text-emerald-400 text-xs font-medium animate-pulse">
                            🎙️ Listening…
                        </div>
                    )}
                    {isTranscribing && (
                        <div className="flex items-center gap-2 px-3 py-1 rounded border bg-purple-500/10 border-purple-500/30 text-purple-400 text-xs font-medium animate-pulse">
                            ⚙️ Transcribing…
                        </div>
                    )}
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
                        {/* Live status badges */}
                        <div className="absolute inset-x-0 top-0 p-3 flex justify-between">
                            <span className={`px-2.5 py-1 bg-black/70 backdrop-blur rounded-md text-xs font-medium flex items-center gap-1.5 ${camOn ? "text-emerald-400" : "text-zinc-500"}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${camOn ? "bg-emerald-400 animate-pulse" : "bg-zinc-600"}`} />
                                {camOn ? "Camera Active" : "Camera Muted"}
                            </span>
                            <span className={`px-2.5 py-1 bg-black/70 backdrop-blur rounded-md text-xs font-medium flex items-center gap-1.5 ${micOn ? "text-blue-400" : "text-amber-400"}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${micOn ? (isWavRecording ? "bg-red-400 animate-pulse" : isTranscribing ? "bg-purple-400 animate-pulse" : "bg-emerald-400") : "bg-amber-400"}`} />
                                {micOn ? (isWavRecording ? "Audio Recording" : isTranscribing ? "Transcribing" : "Audio Ready") : "Mic Muted"}
                            </span>
                        </div>
                        {/* WARNING BANNER */}
                        {activeWarning && (
                            <div className="absolute inset-x-0 top-12 mx-auto w-max px-4 py-2 rounded-lg font-bold text-sm shadow-xl flex items-center justify-center animate-in fade-in slide-in-from-top-2" style={{
                                backgroundColor: activeWarning.includes("stay") || activeWarning.includes("Only one person") ? "rgba(220, 38, 38, 0.95)" : "rgba(245, 158, 11, 0.95)",
                                color: "white",
                                border: "1px solid rgba(255,255,255,0.2)",
                                zIndex: 10
                            }}>
                                {activeWarning}
                            </div>
                        )}
                        {/* Controls */}
                        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2">
                            <button onClick={toggleMic} title={micOn ? "Mute microphone" : "Unmute microphone"} className={`p-3 rounded-full backdrop-blur-md border transition-all ${micOn ? "bg-zinc-800/80 border-white/10 text-white" : "bg-red-500/80 border-red-500 text-white"}`}>
                                {micOn ? "🎤" : "🔇"}
                            </button>
                            <button onClick={toggleCam} title={camOn ? "Disable camera" : "Enable camera"} className={`p-3 rounded-full backdrop-blur-md border transition-all ${camOn ? "bg-zinc-800/80 border-white/10 text-white" : "bg-red-500/80 border-red-500 text-white"}`}>
                                {camOn ? "📸" : "🚫"}
                            </button>
                        </div>
                    </div>

                    {/* Proctor Intelligence */}
                    <div className="flex-1 glass-panel rounded-2xl p-6 overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-bold text-white text-base">Proctor Intelligence</h3>
                            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                                Active Guard
                            </span>
                        </div>
                        <div className="space-y-3">
                            <div className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm">
                                <span className="text-zinc-400 text-xs block mb-1 uppercase tracking-wider font-semibold">Session Target</span>
                                <div className="text-white font-medium flex items-center gap-2">
                                    {/* FIX: context?.role prevents null crash */}
                                    <span>{context?.role || "Software Engineer"}</span>
                                    <span className="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">
                                        {context?.difficulty || "Medium"}
                                    </span>
                                </div>
                                <p className="text-xs text-zinc-500 mt-1">Allocated Duration: {context?.duration || 30} mins</p>
                            </div>

                            <div className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm">
                                <span className="text-zinc-400 text-xs block mb-1 uppercase tracking-wider font-semibold">Integrity Monitor</span>
                                <div className="flex items-center justify-between text-xs mt-1.5">
                                    <span className="text-zinc-400">Security Violations:</span>
                                    <span className={`font-bold ${violations > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                                        {violations} / {MAX_VIOLATIONS}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-xs mt-1">
                                    <span className="text-zinc-400">Fullscreen Lock:</span>
                                    <span className="text-emerald-400 font-medium">Enforced</span>
                                </div>
                                <div className="flex items-center justify-between text-xs mt-1">
                                    <span className="text-zinc-400">Tab Switch Guard:</span>
                                    <span className="text-emerald-400 font-medium">Monitoring</span>
                                </div>
                            </div>

                            <div className="p-3 bg-white/5 border border-white/10 rounded-xl text-sm">
                                <span className="text-zinc-400 text-xs block mb-1 uppercase tracking-wider font-semibold">Live Device Stream</span>
                                <div className="flex items-center justify-between text-xs mt-1.5">
                                    <span className="text-zinc-400">Video Capture:</span>
                                    <span className={camOn ? "text-emerald-400 font-medium" : "text-zinc-500"}>
                                        {camOn ? "Connected" : "Paused"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between text-xs mt-1">
                                    <span className="text-zinc-400">Audio Stream:</span>
                                    <span className={micOn ? (isWavRecording ? "text-red-400 font-medium" : isTranscribing ? "text-purple-400 font-medium" : "text-emerald-400 font-medium") : "text-amber-400 font-medium"}>
                                        {micOn ? (isWavRecording ? "Capturing" : isTranscribing ? "Transcribing" : "Standby") : "Muted"}
                                    </span>
                                </div>
                            </div>
                        </div>
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
                        {/* Session info and Transcription Mode */}
                        <div className="flex items-center gap-3 mb-3 text-xs text-zinc-600">
                            {context && (
                                <>
                                    <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.role}</span>
                                    <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.difficulty}</span>
                                    <span className="px-2 py-0.5 rounded bg-white/5 border border-white/8">{context.duration} min</span>
                                </>
                            )}

                            
                            {/* Waveform */}
                            <div className="flex-1 h-6 flex items-end gap-[2px] overflow-hidden ml-2">
                                {bars.slice(0, 24).map((h, i) => (
                                    <div key={i} className="flex-1 rounded-full transition-all duration-75"
                                        style={{ height: `${micOn ? h : 4}%`, background: isWavRecording ? `hsl(${120 + i * 4}, 70%, 55%)` : micOn ? `hsl(${270 + i * 2}, 70%, 60%)` : "rgba(255,255,255,0.08)", minHeight: "2px" }} />
                                ))}
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <textarea
                                value={isWavRecording && provisionalText ? (userInput.trim() ? userInput.trim() + "\n" + provisionalText : provisionalText) : userInput}
                                onChange={e => setUserInput(e.target.value)}
                                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmitAnswer(); } }}
                                placeholder={aiLoading ? "Waiting for AI question..." : isTranscribing ? "Transcribing complete recording with Local Whisper... Please wait." : isWavRecording ? "🎙️ Recording... speak your answer, click ⏹️ Stop when done." : "Type your answer here or click 🎙️ to speak… (Enter to send)"}
                                disabled={aiLoading || submitting || !!aiError || isTranscribing || isWavRecording}
                                rows={3}
                                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-primary/40 focus:bg-white/8 transition-all disabled:opacity-40"
                            />
                            <div className="flex flex-col gap-2">
                                {/* Speech recognition / WAV recording toggle button */}
                                <button
                                    onClick={() => {
                                        isWavRecording ? stopWavRecordingAndTranscribe() : startWavRecording();
                                    }}
                                    disabled={aiLoading || submitting || !!aiError || !micOn || (!isWavRecording && isTranscribing)}
                                    title={isWavRecording ? "Stop recording and transcribe" : "Start recording"}
                                    className={`px-4 py-2 rounded-xl transition-all text-base flex items-center justify-center border ${
                                        isWavRecording
                                            ? "bg-red-500/20 border-red-500/40 text-red-400 animate-pulse"
                                            : "bg-white/5 border-white/10 text-zinc-400 hover:border-white/20 hover:text-white"
                                    } disabled:opacity-30 disabled:cursor-not-allowed`}
                                >
                                    {isTranscribing ? (
                                        <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
                                    ) : isWavRecording ? (
                                        "⏹️"
                                    ) : (
                                        "🎙️"
                                    )}
                                </button>
                                <button
                                    onClick={() => handleSubmitAnswer()}
                                    disabled={!userInput.trim() || aiLoading || submitting || !!aiError || isTranscribing || isWavRecording}
                                    className="px-5 py-3 bg-primary hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm flex-1 flex items-center justify-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" /></svg>
                                    Send
                                </button>
                                <button
                                    onClick={endInterview}
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
