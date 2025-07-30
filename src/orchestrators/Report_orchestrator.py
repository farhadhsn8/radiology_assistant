from http.client import HTTPException
from src.services.reporters.Reporter import Reporter
from src.services.reporters.Reporter_from_voice import Reporter_from_voice
from src.utils.file_processing import generate_random_string
import os, json

class Report_orchestrator:
    def __init__(self):
        self.text_reporter = Reporter()
        self.voice_reporter = Reporter_from_voice()
        with open('configs/voice.json', 'r') as config_file:
            self.configs = json.load(config_file)


    def from_text(self, input_text: str, report_type: str):
        report = self.text_reporter.generate_report(input_text, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from text")
        return {
                "status": 200,
                "generated_report": report,
                "message": "report was generated from text successfully"
            }
    
    
    def from_voice(self, input_voice, report_type: str):
        file_name = generate_random_string() + f".{self.configs['format']}"
        file_path = os.path.join(self.configs["voice_address"], file_name)
        # Save the file
        with open(file_path, "wb") as f:
            content = input_voice.file.read()  
            f.write(content)
        report = self.voice_reporter.generate_report(file_path, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from voice")
        return {
                "status": 200,
                "generated_report": report,
                "message": "report was generated from voice successfully"
            }

