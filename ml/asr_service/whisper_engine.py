import time
import torch
import soundfile as sf
import librosa
import numpy as np
from transformers import WhisperForConditionalGeneration, WhisperProcessor, BitsAndBytesConfig
from peft import PeftModel

class WhisperEngine:
    def __init__(self, base_model_id, lora_path):
        self.base_model_id = base_model_id
        self.lora_path = lora_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        
        self.load_time_s = 0.0
        self.warmup_time_s = 0.0

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

    def transcribe_audio_array(self, audio_array, sample_rate):
        if sample_rate != 16000:
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
            
        inputs = self.processor.feature_extractor(
            audio_array,
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features.to(self.device)
        
        # The 8-bit model weights act as fp16 for inference
        inputs = inputs.half()

        with torch.inference_mode():
            forced_ids = self.processor.get_decoder_prompt_ids(language="english", task="transcribe")
            generated = self.model.generate(
                inputs,
                forced_decoder_ids=forced_ids,
                max_new_tokens=225,
                condition_on_prev_tokens=False,
                repetition_penalty=1.15
            )
            
        transcription = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        
        # Hallucination filter
        lower_t = transcription.lower()
        hallucinations = [
            "thank you.", "thank you", "bye.", "bye", "you", "subscribe", 
            "subtitles by", "hello, i am your friend", "hello, i am your friend and i will be your friend"
        ]
        
        # Aggressive repeat/gibberish filter for '===' and similar artifacts
        if "===" in transcription or lower_t in hallucinations or transcription.startswith("Thank you for watching"):
            return ""
            
        return transcription
