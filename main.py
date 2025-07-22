from src.apis.v1.route import app as api_app
from fastapi import FastAPI


if __name__ == "__main__":
    app = FastAPI()
    app.mount("/api", api_app)