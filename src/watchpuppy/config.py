import json
import os
from typing import Optional, Dict, Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigManager:
    """
    Saves and loads configuration to/from JSON or YAML files.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        ext = os.path.splitext(filepath)[1].lower()
        if ext in ['.yaml', '.yml']:
            if not HAS_YAML:
                raise ImportError("PyYAML is not installed, cannot use YAML format.")
            self.format = 'yaml'
        else:
            self.format = 'json'

    def save(self, config: Dict[str, Any]) -> None:
        """
        Saves config dictionary to file in the specified format.
        """
        with open(self.filepath, 'w', encoding='utf-8') as f:
            if self.format == 'yaml':
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(config, f, indent=4, ensure_ascii=False)

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Loads config dictionary from file. Returns None if file does not exist.
        """
        if not os.path.isfile(self.filepath):
            return None
        with open(self.filepath, 'r', encoding='utf-8') as f:
            if self.format == 'yaml':
                return yaml.safe_load(f)
            else:
                return json.load(f)