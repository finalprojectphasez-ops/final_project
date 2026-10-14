import os
import json
import re
import time
import torch
import soundfile as sf
import librosa
import numpy as np
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from peft import PeftModel

class WhisperEngine:
    def __init__(self, base_model_id, lora_path, no_repeat_ngram_size: int = 0):
        self.base_model_id = base_model_id
        self.lora_path = lora_path
        self.no_repeat_ngram_size = no_repeat_ngram_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.glossary = self._load_glossary()
        
        self.load_time_s = 0.0
        self.warmup_time_s = 0.0

    def _load_glossary(self):
        glossary_path = os.path.join(os.path.dirname(__file__), "glossary.json")
        if os.path.exists(glossary_path):
            try:
                with open(glossary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    places_count = len(data.get("places_and_institutions", []))
                    tech_count = len(data.get("technical_corrections", {}))
                    place_count = len(data.get("place_corrections", {}))
                    name_count = len(data.get("candidate_name_variants", {}))
                    print(f"[WhisperEngine] Loaded glossary: {places_count} places, {tech_count} tech corrections, {place_count} place corrections, {name_count} candidate name maps")
                    return data
            except Exception as e:
                print(f"[WhisperEngine] Warning loading glossary.json: {e}")
        return {
            "places_and_institutions": [],
            "technical_corrections": {},
            "place_corrections": {},
            "candidate_name_variants": {}
        }

    def _extract_candidate_name(self, context: str):
        if not context:
            return None
        # Support common verified personal names with hyphens, apostrophes, accented letters, and spaces
        match = re.search(r'\bCandidate:\s*([A-Za-z\u00C0-\u024F\s\'’\-]+?)(?:\.|$|\n)', context, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip().strip('\'’\\- ')
            if 2 <= len(name) <= 30 and len(name.split()) <= 4:
                return name
        return None

    def build_prompt(self, context: str = None) -> str:
        """
        Builds a focused transcription prompt.
        - Default: Short technical vocabulary prompt only.
        - With verified candidate context: Candidate details (name, college, hometown)
          are added ONLY if verified in the context for this specific interview.
        - Never injects the generic 20+ places/colleges list.
        - Completely stateless across calls.
        """
        parts = ["Technical interview in English."]
        
        # 1. Authoritative candidate profile / resume context if verified and supplied
        if context and context.strip():
            clean_ctx = " ".join(context.strip().split())[:120]
            parts.append(f"Candidate profile: {clean_ctx}.")
            
        # 2. Short core technical vocabulary prompt
        parts.append(
            "Technologies: Frontend developer, full-stack developer, "
            "React, JavaScript, TypeScript, HTML, CSS, Python, SQL, API, database, "
            "cloud computing, machine learning."
        )
        return " ".join(parts)

    def load_model(self):
        print(f"[WhisperEngine] Loading processor for {self.base_model_id}...")
        t0 = time.time()
        self.processor = WhisperProcessor.from_pretrained(self.base_model_id, language="English", task="transcribe")
        
        print("[WhisperEngine] Loading base model (8-bit)...")
        bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
        base_model = WhisperForConditionalGeneration.from_pretrained(
            self.base_model_id,
            quantization_config=bnb_cfg,
            device_map="auto"
        )
        base_model.config.forced_decoder_ids = None
        base_model.config.suppress_tokens = []
        
        print(f"[WhisperEngine] Loading LoRA adapter from {self.lora_path}...")
        self.model = PeftModel.from_pretrained(base_model, self.lora_path)
        self.model.eval()
        self.load_time_s = time.time() - t0
        print(f"[WhisperEngine] Model loaded in {self.load_time_s:.2f}s")
        
        self._warmup()

    def _warmup(self):
        print("[WhisperEngine] Warming up model...")
        t0 = time.time()
        # Create a 1-second silent audio buffer at 16kHz
        silent_audio = np.zeros(16000, dtype=np.float32)
        try:
            self.transcribe_audio_array(silent_audio, sample_rate=16000)
            self.warmup_time_s = time.time() - t0
            print(f"[WhisperEngine] Warmup complete in {self.warmup_time_s:.2f}s")
        except Exception as e:
            print(f"[WhisperEngine] Warmup failed: {e}")

    def _decode_segment(self, segment_audio, prompt_ids, forced_ids) -> str:
        inputs = self.processor.feature_extractor(
            segment_audio,
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features.to(self.device).half()

        gen_kwargs = {
            "forced_decoder_ids": forced_ids,
            "prompt_ids": prompt_ids,
            "max_new_tokens": 225,
            "condition_on_prev_tokens": False,
            "repetition_penalty": 1.0,
        }
        if self.no_repeat_ngram_size > 0:
            gen_kwargs["no_repeat_ngram_size"] = self.no_repeat_ngram_size

        with torch.inference_mode():
            generated = self.model.generate(
                inputs,
                **gen_kwargs
            )
            
        return self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def transcribe_audio_array(self, audio_array, sample_rate, context: str = None):
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)

        # Build dynamic prompt for this recording session incorporating candidate context + glossary
        prompt_text = self.build_prompt(context)
        p_tensor = self.processor.get_prompt_ids(prompt_text, return_tensors="pt")
        prompt_ids = p_tensor.to(self.device) if isinstance(p_tensor, torch.Tensor) else torch.tensor(p_tensor).to(self.device)
        forced_ids = self.processor.get_decoder_prompt_ids(language="english", task="transcribe")

        WINDOW_SAMPLES = 30 * 16000  # 480,000 samples = 30.0 seconds
        if len(audio_array) <= WINDOW_SAMPLES:
            transcription = self._decode_segment(audio_array, prompt_ids, forced_ids)
        else:
            # Multi-window long-form decoding: processes multi-minute audio in sequential 30s windows
            window_texts = []
            segment_hallucinations = {
                "thank you.", "thank you", "bye.", "bye", "you", "subscribe", 
                "subtitles by", "thank you for watching", "thanks for watching", "."
            }
            for start in range(0, len(audio_array), WINDOW_SAMPLES):
                end = min(start + WINDOW_SAMPLES, len(audio_array))
                seg = audio_array[start:end]
                # Skip tiny or silent trailing slices (<0.2s or peak < 0.005)
                if len(seg) < 3200 or np.max(np.abs(seg)) < 0.005:
                    continue
                seg_text = self._decode_segment(seg, prompt_ids, forced_ids)
                if seg_text and seg_text.lower() not in segment_hallucinations:
                    window_texts.append(seg_text)
            transcription = " ".join(window_texts).strip()
        
        # 1. Technical corrections (generic technical terms)
        tech_corrections = self.glossary.get("technical_corrections", {})
        for wrong, right in tech_corrections.items():
            pattern = r'\b' + re.escape(wrong) + r'\b'
            transcription = re.sub(pattern, right, transcription, flags=re.IGNORECASE)

        # 2. Candidate-specific place corrections:
        # Applied ONLY when supported by the current verified candidate context (e.g. location, education)
        if context:
            place_corrections = self.glossary.get("place_corrections", {})
            for wrong, right in place_corrections.items():
                if right.lower() in context.lower():
                    pattern = r'\b' + re.escape(wrong) + r'\b'
                    transcription = re.sub(pattern, right, transcription, flags=re.IGNORECASE)

        # 3. Candidate-specific personal name corrections:
        # Applied ONLY when the canonical name is verified for the CURRENT candidate in context/resume
        candidate_name = self._extract_candidate_name(context)
        if candidate_name:
            variants_map = self.glossary.get("candidate_name_variants", {})
            canonical_key = next((k for k in variants_map if k.lower() == candidate_name.lower()), None)
            if canonical_key:
                for variant in variants_map[canonical_key]:
                    pattern = r'\b' + re.escape(variant) + r'\b'
                    transcription = re.sub(pattern, canonical_key, transcription, flags=re.IGNORECASE)

        # Hallucination filter
        lower_t = transcription.lower()
        hallucinations = [
            "thank you.", "thank you", "bye.", "bye", "you", "subscribe", 
            "subtitles by", "thank you for watching", "thanks for watching"
        ]
        
        # Aggressive repeat/gibberish filter for '===', '//', and similar artifacts
        if "===" in transcription or "//" in transcription or lower_t in hallucinations or transcription.startswith("Thank you for watching"):
            return ""
            
        return transcription
