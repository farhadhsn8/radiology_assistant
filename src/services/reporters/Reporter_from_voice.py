
from src.services.reporters.Reporter import Reporter
from transformers import pipeline
from pydub import AudioSegment
import os, glob, re, numpy as np
from natsort import natsorted
from io import BytesIO
from src.utils.file_processing import generate_meaningful_filename

class Reporter_from_voice:
    def __init__(self):
        self.text_reporter = Reporter()
        self.pipe = pipeline(task="automatic-speech-recognition", model="openai/whisper-base", device=-1)
        self.chunk_duration_sec = 30

    def split_audio_fixed_with_boundary(self, audio_path, output_dir):
        """Split audio into ~30s chunks, adjusting boundaries to avoid mid-word cuts."""
        audio_name = os.path.basename(audio_path)
        try:
            audio = AudioSegment.from_file(audio_path)
        except Exception as e:
            raise ValueError(f"Failed to load audio {audio_path}: {e}")
        
        duration_sec = len(audio) / 1000.0
        if duration_sec <= self.chunk_duration_sec:
            return [audio_path]
        
        try:
            os.makedirs(output_dir, exist_ok=True)  # Ensure chunk dir exists
        except OSError as e:
            raise ValueError(f"Failed to create directory {output_dir}: {e}")
        
        saved_files = []
        start_ms = 0
        i = 1
        
        while start_ms < len(audio):
            end_ms = min(start_ms + self.chunk_duration_sec * 1000, len(audio))
            temp_chunk = audio[start_ms:end_ms]
            
            # Check last 1s for mid-word
            check_audio = temp_chunk[-1000:] if len(temp_chunk) > 1000 else temp_chunk
            try:
                check_audio_wav = check_audio.export(BytesIO(), format="wav")
                check_audio_np = np.frombuffer(check_audio_wav.read(), dtype=np.int16)
                check_text = self.speech_to_text(check_audio_np, format="wav")
                if re.search(r'\S$|\w$', check_text.strip()):  # Mid-word
                    ext_ms = min(end_ms + 5000, len(audio))  # Extend up to 5s
                    if ext_ms > end_ms:
                        ext_audio = audio[end_ms:ext_ms]
                        silence = ext_audio.get_silence_duration(threshold=-40)
                        if silence:
                            end_ms += silence
                        else:
                            end_ms = ext_ms
            except Exception as e:
                print(f"Warning: Failed to check word boundary for chunk {i}: {e}")
            
            chunk = audio[start_ms:end_ms]
            if len(chunk) / 1000.0 >= 0.8:  # Skip short chunks
                chunk_filename = os.path.join(output_dir, f"{audio_name}_{i}.mp3")
                try:
                    chunk.export(chunk_filename, format="mp3")
                    saved_files.append(chunk_filename)
                    i += 1
                except Exception as e:
                    print(f"Warning: Failed to export chunk {chunk_filename}: {e}")
            start_ms = end_ms
        
        return saved_files

    def convert_to_mp3(self, input_file_path, output_file_path):
        """Convert audio to MP3."""
        try:
            AudioSegment.from_file(input_file_path).export(output_file_path, format="mp3")
        except Exception as e:
            raise ValueError(f"Failed to convert {input_file_path} to MP3: {e}")

    def speech_to_text(self, audio_input, language="en", format="mp3"):
        """Convert speech to text from file path or numpy array."""
        try:
            if isinstance(audio_input, np.ndarray):
                input_data = {"raw": audio_input, "sampling_rate": 16000}
            else:
                input_data = audio_input  # Assume file path
            return self.pipe(input_data, generate_kwargs={"language": language})["text"]
        except Exception as e:
            raise ValueError(f"Failed to transcribe audio: {e}")

    def stt_all(self, directory):
        """Transcribe all MP3 files in directory."""
        text = ""
        for file in natsorted(glob.glob(os.path.join(directory, "*.mp3"))):
            text += self.speech_to_text(file) + " "
        return text.strip()

    def generate_report(self, audio_path: str, report_type: str) -> tuple[str, str]:
        print(f"Generating report for audio: {audio_path}")
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        chunks_dir = f"assets/voices/{audio_name}"
        print(f"Chunk directory: {chunks_dir}")
        self.convert_to_mp3(audio_path, file_addr)
        chunk_paths = self.split_audio_fixed_with_boundary(file_addr, chunks_dir)
        gen_text = self.stt_all(chunks_dir)
        report = self.text_reporter.generate_report(gen_text, report_type)
        
            
        return report, gen_text  # Return report and raw transcribed text
