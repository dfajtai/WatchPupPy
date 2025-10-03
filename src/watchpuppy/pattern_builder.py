import re

def simple_pattern_builder(filename: str) -> str:
    """
    Generates a simple regex pattern from a given filename by replacing
    consecutive alphabetic characters with '[a-zA-Z]+', consecutive digits with '\\d+',
    and escaping common special characters like '.', '-', and '_'.

    This is useful for users unfamiliar with regular expressions to create
    a basic pattern matching similar filenames.

    Args:
        filename (str): The input filename to generate the pattern from.

    Returns:
        str: A regex pattern string that matches filenames with a similar structure.
    """
    pattern = ""
    i = 0
    while i < len(filename):
        c = filename[i]
        if c.isalpha():
            while i < len(filename) and filename[i].isalpha():
                i += 1
            pattern += "[a-zA-Z]+"
            continue
        elif c.isdigit():
            while i < len(filename) and filename[i].isdigit():
                i += 1
            pattern += r"\d+"
            continue
        elif c in ".-_":
            pattern += "\\" + c
            i += 1
        else:
            pattern += re.escape(c)
            i += 1
    return pattern