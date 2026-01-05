import json
from langchain_openai import ChatOpenAI


class llm:
    def __init__(self) -> None:
        with open("env.json", "r", encoding="utf-8") as config_file:
            self.configs = json.load(config_file)["models"]["llm"]

        self.client = ChatOpenAI(
            model=self.configs["model_name"],
            base_url=self.configs["base_url"],
            temperature=self.configs.get("temperature", 0.0),
            api_key=self.configs["api_key"],
        )

    def get_answer(self, inp_text: str, system_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": inp_text},
        ]
        out = self.client.invoke(messages).content
        return out.strip() if isinstance(out, str) else str(out)

 
