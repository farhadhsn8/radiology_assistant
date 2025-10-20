
from fastapi.exceptions import HTTPException
from src.services.reporters.Reporter import Reporter
from src.services.reporters.Reporter_from_voice import Reporter_from_voice
from src.utils.file_processing import generate_meaningful_filename
import os, json
from pydub import AudioSegment

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
        return {"status": 200, "generated_report": report, "message": "Report generated from text"}

    def from_voice(self, input_voice, report_type: str):
        # Use temporary filename based on report_type
        temp_file_name = generate_meaningful_filename(report_type, extension=self.configs["format"])
        file_path = os.path.join(self.configs["voice_address"], temp_file_name)
        print(f"Saving audio to: {file_path}")
        try:
            os.makedirs(self.configs["voice_address"], exist_ok=True)  # Ensure voices dir exists
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to create directory {self.configs['voice_address']}: {e}")
        
        with open(file_path, "wb") as f:
            f.write(input_voice.file.read())
        
      
            # Generate report and get raw report text
        report, raw_report = self.voice_reporter.generate_report(file_path, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from voice")
            
        # Rename file based on report content
        final_file_name = generate_meaningful_filename(report_type, raw_report, self.configs["format"])
        final_file_path = os.path.join(self.configs["voice_address"], final_file_name)
        if file_path != final_file_path and os.path.exists(file_path):
            os.rename(file_path, final_file_path)
            print(f"Renamed audio to: {final_file_path}")
            
        return {"status": 200, "generated_report": report, "message": "Report generated from voice"}
       