from src.services.llm.llm import llm

class Reporter:
    def __init__(self):
        llm_instance = llm()

    def report(self, message: str):
        """
        Report a message to the user.
        """
        print(message)

    def prepare_inputs(self, d):
        pass

    
    def generate_report(self, raw_text: str, report_type: str) -> str:
        template = self.get_template(report_type)
        prompt = self.get_prompt(report_type)
        materials = self.prepare_inputs(raw_text, template, report_type)
        return self.llm_instance.get_answer(materials, prompt)

        