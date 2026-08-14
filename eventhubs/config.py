import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG_DIR = os.path.join(Path.home(), ".config", "eventhubs")
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "config.yaml")

VALID_CREDENTIAL_TYPES = ("default", "azurecli", "environment", "managedidentity")


def get_config_path() -> str:
    return os.environ.get("EVENTHUB_CONFIG", DEFAULT_CONFIG_PATH)


def load_config() -> Dict[str, Any]:
    path = get_config_path()
    if not os.path.exists(path):
        return {"current-context": "", "contexts": {}}
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("current-context", "")
    data.setdefault("contexts", {})
    return data


def save_config(config: Dict[str, Any]) -> None:
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_context(config: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    return config.get("contexts", {}).get(name)


def get_current_context_name(config: Dict[str, Any]) -> str:
    return config.get("current-context", "")


def get_current_context(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = get_current_context_name(config)
    if not name:
        return None
    return get_context(config, name)


def set_context(config: Dict[str, Any], name: str, values: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a context, merging with existing values."""
    contexts = config.setdefault("contexts", {})
    existing = contexts.get(name, {})
    existing.update({k: v for k, v in values.items() if v is not None})
    contexts[name] = existing
    return config


def delete_context(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    contexts = config.get("contexts", {})
    if name not in contexts:
        raise ValueError(f"context '{name}' not found")
    del contexts[name]
    if config.get("current-context") == name:
        config["current-context"] = ""
    return config


def use_context(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    if name not in config.get("contexts", {}):
        raise ValueError(f"context '{name}' not found")
    config["current-context"] = name
    return config
