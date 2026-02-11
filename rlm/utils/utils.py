import re

def parse_code_blocks(text: str) -> str:
    """
    Parses code blocks from a string of text.
    Currently only supports `repl` blocks.
    """
    pattern = r"```repl(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if not matches:
        return None
    return matches[0].strip()

def parse_final_answer(text: str) -> str:
    """
    Parses the final answer from the text logic.
    Supports FINAL(answer) and FINAL_VAR(variable_name).
    """
    # Check for FINAL_VAR(variable_name)
    var_pattern = r"FINAL_VAR\((.*?)\)"
    var_match = re.search(var_pattern, text)
    if var_match:
        return {"type": "variable", "value": var_match.group(1).strip()}

    # Check for FINAL(answer)
    # This regex is a bit greedy/tricky if the answer contains parentheses.
    # We assume the answer ends at the last closing parenthesis.
    # Improved regex to capture content inside balanced parentheses would be better,
    # but for simple text keys this might suffice or we rely on the model to call it last.
    
    # Simple check: FINAL(...)
    if "FINAL(" in text:
        start_index = text.find("FINAL(") + 6
        end_index = text.rfind(")")
        if start_index < end_index:
             return {"type": "direct", "value": text[start_index:end_index]}

    return None
