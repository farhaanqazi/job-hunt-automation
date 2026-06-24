import pathlib
import yaml

TARGET_COMPANIES_PATH = "config/target_companies.yaml"
ATS_DIRECTORY_PATH = "config/ats_directory.yaml"

def _load_yaml(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def _save_yaml(path: str, data: dict) -> None:
    pathlib.Path(path).write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")

def load_targets() -> dict:
    return _load_yaml(TARGET_COMPANIES_PATH)

def load_ats_directory() -> dict:
    return _load_yaml(ATS_DIRECTORY_PATH)

def add_target(ats_type: str, company: str, token: str) -> None:
    data = load_targets()
    if ats_type not in data:
        data[ats_type] = []
    
    token_key = "board_token" if ats_type == "greenhouse" else "handle"
    
    # Check if already exists
    for item in data[ats_type]:
        if item.get(token_key) == token:
            item["enabled"] = True
            _save_yaml(TARGET_COMPANIES_PATH, data)
            return

    data[ats_type].append({
        "company": company,
        token_key: token,
        "enabled": True
    })
    _save_yaml(TARGET_COMPANIES_PATH, data)

def toggle_target(ats_type: str, token: str, enabled: bool) -> None:
    data = load_targets()
    if ats_type not in data:
        return
        
    token_key = "board_token" if ats_type == "greenhouse" else "handle"
    for item in data[ats_type]:
        if item.get(token_key) == token:
            item["enabled"] = enabled
            break
            
    _save_yaml(TARGET_COMPANIES_PATH, data)

def delete_target(ats_type: str, token: str) -> None:
    data = load_targets()
    if ats_type not in data:
        return
        
    token_key = "board_token" if ats_type == "greenhouse" else "handle"
    data[ats_type] = [item for item in data[ats_type] if item.get(token_key) != token]
    _save_yaml(TARGET_COMPANIES_PATH, data)
