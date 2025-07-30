import random
import string

import re, json

def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        return "The specified file was not found."
    except Exception as e:
        return f"An error occurred: {e}"
    

    
def extract_field_from_json(text, field_name):
    text = text.encode('latin-1').decode('unicode_escape')
    pattern = rf"{re.escape(field_name)}:\s*\"((?:[^\"\\]|\\.)*)\""
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None


def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))