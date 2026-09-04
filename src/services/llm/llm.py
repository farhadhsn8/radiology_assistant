from langchain_openai import ChatOpenAI

from src.config import get_llm_config


class LLM:
    def __init__(self) -> None:
        config = get_llm_config()
        self.client = ChatOpenAI(
            model=config["model_name"],
            base_url=config["base_url"],
            temperature=config["temperature"],
            api_key=config["api_key"],
        )

    def get_answer(self, input_text: str, system_prompt: str) -> str:
        final_prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text},
        ]
        return self.client.invoke(final_prompt).content
