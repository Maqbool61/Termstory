import os
import json
from typing import List, Any

def get_history_files() -> List[str]:
    """Return a list of existing shell history file paths"""
    history_files = []
    
    # Check default paths for zsh and bash
    zsh_hist = os.path.expanduser("~/.zsh_history")
    bash_hist = os.path.expanduser("~/.bash_history")
    
    if os.path.exists(zsh_hist):
        history_files.append(zsh_hist)
    if os.path.exists(bash_hist):
        history_files.append(bash_hist)
        
    return history_files

def get_db_path() -> str:
    """Return the path to the sqlite database, creating parent directories if needed"""
    db_dir = os.path.expanduser("~/.termstory")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "termstory.db")

def get_config_path() -> str:
    """Return the path to the config JSON file"""
    db_dir = os.path.expanduser("~/.termstory")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "config.json")

def translate_legacy_key(config: dict, key: str) -> str:
    """Translate a legacy flat config key to the new nested dot path structure."""
    if key == "groq_api_key":
        return "providers.groq.api_key"
    if key == "ai_provider":
        return "active_provider"
    if key == "model_name":
        provider = config.get("active_provider", "groq")
        if provider == "disabled":
            provider = "groq"
        return f"providers.{provider}.model_name"
    if key == "api_base_url":
        provider = config.get("active_provider", "groq")
        if provider == "disabled":
            provider = "groq"
        return f"providers.{provider}.api_base_url"
    return key

def get_config_value(config: dict, path: str) -> Any:
    """Retrieve a configuration value using a dot-separated path (e.g. 'providers.groq.api_key')"""
    path = translate_legacy_key(config, path)
    parts = path.split(".")
    curr = config
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return curr

def set_config_value(config: dict, path: str, value: Any) -> None:
    """Set a configuration value using a dot-separated path, creating parent dicts if needed"""
    path = translate_legacy_key(config, path)
    parts = path.split(".")
    curr = config
    for part in parts[:-1]:
        if part not in curr or not isinstance(curr[part], dict):
            curr[part] = {}
        curr = curr[part]
    curr[parts[-1]] = value

def load_config() -> dict:
    """Load configuration dictionary from disk, returning defaults and migrating legacy config if needed"""
    config_path = get_config_path()
    defaults = {
        "ai_enabled": False,
        "active_provider": "disabled",  # "groq", "openai", "ollama", "disabled"
        "providers": {
            "groq": {
                "api_key": "",
                "api_base_url": "https://api.groq.com/openai/v1",
                "model_name": "llama-3.1-8b-instant"
            },
            "openai": {
                "api_key": "",
                "api_base_url": "https://api.openai.com/v1",
                "model_name": "gpt-4o-mini"
            },
            "ollama": {
                "api_key": "",
                "api_base_url": "http://localhost:11434/v1",
                "model_name": "llama3"
            }
        },
        "has_seen_onboarding": False
    }
    
    # 1. Read existing config file
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}
            
    # 2. Perform legacy key migrations
    migrated = False
    if "ai_provider" in config:
        config["active_provider"] = config.pop("ai_provider")
        migrated = True
    if "groq_api_key" in config:
        if "providers" not in config:
            config["providers"] = {}
        if "groq" not in config["providers"]:
            config["providers"]["groq"] = {}
        config["providers"]["groq"]["api_key"] = config.pop("groq_api_key")
        migrated = True
        
    if "api_base_url" in config:
        val = config.pop("api_base_url")
        prov = config.get("active_provider", "groq")
        if prov == "disabled":
            prov = "groq"
        if "providers" not in config:
            config["providers"] = {}
        if prov not in config["providers"]:
            config["providers"][prov] = {}
        config["providers"][prov]["api_base_url"] = val
        migrated = True
        
    if "model_name" in config:
        val = config.pop("model_name")
        prov = config.get("active_provider", "groq")
        if prov == "disabled":
            prov = "groq"
        if "providers" not in config:
            config["providers"] = {}
        if prov not in config["providers"]:
            config["providers"][prov] = {}
        config["providers"][prov]["model_name"] = val
        migrated = True
        
    # 3. Recursively merge defaults
    def merge_defaults(tgt: dict, src: dict) -> bool:
        changed = False
        for k, v in src.items():
            if k not in tgt:
                tgt[k] = json.loads(json.dumps(v))
                changed = True
            elif isinstance(v, dict) and isinstance(tgt[k], dict):
                if merge_defaults(tgt[k], v):
                    changed = True
        return changed
        
    defaults_merged = merge_defaults(config, defaults)
    
    if migrated or defaults_merged:
        save_config(config)
        
    return config

def save_config(config: dict) -> None:
    """Save configuration dictionary to disk"""
    config_path = get_config_path()
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass
