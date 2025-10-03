import re
import os
from typing import List

class PatternMatcher:
    """
    Handles filename pattern matching using regex patterns.
    """

    def __init__(self, patterns: List[str] = None) -> None:
        self.patterns = [re.compile(p) for p in patterns] if patterns else []

    def matches(self, filename: str) -> bool:
        """
        Returns True if the filename matches any of the patterns, or if no patterns defined.
        """
        if not self.patterns:
            return True
        return any(pat.search(filename) for pat in self.patterns)

    def filter_files(self, folder: str) -> List[str]:
        """
        Returns a list of filenames in the given folder that match the patterns.
        """
        matched_files = []
        try:
            for entry in os.listdir(folder):
                if os.path.isfile(os.path.join(folder, entry)) and self.matches(entry):
                    matched_files.append(entry)
        except Exception as e:
            print(f"Error while filtering files in {folder}: {e}")
        return matched_files