import json
from pathlib import Path
from typing import Any, Dict, List


def ensure_required_fields(page: Dict[str, Any]) -> bool:
    return bool(page.get('url') and page.get('title') and page.get('sections'))


def validate_json(path: Path) -> bool:
    try:
        with path.open('r', encoding='utf-8') as fh:
            json.load(fh)
        return True
    except Exception:
        return False


def ensure_no_major_duplicates(items: List[Dict[str, Any]]) -> bool:
    if not items:
        return True
    seen = set()
    for item in items:
        sig = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if sig in seen:
            return False
        seen.add(sig)
    return True
