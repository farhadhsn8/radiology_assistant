from langchain_openai import ChatOpenAI 
import json 



class llm:
    def __init__(self) -> None:
        with open('env.json', 'r') as config_file:
            self.configs = json.load(config_file)["llm"]
        self.client = ChatOpenAI(
            model = self.configs["model_name"],
            base_url=self.configs['base_url'],
            temperature = self.configs["temperature"],
            api_key=self.configs['api_key']
        )

    
    def get_answer(self, inp_text: str, prompt: str)-> str:
        final_prompt = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": inp_text}
        ]
        
        return self.client.invoke(final_prompt).content

         



