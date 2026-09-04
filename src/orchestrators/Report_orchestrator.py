import os

from fastapi.exceptions import HTTPException

from src.config import PROJECT_ROOT, get_voice_config
from src.services.reporters.Reporter import Reporter
from src.services.reporters.Reporter_from_voice import Reporter_from_voice
from src.utils.file_processing import generate_meaningful_filename


class Report_orchestrator:
    def __init__(self):
        self.text_reporter = Reporter()
        self.voice_reporter = Reporter_from_voice()
        self.voice_dir = PROJECT_ROOT / get_voice_config()["voice_address"]
        self.voice_format = get_voice_config()["format"]

    def from_text(self, input_text: str, report_type: str):
        report = self.text_reporter.generate_report(input_text, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from text")
        return {"status": 200, "generated_report": report, "message": "Report generated from text"}

    def from_voice(self, input_voice):
        temp_file_name = generate_meaningful_filename("unknown", extension=self.voice_format)
        file_path = self.voice_dir / temp_file_name

        try:
            os.makedirs(self.voice_dir, exist_ok=True)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to create directory {self.voice_dir}: {e}")

        with open(file_path, "wb") as f:
            f.write(input_voice.file.read())

        report, raw_report = self.voice_reporter.generate_report(str(file_path))
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from voice")

        final_file_name = generate_meaningful_filename("unknown", raw_report, self.voice_format)
        final_file_path = self.voice_dir / final_file_name
        if file_path != final_file_path and file_path.exists():
            file_path.rename(final_file_path)

        return {"status": 200, "generated_report": report, "message": "Report generated from voice"}
