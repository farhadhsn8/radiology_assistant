from src.apis.v1.route import app as api_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# http://127.0.0.1:5682/api/docs
# ps aux | grep uvicorn
# kill 376300
# uvicorn main:app --host 0.0.0.0 --port 5682 --workers 1 
# nohup uvicorn main:app --host 0.0.0.0 --port 5682 --workers 1 > logs/output.log 2>&1 &

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (adjust in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.mount("/api", api_app)