from src.apis.v1.route import app as api_app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
# source radio/bin/activate
# cp index.html  /var/www/html/index.html
# cp  reportexx /etc/nginx/sites-available/reportexx 
# sudo nginx -s reload
# ps aux | grep uvicorn
# kill id
# nohup uvicorn main:app --host 127.0.0.1  --port 5682 --timeout-keep-alive 300  --workers 1 > logs/output.log 2>&1 &
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (adjust in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.mount("/api", api_app)
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("index.html")