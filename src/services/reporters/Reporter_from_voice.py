from pydub import AudioSegment
from src.services.reporters.Reporter import Reporter
from transformers import pipeline
import os 

class Reporter_from_voice:
    def __init__(self):
        device =  -1  # -1 for CPU, 0 for GPU
        self.text_reporter = Reporter()
        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-base",  # facebook/wav2vec2-large-robust    openai/whisper-base      facebook/wav2vec2-base-960h
            device=device,
        )



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

    
    def generate_report(self, audio_path: str, report_type: str) -> str:
        file_addr = os.path.splitext(audio_path)[0] + ".mp3"
        self.convert_to_mp3(audio_path,file_addr)

        gen_text = self.speech_to_text(file_addr)
        return self.text_reporter.generate_report(gen_text, report_type)

        