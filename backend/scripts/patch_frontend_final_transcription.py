import re

with open('frontend/src/app/interview/[id]/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add allAudioChunksRef
refs_target = """    const audioChunksRef = useRef<Float32Array[]>([]);"""
refs_replacement = """    const audioChunksRef = useRef<Float32Array[]>([]);
    const allAudioChunksRef = useRef<Float32Array[]>([]);"""
content = content.replace(refs_target, refs_replacement)

# 2. Modify flushAudioChunks
flush_target = r"    const flushAudioChunks = \(isFinal: boolean\) => \{.*?    const wavBlob = encodeWAV\(samples, 16000\);"
flush_replacement = """    const flushAudioChunks = (isFinal: boolean, sr?: number) => {
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
        
        const actualSampleRate = sr || audioContextRef.current?.sampleRate || 16000;
        const wavBlob = encodeWAV(samples, actualSampleRate);"""
content = re.sub(flush_target, flush_replacement, content, flags=re.DOTALL)

# 3. Modify startWavRecording to push to allAudioChunksRef
start_target = """            processor.onaudioprocess = (e) => {
                const channelData = e.inputBuffer.getChannelData(0);
                audioChunksRef.current.push(new Float32Array(channelData));
            };"""
start_replacement = """            processor.onaudioprocess = (e) => {
                const channelData = e.inputBuffer.getChannelData(0);
                const chunk = new Float32Array(channelData);
                audioChunksRef.current.push(chunk);
                allAudioChunksRef.current.push(chunk);
            };"""
content = content.replace(start_target, start_replacement)

# 4. Modify startWavRecording to clear allAudioChunksRef
clear_target = """            audioChunksRef.current = [];
            uploadQueueRef.current = [];"""
clear_replacement = """            audioChunksRef.current = [];
            allAudioChunksRef.current = [];
            uploadQueueRef.current = [];"""
content = content.replace(clear_target, clear_replacement)

# 5. Rewrite stopWavRecordingAndTranscribe
stop_target = r"    const stopWavRecordingAndTranscribe = useCallback\(async \(\) => \{.*?        flushAudioChunks\(true\);\n    \}, \[\]\);"
stop_replacement = """    const stopWavRecordingAndTranscribe = useCallback(async () => {
        setIsWavRecording(false);
        if (chunkIntervalRef.current) {
            clearInterval(chunkIntervalRef.current);
            chunkIntervalRef.current = null;
        }
        
        const actualSampleRate = audioContextRef.current?.sampleRate || 16000;
        
        if (scriptProcessorRef.current) {
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        
        // Finalize chunking queue
        flushAudioChunks(true, actualSampleRate);
        
        // Wait for chunk queue to finish
        while (isUploadingRef.current || uploadQueueRef.current.length > 0) {
            await new Promise(r => setTimeout(r, 200));
        }
        
        // Run full transcription
        setIsTranscribing(true);
        try {
            const chunks = allAudioChunksRef.current;
            if (chunks.length > 0) {
                const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
                const samples = new Float32Array(totalLength);
                let offset = 0;
                for (let chunk of chunks) {
                    samples.set(chunk, offset);
                    offset += chunk.length;
                }
                
                const wavBlob = encodeWAV(samples, actualSampleRate);
                const formData = new FormData();
                formData.append("audio", wavBlob, "full_recording.wav");
                const res = await fetch(`${BACKEND}/api/speech/transcribe-local`, {
                    method: "POST",
                    body: formData,
                });
                const data = await res.json();
                if (res.ok && data.text) {
                    // REPLACE provisional transcript
                    setUserInput(data.text);
                }
            }
        } catch (err) {
            console.error("Full transcription error", err);
        } finally {
            setIsTranscribing(false);
        }
    }, []);"""
content = re.sub(stop_target, stop_replacement, content, flags=re.DOTALL)

with open('frontend/src/app/interview/[id]/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to page.tsx")
