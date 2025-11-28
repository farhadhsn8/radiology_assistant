import os
import json
from fastapi.exceptions import HTTPException
from src.services.reporters.Reporter_fa import ReporterFA
from src.services.reporters.reporter_from_voice_fa import Reporter_from_voice_FA
from src.utils.file_processing import generate_meaningful_filename


class Report_orchestrator_fa:
    def __init__(self):
        self.text_reporter = ReporterFA()
        self.voice_reporter = Reporter_from_voice_FA()
        with open('configs/voice.json', 'r', encoding="utf-8") as config_file:
            self.configs = json.load(config_file)

    def from_text(self, input_text: str, report_type: str):
        report = self.text_reporter.generate_report(input_text, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate Farsi report from text")
        return {
            "status": 200,
            "generated_report": report,
            "message": "Farsi report generated from text",
        }

    def from_voice(self, input_voice):
    
        original_ext = os.path.splitext(input_voice.filename or "")[1].lower()
        if not original_ext:
          
            original_ext = "." + self.configs.get("format", "mp3")

     
        temp_file_name = generate_meaningful_filename(
            "unknown",
            extension=original_ext.lstrip("."),
        )
        file_path = os.path.join(self.configs["voice_address"], temp_file_name)
        print(f"[FA] Saving raw audio to: {file_path}")

        try:
            os.makedirs(self.configs["voice_address"], exist_ok=True)
        except OSError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create directory {self.configs['voice_address']}: {e}",
            )

        with open(file_path, "wb") as f:
            f.write(input_voice.file.read())

     
        report, raw_report = self.voice_reporter.generate_report(file_path)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate Farsi report from voice")

     
        final_ext = self.configs.get("format", "mp3")
        final_file_name = generate_meaningful_filename(
            "unknown",
            raw_report,
            final_ext,
        )
        final_file_path = os.path.join(self.configs["voice_address"], final_file_name)

        if file_path != final_file_path and os.path.exists(file_path):
            os.rename(file_path, final_file_path)
            print(f"[FA] Renamed audio to: {final_file_path}")

        return {
            "status": 200,
            "generated_report": report,
            "message": "Farsi report generated from voice",
        }
