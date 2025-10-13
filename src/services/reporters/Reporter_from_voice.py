from src.services.reporters.Reporter import Reporter
from transformers import pipeline
from pydub import AudioSegment
from pydub.silence import split_on_silence
import os
import glob
from natsort import natsorted


class Reporter_from_voice:
    def __init__(self):
        device =  -1  # -1 for CPU, 0 for GPU
        self.text_reporter = Reporter()
        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-base",  # facebook/wav2vec2-large-robust    openai/whisper-base      facebook/wav2vec2-base-960h
            device=device,
        )



    def split_audio_on_silence(self, audio_path, t, output_dir, min_silence_len=120, silence_thresh=-40, keep_silence=100):
        """
        Splits an audio file into parts if its duration is longer than t seconds.
        Splitting is done on silence or weak signal.

        Parameters:
        - audio_path: str, path to the input audio file
        - t: float, threshold duration in seconds
        - output_dir: str, directory to save the split audio parts
        - min_silence_len: int, minimum length of silence to be used for splitting (ms)
        - silence_thresh: int, silence threshold in dBFS (lower means more sensitive)
        - keep_silence: int, amount of silence to leave at the edges of each chunk (ms)

        Returns:
        - List of saved file paths if split, else original audio path in a list
        """

        audio_name = os.path.basename(audio_path)
        # Load audio
        audio = AudioSegment.from_file(audio_path)
        duration_sec = len(audio) / 1000.0

        if duration_sec <= t:
            # No need to split, just return original
            print(f"Audio duration {duration_sec}s <= threshold {t}s, no splitting needed.")
            return [audio_path]

        os.makedirs(output_dir, exist_ok=True)

        # Split on silence
        chunks = split_on_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence
        )

        saved_files = []
        total_length_ms = 0
        for i, chunk in enumerate(chunks):
                chunk_length_sec = len(chunk) / 1000.0
                if chunk_length_sec < 0.8:
                    continue
                    
                chunk_filename = os.path.join(output_dir, f"audio_name_{i+1}.mp3")
                chunk.export(chunk_filename, format="mp3")
                saved_files.append(chunk_filename)
                total_length_ms += len(chunk)


        return saved_files
    



    def convert_to_mp3(self, input_file_path, output_file_path):

        """
        Convert an audio file to MP3 format.

        :param input_file_path: Path to the input audio file.
        :param output_file_path: Path where the output MP3 file will be saved.
        """
        # Load the audio file
        audio = AudioSegment.from_file(input_file_path)
        # Export as MP3
        audio.export(output_file_path, format="mp3")


    def speech_to_text(self, audio_path: str, language: str = "en") -> str:        
        # Process audio with language specification
        result = self.pipe(
            audio_path,
            generate_kwargs={"language": language}
        )
        return result["text"]

    
    def stt_all(self, directory):
        # List all entries in the directory
        text_all = ""
        files = glob.glob(directory+"/*.mp3")
        # Sort files using natural sorting
        sorted_files = natsorted(files)
        for v in sorted_files:
            ou = self.speech_to_text(v)
            text_all += ou
        return text_all


    def generate_report(self, audio_path: str, report_type: str) -> str:
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        audio_name = os.path.basename(audio_path)
        chunks_dir = f"assets/voices/{audio_name}"
        self.convert_to_mp3(audio_path,file_addr)
        self.split_audio_on_silence(file_addr,30, chunks_dir)
        gen_text = self.stt_all(chunks_dir)
        return self.text_reporter.generate_report(gen_text, report_type)

        