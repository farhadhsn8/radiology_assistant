


def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        return "The specified file was not found."
    except Exception as e:
        return f"An error occurred: {e}"