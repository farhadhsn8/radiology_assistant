

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.security import APIKeyHeader

import json

from src.orchestrators.Report_orchestrator import Report_orchestrator
from src.orchestrators.report_orchestrator_fa import Report_orchestrator_fa


API = json.load(open('env.json'))['API']
api_key_header = APIKeyHeader(name=API["name"])

app = FastAPI()

repr_orch = Report_orchestrator()
orch_fa = Report_orchestrator_fa()


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API["key"]:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/text/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_text(input_text: str, report_type: str):
    return repr_orch.from_text(input_text, report_type)


@app.post("/voice/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_voice(input_voice: UploadFile):
  
    return repr_orch.from_voice(input_voice)


@app.post("/reports/fa/text", dependencies=[Depends(verify_api_key)])
async def generate_farsi_report_from_text(
    input_text: str = Form(...),
    report_type: str = Form(...),
):
    return orch_fa.from_text(input_text, report_type)


@app.post("/reports/fa/voice", dependencies=[Depends(verify_api_key)])
async def generate_farsi_report_from_voice(
    input_voice: UploadFile = File(...),
):
    return orch_fa.from_voice(input_voice)
