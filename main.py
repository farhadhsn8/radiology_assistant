from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.apis.v1.route import app as api_app
from src.config import PROJECT_ROOT

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api", api_app)


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(PROJECT_ROOT / "index.html")
