import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSETS_DIR = PROJECT_ROOT / "assets"
CONFIGS_DIR = PROJECT_ROOT / "configs"
ENV_FILE = PROJECT_ROOT / "env.json"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def asset_path(relative_path: str) -> Path:
    return ASSETS_DIR / relative_path


def get_env_config() -> dict:
    return _load_json(ENV_FILE)


def get_api_config() -> dict:
    return get_env_config()["API"]


def get_llm_config() -> dict:
    return get_env_config()["models"]["llm"]


def get_voice_config() -> dict:
    return _load_json(CONFIGS_DIR / "voice.json")
