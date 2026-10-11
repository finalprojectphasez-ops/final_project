import re

with open('frontend/src/app/interview/[id]/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove Window interface for webkitSpeechRecognition
content = re.sub(r'// FIX: Extend Window.*?\n}\n', '', content, flags=re.DOTALL)

# 2. State cleanup
content = content.replace('    const [isListening, setIsListening] = useState(false);\n', '')
content = content.replace('    const recognitionRef = useRef<SpeechRecognition | null>(null);\n', '')
content = content.replace('    const [transcriptionMode, setTranscriptionMode] = useState<"web_speech" | "local_whisper">("web_speech");\n', '')

# 3. Add forceStopWavRecording and remove stopListening / startListening Web Speech API
force_stop_code = """    const forceStopWavRecording = useCallback(() => {
        setIsWavRecording(false);
        if (scriptProcessorRef.current) {
            scriptProcessorRef.current.disconnect();
            scriptProcessorRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        audioChunksRef.current = [];
    }, []);
"""
content = re.sub(
    r'    // -----------------------------------------------------------------------\n    // FIX: Speech Recognition — use Web Speech API for mic-to-text\n    // -----------------------------------------------------------------------\n    const startListening = useCallback\(\(\) => \{.*?\n    const stopListening = useCallback\(\(\) => \{.*?\n    \}, \[\]\);\n',
    force_stop_code, 
    content, 
    flags=re.DOTALL
)

# 4. Replace other usages of stopListening with forceStopWavRecording
content = content.replace('stopListening(); // Stop STT while submitting', 'forceStopWavRecording();')
content = content.replace('if (!newVal) stopListening();', 'if (!newVal) forceStopWavRecording();')
content = content.replace('stopListening();', 'forceStopWavRecording();')
content = content.replace('stopListening, ', 'forceStopWavRecording, ')
content = content.replace('{isListening && (', '{isWavRecording && (')
content = content.replace('disabled={isListening || isWavRecording || isTranscribing}', 'disabled={isWavRecording || isTranscribing}')
content = content.replace('isListening || isWavRecording ?', 'isWavRecording ?')
content = content.replace('isListening ? "🎙️ Listening… speak your answer (or type here)" : ', '')
content = content.replace('title={isWavRecording || isListening ?', 'title={isWavRecording ?')
content = content.replace(
    'if (transcriptionMode === "local_whisper") {\n                                            isWavRecording ? stopWavRecordingAndTranscribe() : startWavRecording();\n                                        } else {\n                                            isListening ? stopListening() : startListening();\n                                        }', 
    'isWavRecording ? stopWavRecordingAndTranscribe() : startWavRecording();'
)

# 5. Remove transcription mode select box
select_ui = r'<div className="ml-4 flex items-center gap-2">\s*<span className="font-semibold text-zinc-400">Transcription Mode:</span>\s*<select[^>]+>\s*<option[^>]+>.*?</option>\s*<option[^>]+>.*?</option>\s*</select>\s*</div>'
content = re.sub(select_ui, '', content, flags=re.DOTALL)

with open('frontend/src/app/interview/[id]/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Frontend cleanup done")
