
import os
import numpy as np
import re
from transformers import pipeline
from pydub import AudioSegment
from natsort import natsorted

from src.services.reporters.Reporter_fa import ReporterFA
from src.services.reporters.type_detector_fa import Type_detector_FA



class Reporter_from_voice_FA:
   
    def __init__(self):
        self.text_reporter = ReporterFA()

        self.type_detector = Type_detector_FA()

       
        model_name = os.getenv("PERSIAN_STT_MODEL_NAME", "m3hrdadfi/wav2vec2-large-xlsr-persian-v2")
        device = int(os.getenv("PERSIAN_STT_DEVICE", "-1"))

        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model=model_name,
            device=device,
        )

        self.chunk_duration_sec = 27
        self.type_detector = Type_detector_FA()
 
    def split_audio_fixed_with_boundary(
        self,
        audio_path: str,
        output_dir: str,
        duration_sec: int = 29,
        overlap_sec: int = 2,
    ):
       
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
            if end > audio_length:
                end = audio_length

            chunk = audio[start:end]
            chunk_filename = f"chunk_{chunk_index}.mp3"
            chunk_path = os.path.join(output_dir, chunk_filename)
            chunk.export(chunk_path, format="mp3")

            chunk_paths.append(chunk_path)

            start += (duration_ms - overlap_ms)
            chunk_index += 1

        return chunk_paths

    def convert_to_mp3(self, input_file_path: str, output_file_path: str):
        """Convert any audio format to MP3."""
        try:
            AudioSegment.from_file(input_file_path).export(
                output_file_path,
                format="mp3",
            )
        except Exception as e:
            raise ValueError(f"Failed to convert {input_file_path} to MP3: {e}")


 
    @staticmethod
    def normalize_persian_text(text: str) -> str:
      
        if not text:
            return text

        text = text.replace("\u064a", "\u06cc")  
        text = text.replace("\u0643", "\u06a9") 

        
        arabic_diacritics_pattern = re.compile(
            r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]"
        )
        text = re.sub(arabic_diacritics_pattern, "", text)

        return text.strip()

   
    def speech_to_text(self, audio_input, language: str = "fa") -> str:
       
        try:
            if isinstance(audio_input, np.ndarray):
                input_data = {"raw": audio_input, "sampling_rate": 16000}
            else:
                input_data = audio_input 

            result = self.pipe(
                input_data,
                generate_kwargs={
                    "language": language,
                    "task": "transcribe",
                },
            )

            raw_text = result["text"]
            normalized = self.normalize_persian_text(raw_text)
            return normalized

        except Exception as e:
            raise ValueError(f"Failed to transcribe Farsi audio: {e}")

    def stt_all(self, chunk_paths):
       
        text = ""
        for file in natsorted(chunk_paths):
            chunk_text = self.speech_to_text(file) + " "
            text += chunk_text
            print(file, chunk_text)
        return text.strip()


    def generate_report(self, audio_path: str) -> tuple[str | None, str]:
       
        print(f"[FA] Generating report for audio: {audio_path}")

        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = f"assets/voices/{audio_name}"

        print(f"[FA] Chunk directory: {chunks_dir}")
        self.convert_to_mp3(audio_path, file_addr)

        chunk_paths = self.split_audio_fixed_with_boundary(file_addr, chunks_dir)

        gen_text = self.stt_all(chunk_paths)

        report_type = self.type_detector.detect(gen_text)
        print("[FA] gen_text:", gen_text)
        print("[FA] report_type:", report_type)

        try:
            report = self.text_reporter.generate_report(gen_text, report_type)
        except Exception as e:
            print(f"[FA] Error generating Farsi report (type={report_type}): {e}")
            report = None

        print("[FA] final_report::", report)

        return report, gen_text
