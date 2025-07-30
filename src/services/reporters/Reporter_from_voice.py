from src.services.reporters.Reporter import Reporter
from transformers import pipeline


class Reporter_from_voice:
    def __init__(self):
        device =  -1  # -1 for CPU, 0 for GPU
        self.text_reporter = Reporter()
        self.pipe = pipeline(
            task="automatic-speech-recognition",
            model="openai/whisper-base",  # facebook/wav2vec2-large-robust    openai/whisper-base      facebook/wav2vec2-base-960h
            device=device,
        )


    def speech_to_text(self, audio_path: str, language: str = "en") -> str:        
        # Process audio with language specification
        result = self.pipe(
            audio_path,
            generate_kwargs={"language": language}
        )
        return result["text"]

    
    def generate_report(self, audio_path: str, report_type: str) -> str:
        gen_text = self.speech_to_text(audio_path)
        return self.text_reporter.generate_report(gen_text, report_type)

        