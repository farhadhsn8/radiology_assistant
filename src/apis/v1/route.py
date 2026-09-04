from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from fastapi.security import APIKeyHeader

from src.config import get_api_config
from src.orchestrators.Report_orchestrator import Report_orchestrator

API = get_api_config()

api_key_header = APIKeyHeader(name=API["name"])

app = FastAPI()
report_orchestrator = Report_orchestrator()


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API["key"]:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/text/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_text(input_text: str, report_type: str):
    return report_orchestrator.from_text(input_text, report_type)


@app.post("/voice/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_voice(input_voice: UploadFile):
    return report_orchestrator.from_voice(input_voice)
