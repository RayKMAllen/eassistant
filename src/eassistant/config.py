from pathlib import Path
from typing import Any, Dict, cast

import yaml


def get_config() -> Dict[str, Any]:
    """
    Reads the config file and returns the config object.
    """
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return cast(Dict[str, Any], config_data)


config: Dict[str, Any] = get_config()
