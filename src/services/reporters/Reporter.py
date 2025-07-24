from src.services.llm.llm import llm
from src.utils.file_processing import read_text_file



class Reporter:
    def __init__(self):
        self.llm_instance = llm()

    def report(self, message: str):
        """
        Report a message to the user.
        """
        print(message)

    def prepare_inputs(self, raw_text: str, template: str, report_type: str) -> dict:
        input_text = f"""
        Report Type: {report_type}
        -------------------------
        Template report: {template}
        -------------------------
        Patient raw report: {raw_text}
        """
        return input_text


    def get_template(self, report_type: str) -> str: # type sample: CT:contrast:abdomen_and_pelvis
        type_parts = report_type.split(":")
        file_addr = f"assets/templates/{type_parts[0]}/{type_parts[1]}/{type_parts[2]}.txt"
        content = read_text_file(file_addr)
        if "not found" in content:
            raise FileNotFoundError(f"Template file for {report_type} not found.")
        if "error" in content:
            raise Exception(f"Error reading template file for {report_type}: {content}")
        return content
    

    def get_prompt(self, report_type: str) -> str:
        type_parts = report_type.split(":")
        file_addr = f"assets/prompts/{type_parts[0]}/{type_parts[1]}/{type_parts[2]}.txt"
        content = read_text_file(file_addr)
        if "not found" in content:
            raise FileNotFoundError(f"Prompt file for {report_type} not found.")
        if "error" in content:
            raise Exception(f"Error reading prompt file for {report_type}: {content}")
        return content

    
    def generate_report(self, raw_text: str, report_type: str) -> str:
        template = self.get_template(report_type)
        prompt = self.get_prompt(report_type)
        materials = self.prepare_inputs(raw_text, template, report_type)
        return self.llm_instance.get_answer(materials, prompt)



       
        