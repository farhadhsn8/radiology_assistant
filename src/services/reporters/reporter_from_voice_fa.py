from __future__ import annotations

import json
import os
from typing import Tuple

import numpy as np
from natsort import natsorted
from pydub import AudioSegment
from transformers import pipeline

from src.services.llm.llm import llm
from src.services.llm.refine_transcription import FarsiTranscriptionRefiner
from src.services.reporters.Reporter_fa import ReporterFA
from src.services.reporters.type_detector_fa import Type_detector_FA
from src.utils.normalize_and_mapping import normalize_persian_text


class Reporter_from_voice_FA:

    def __init__(self) -> None:
        self.text_reporter = ReporterFA()
        self.type_detector = Type_detector_FA()
        self.llm_client = llm()
        self.refiner = FarsiTranscriptionRefiner(self.llm_client)

        try:
            with open("configs/medical_terms.json", "r", encoding="utf-8") as f:
                self.medical_dict = json.load(f)
        except Exception as e:
            print(f"[ERROR] Could not load configs/medical_terms.json: {e}")
            self.medical_dict = {}

        model_name = os.getenv(
            "PERSIAN_STT_MODEL_NAME",
            "jonatasgrosman/wav2vec2-large-xlsr-53-persian",
        )
        device = int(os.getenv("PERSIAN_STT_DEVICE", "-1"))

        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model=model_name,
            device=device,
        )

        self.chunk_duration_sec = 27
        self.chunk_overlap_sec = 2

    def split_audio_fixed_with_boundary(
        self,
        audio_path: str,
        output_dir: str,
        duration_sec: int,
        overlap_sec: int,
    ) -> list[str]:
        audio = AudioSegment.from_file(audio_path)
        duration_ms = int(duration_sec * 1000)
        overlap_ms = int(overlap_sec * 1000)

        os.makedirs(output_dir, exist_ok=True)
        audio_length = len(audio)

        chunk_paths: list[str] = []
        start = 0
        chunk_index = 0

        while start < audio_length:
            end = min(start + duration_ms, audio_length)
            chunk = audio[start:end]

            chunk_filename = f"chunk_{chunk_index}.mp3"
            chunk_path = os.path.join(output_dir, chunk_filename)
            chunk.export(chunk_path, format="mp3")

            chunk_paths.append(chunk_path)
            start += (duration_ms - overlap_ms)
            chunk_index += 1

        return chunk_paths

    @staticmethod
    def convert_to_mp3(input_file_path: str, output_file_path: str) -> None:
        try:
            AudioSegment.from_file(input_file_path).export(
                output_file_path,
                format="mp3",
            )
        except Exception as e:
            raise ValueError(f"Failed to convert to MP3: {e}")


    def speech_to_text(self, audio_input, language: str = "fa") -> str:
        if isinstance(audio_input, np.ndarray):
            input_data = {"raw": audio_input, "sampling_rate": 16000}
        else:
            input_data = audio_input

        result = self.pipe(
            input_data,
            generate_kwargs={"language": language, "task": "transcribe"},
        )
        return normalize_persian_text(result.get("text", ""))

    def stt_all(self, chunk_paths: list[str]) -> str:
        parts: list[str] = []
        for file in natsorted(chunk_paths):
            txt = self.speech_to_text(file)
            if txt:
                parts.append(txt)

        joined = " ".join(parts).strip()
        return normalize_persian_text(joined)

    def generate_report(self, audio_path: str) -> Tuple[str | None, str]:
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = f"assets/voices/{audio_name}"
        self.convert_to_mp3(audio_path, file_addr)

        chunk_paths = self.split_audio_fixed_with_boundary(
            audio_path=file_addr,
            output_dir=chunks_dir,
            duration_sec=self.chunk_duration_sec,
            overlap_sec=self.chunk_overlap_sec,
        )

        raw_gen_text = self.stt_all(chunk_paths)

        print("[FA] RAW STT (before refine / mapping):")
        print(raw_gen_text)
        print("[FA] Persian-only Refinement (UI) starting...")
        try:
            final_for_ui = self.refiner.refine_transcription(
                raw_gen_text,
                self.medical_dict,
            )
        except Exception as e:
            print(f"[FA] LLM refine (UI) error: {e}")
            final_for_ui = raw_gen_text

        report_type = (
            self.type_detector.detect(raw_gen_text)
            or self.type_detector.detect(final_for_ui)
            or "general"
        )

        print(f"[FA] Report type: {report_type}")
        print(f"[FA] Final Text for Generator (UI): {final_for_ui}")
        try:
            report = self.text_reporter.generate_report(raw_gen_text, report_type)
        except Exception as e:
            print(f"[FA] Report Gen Error: {e}")
            report = None
        return report, final_for_ui
