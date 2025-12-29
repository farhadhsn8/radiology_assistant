import os
import numpy as np
import re
import json
from transformers import pipeline
from pydub import AudioSegment
from natsort import natsorted

from src.services.reporters.Reporter_fa import ReporterFA
from src.services.reporters.type_detector_fa import Type_detector_FA
from src.utils.measurement_resolver_fa import resolve_measurements
from src.services.llm.llm import llm 

class Reporter_from_voice_FA:
    def __init__(self):
        self.text_reporter = ReporterFA()
        self.type_detector = Type_detector_FA()
        self.llm_service = llm() 
        
        # لود کردن دیکشنری برای مرحله Mapping
        try:
            with open('configs/medical_terms.json', 'r', encoding="utf-8") as f:
                self.medical_dict = json.load(f)
        except Exception as e:
            print(f"[ERROR] Could not find medical_terms.json: {e}")
            self.medical_dict = {}

        model_name = os.getenv("PERSIAN_STT_MODEL_NAME", "jonatasgrosman/wav2vec2-large-xlsr-53-persian")
        device = int(os.getenv("PERSIAN_STT_DEVICE", "-1"))

        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model=model_name,
            device=device,
        )

        self.chunk_duration_sec = 27

    def split_audio_fixed_with_boundary(self, audio_path, output_dir, duration_sec=29, overlap_sec=2):
        audio = AudioSegment.from_file(audio_path)
        duration_ms = int(duration_sec * 1000)
        overlap_ms = int(overlap_sec * 1000)
        os.makedirs(output_dir, exist_ok=True)
        audio_length = len(audio)
        chunk_paths = []
        start = 0
        chunk_index = 0
        while start < audio_length:
            end = start + duration_ms
            if end > audio_length: end = audio_length
            chunk = audio[start:end]
            chunk_filename = f"chunk_{chunk_index}.mp3"
            chunk_path = os.path.join(output_dir, chunk_filename)
            chunk.export(chunk_path, format="mp3")
            chunk_paths.append(chunk_path)
            start += (duration_ms - overlap_ms)
            chunk_index += 1
        return chunk_paths

    def convert_to_mp3(self, input_file_path, output_file_path):
        try:
            AudioSegment.from_file(input_file_path).export(output_file_path, format="mp3")
        except Exception as e:
            raise ValueError(f"Failed to convert to MP3: {e}")

    @staticmethod
    def normalize_persian_text(text: str) -> str:
        if not text: return text
        text = text.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
        arabic_diacritics_pattern = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]")
        return re.sub(arabic_diacritics_pattern, "", text).strip()

    def speech_to_text(self, audio_input, language: str = "fa") -> str:
        input_data = {"raw": audio_input, "sampling_rate": 16000} if isinstance(audio_input, np.ndarray) else audio_input
        result = self.pipe(input_data, generate_kwargs={"language": language, "task": "transcribe"})
        return self.normalize_persian_text(result["text"])

    def stt_all(self, chunk_paths):
        text = ""
        for file in natsorted(chunk_paths):
            text += self.speech_to_text(file) + " "
        return text.strip()

    def generate_report(self, audio_path: str) -> tuple[str | None, str]:
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = f"assets/voices/{audio_name}"

        self.convert_to_mp3(audio_path, file_addr)
        chunk_paths = self.split_audio_fixed_with_boundary(file_addr, chunks_dir)

        raw_gen_text = self.stt_all(chunk_paths)

        print("[FA] Persian-only Refinement starting...")
        try:
            refined_fa = self.llm_service.refine_transcription_fa_only(raw_gen_text)
        except Exception as e:
            print(f"[FA] LLM refine error: {e}")
            refined_fa = raw_gen_text

        # قالب/تمپلیت با report_type انتخاب می‌شود => این قسمت را مقاوم کن
        report_type = (
            self.type_detector.detect(raw_gen_text)
            or self.type_detector.detect(refined_fa)
            or "general"
        )

        refined_fa = resolve_measurements(refined_fa)

        try:
            final_refined = self.llm_service.refine_transcription(refined_fa, self.medical_dict)
        except Exception as e:
            print(f"[FA] LLM mapping/rewrite error: {e}")
            final_refined = refined_fa

        print(f"[FA] Report type: {report_type}")
        print(f"[FA] Final Text for Generator (UI): {final_refined}")

        try:
            report = self.text_reporter.generate_report(final_refined, report_type)
        except Exception as e:
            print(f"[FA] Report Gen Error: {e}")
            report = None

        # gen_text برای نمایش: متن نهایی اصلاح‌شده
        return report, final_refined
