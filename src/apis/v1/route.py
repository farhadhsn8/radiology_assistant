from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import APIKeyHeader
from orchestrators.Report_orchestrator import Report_orchestrator
import json 
# ps aux | grep uvicorn
# kill 376300
# uvicorn main:app --host 0.0.0.0 --port 5682 --workers 1 
# nohup uvicorn main:app --host 0.0.0.0 --port 5682 --workers 1 > output.log 2>&1 & 



API = json.load(open('env.json'))['API']

api_key_header = APIKeyHeader(name=API["name"])

app = FastAPI()
repr_orch = Report_orchestrator()


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API["key"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
@app.post("/text/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_text(input_text: str, report_type: str):     
    return repr_orch.from_text(input_text, report_type)   
    
@app.post("/voice/gen_report", dependencies=[Depends(verify_api_key)])
async def generate_report_from_voice(input_voice, report_type):     
    return repr_orch.from_voice(input_voice, report_type)
