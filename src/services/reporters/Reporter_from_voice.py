import os

import numpy as np
from natsort import natsorted
from pydub import AudioSegment
from transformers import pipeline

from src.config import PROJECT_ROOT, get_voice_config
from src.services.reporters.Reporter import Reporter
from src.services.reporters.type_detector import TypeDetector


class Reporter_from_voice:
    def __init__(self):
        self.text_reporter = Reporter()
        self.type_detector = TypeDetector()
        self.voice_dir = PROJECT_ROOT / get_voice_config()["voice_address"]
        self.pipe = pipeline(task="automatic-speech-recognition", model="openai/whisper-base", device=-1)

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
            end = min(start + duration_ms, audio_length)

            chunk = audio[start:end]

            chunk_path = os.path.join(output_dir, f"chunk_{chunk_index}.mp3")
            chunk.export(chunk_path, format="mp3")

            chunk_paths.append(chunk_path)

            start += duration_ms - overlap_ms
            chunk_index += 1

        return chunk_paths

    def convert_to_mp3(self, input_file_path, output_file_path):
        try:
            AudioSegment.from_file(input_file_path).export(output_file_path, format="mp3")
        except Exception as e:
            raise ValueError(f"Failed to convert {input_file_path} to MP3: {e}")

    def speech_to_text(self, audio_input, language="en"):
        try:
            if isinstance(audio_input, np.ndarray):
                input_data = {"raw": audio_input, "sampling_rate": 16000}
            else:
                input_data = audio_input
            return self.pipe(input_data, generate_kwargs={"language": language})["text"]
        except Exception as e:
            raise ValueError(f"Failed to transcribe audio: {e}")

    def stt_all(self, chunk_paths):
        text = ""
        for file in natsorted(chunk_paths):
            chunk_text = self.speech_to_text(file)
            text += chunk_text + " "
            print(file, chunk_text)
        return text

    def generate_report(self, audio_path: str) -> tuple[str, str]:
        print(f"Generating report for audio: {audio_path}")
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = os.path.join(self.voice_dir, audio_name)
        print(f"Chunk directory: {chunks_dir}")
        self.convert_to_mp3(audio_path, file_addr)
        chunk_paths = self.split_audio_fixed_with_boundary(file_addr, chunks_dir)
        gen_text = self.stt_all(chunk_paths)
        report_type = self.type_detector.detect(gen_text)
        print("gen_text", gen_text)
        print("report_type", report_type)
        report = self.text_reporter.generate_report(gen_text, report_type)
        print("final_report::", report)

        return report, gen_text
