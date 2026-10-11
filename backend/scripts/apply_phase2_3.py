import re
import os

# 1. Update whisper_engine.py (Hallucination reduction)
with open('ml/asr_service/whisper_engine.py', 'r', encoding='utf-8') as f:
    we_content = f.read()

generate_target = """            generated = self.model.generate(
                inputs,
                forced_decoder_ids=forced_ids,
                max_new_tokens=225
            )"""
generate_replacement = """            generated = self.model.generate(
                inputs,
                forced_decoder_ids=forced_ids,
                max_new_tokens=225,
                condition_on_prev_tokens=False
            )"""
we_content = we_content.replace(generate_target, generate_replacement)

transcription_target = """        transcription = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        return transcription"""
transcription_replacement = """        transcription = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        
        # Hallucination filter
        lower_t = transcription.lower()
        hallucinations = ["thank you.", "thank you", "bye.", "bye", "you", "subscribe", "subtitles by"]
        if lower_t in hallucinations or transcription.startswith("Thank you for watching"):
            return ""
            
        return transcription"""
we_content = we_content.replace(transcription_target, transcription_replacement)

with open('ml/asr_service/whisper_engine.py', 'w', encoding='utf-8') as f:
    f.write(we_content)


# 2. Update asr_server.py (VAD)
with open('ml/asr_service/asr_server.py', 'r', encoding='utf-8') as f:
    asr_content = f.read()

vad_target = """        # soundfile returns 2D array if stereo, we need mono
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        duration = len(audio_data) / sample_rate"""
vad_replacement = """        # soundfile returns 2D array if stereo, we need mono
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
            
        # Basic VAD using RMS and Max Amplitude
        rms = np.sqrt(np.mean(audio_data**2))
        max_amp = np.max(np.abs(audio_data))
        if rms < 0.001 or max_amp < 0.005:
            return JSONResponse(status_code=200, content={"error": "No speech detected", "code": "NO_SPEECH_DETECTED", "text": ""})
            
        duration = len(audio_data) / sample_rate"""
asr_content = asr_content.replace(vad_target, vad_replacement)

with open('ml/asr_service/asr_server.py', 'w', encoding='utf-8') as f:
    f.write(asr_content)


# 3. Update frontend page.tsx
with open('frontend/src/app/interview/[id]/page.tsx', 'r', encoding='utf-8') as f:
    page_content = f.read()

# Add queue refs and mergeTranscripts
refs_target = """    const audioContextRef = useRef<AudioContext | null>(null);
    const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
    const audioChunksRef = useRef<Float32Array[]>([]);"""
refs_replacement = """    const audioContextRef = useRef<AudioContext | null>(null);
    const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
    const audioChunksRef = useRef<Float32Array[]>([]);
    
    // Streaming refs
    const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const uploadQueueRef = useRef<Blob[]>([]);
    const isUploadingRef = useRef(false);

    const mergeTranscripts = (existing: string, next: string) => {
        if (!existing) return next.trim();
        if (!next) return existing;
        
        const w1 = existing.trim().split(/\s+/);
        const w2 = next.trim().split(/\s+/);
        
        let overlap = 0;
        for (let i = 1; i <= Math.min(w1.length, w2.length, 4); i++) {
            const endW1 = w1.slice(-i).join(" ").toLowerCase().replace(/[^a-z]/g, '');
            const startW2 = w2.slice(0, i).join(" ").toLowerCase().replace(/[^a-z]/g, '');
            if (endW1 === startW2 && endW1.length > 0) {
                overlap = i;
            }
        }
        
        if (overlap > 0) {
            return existing.trim() + " " + w2.slice(overlap).join(" ");
        }
        return existing.trim() + " " + next.trim();
    };
"""
page_content = page_content.replace(refs_target, refs_replacement)

# Replace startWavRecording and stopWavRecordingAndTranscribe
methods_regex = r'    const startWavRecording = useCallback\(\(\) => \{.*?    const forceStopWavRecording = useCallback\(\(\) => \{'
methods_replacement = """    const processUploadQueue = async () => {
        if (isUploadingRef.current || uploadQueueRef.current.length === 0) return;
        isUploadingRef.current = true;
        
        while (uploadQueueRef.current.length > 0) {
            const blob = uploadQueueRef.current.shift();
            if (!blob) continue;
            
            setIsTranscribing(true);
            try {
                const formData = new FormData();
                formData.append("audio", blob, "chunk.wav");
                const res = await fetch(`${BACKEND}/api/speech/transcribe-local`, {
                    method: "POST",
                    body: formData,
                });
                const data = await res.json();
                if (res.ok && data.text) {
                    setUserInput(prev => mergeTranscripts(prev, data.text));
                }
            } catch (err) {
                console.error("Chunk upload error", err);
            } finally {
                setIsTranscribing(false);
            }
        }
        isUploadingRef.current = false;
    };

    const flushAudioChunks = (isFinal: boolean) => {
        const chunks = audioChunksRef.current;
        if (chunks.length === 0) return;
        
        const overlapCount = 2; // ~0.5s overlap
        audioChunksRef.current = isFinal ? [] : chunks.slice(-overlapCount);
        
        const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const samples = new Float32Array(totalLength);
        let offset = 0;
        for (let chunk of chunks) {
            samples.set(chunk, offset);
            offset += chunk.length;
        }
        
        const wavBlob = encodeWAV(samples, 16000);
        
        if (uploadQueueRef.current.length < 10) {
            uploadQueueRef.current.push(wavBlob);
            processUploadQueue();
        }
    };

    const startWavRecording = useCallback(() => {
        if (!streamRef.current) {
            setAiError("Microphone not available.");
            return;
        }
        try {
            audioChunksRef.current = [];
            uploadQueueRef.current = [];
            isUploadingRef.current = false;
            
            const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            audioContextRef.current = ctx;
            const source = ctx.createMediaStreamSource(streamRef.current);
            const processor = ctx.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                const channelData = e.inputBuffer.getChannelData(0);
                audioChunksRef.current.push(new Float32Array(channelData));
            };
            
            source.connect(processor);
            processor.connect(ctx.destination);
            scriptProcessorRef.current = processor;
            
            setIsWavRecording(true);
            
            if (chunkIntervalRef.current) clearInterval(chunkIntervalRef.current);
            chunkIntervalRef.current = setInterval(() => {
                flushAudioChunks(false);
            }, 3000);
            
        } catch (err) {
            console.error("WAV Recording Error:", err);
            setAiError("Failed to start WAV recorder.");
        }
    }, []);

    const stopWavRecordingAndTranscribe = useCallback(async () => {
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
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        
        flushAudioChunks(true);
    }, []);

    const forceStopWavRecording = useCallback(() => {"""
page_content = re.sub(methods_regex, methods_replacement, page_content, flags=re.DOTALL)

# Add interval clearing to forceStopWavRecording
force_target = """    const forceStopWavRecording = useCallback(() => {
        setIsWavRecording(false);"""
force_replacement = """    const forceStopWavRecording = useCallback(() => {
        setIsWavRecording(false);
        if (chunkIntervalRef.current) clearInterval(chunkIntervalRef.current);"""
page_content = page_content.replace(force_target, force_replacement)

with open('frontend/src/app/interview/[id]/page.tsx', 'w', encoding='utf-8') as f:
    f.write(page_content)

print("Phase 2 and 3 scripts generated and applied.")
