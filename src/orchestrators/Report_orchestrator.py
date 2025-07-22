from http.client import HTTPException
from src.services.reporters import Reporter, Reporter_from_voice



class Report_orchestrator:
    def __init__(self):
        self.text_reporter = Reporter()
        self.voice_reporter = Reporter_from_voice()


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
        report = self.voice_reporter.generate_report(input_voice, report_type)
        if not report:
            raise HTTPException(status_code=400, detail="Failed to generate report from voice")
        return {
                "status": 200,
                "generated_report": report,
                "message": "report was generated from voice successfully"
            }

