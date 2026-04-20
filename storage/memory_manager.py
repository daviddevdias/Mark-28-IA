from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

import config
from google import genai

log = logging.getLogger("memory")

_lock = RLock()

MAX_VALUE_LEN: int = 400

_cache: dict | None = None


def _base_dir() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent






MEMORY_PATH: Path = _base_dir() / "api" / "long_term.json"






def _default() -> dict:
    return {
        "identity": {"mestre": {"value": ""}},
        "preferences": {"cidade": {"value": ""}},
        "projects": {},
        "relationships": {},
        "wishes": {},
        "notes": {},
    }






def load_memory(force: bool = False) -> dict:
    global _cache

    with _lock:
        if _cache is not None and not force:
            return _cache

        if not MEMORY_PATH.exists():
            _cache = _default()
            return _cache

        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))

            if not isinstance(data, dict):
                _cache = _default()
                return _cache

            base = _default()

            for k, v in base.items():
                data.setdefault(k, v)

            _cache = data
            return _cache

        except Exception:
            _cache = _default()
            return _cache






def save_memory(memory: dict) -> None:
    global _cache

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MEMORY_PATH.with_suffix(".tmp")

    with _lock:
        tmp.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(MEMORY_PATH)
        _cache = memory






def invalidate_cache() -> None:
    global _cache

    with _lock:
        _cache = None






def get_nome() -> str:
    return load_memory().get("identity", {}).get("mestre", {}).get("value", "")






def get_cidade() -> str:
    return load_memory().get("preferences", {}).get("cidade", {}).get("value", "")






def get_value(category: str, key: str, default: Any = None) -> Any:
    node = load_memory().get(category, {}).get(key, {})
    if isinstance(node, dict):
        return node.get("value", default)
    return node or default






def format_memory_for_prompt() -> str:
    mem = load_memory()
    out = ["[MEMORIA DO USUARIO]"]

    for cat, items in mem.items():
        if not isinstance(items, dict):
            continue

        out.append(f"\n{cat.upper()}:")

        for k, v in items.items():
            val = v.get("value") if isinstance(v, dict) else v
            out.append(f"  - {k}: {val}")

    return "\n".join(out)






def _merge(target: dict, updates: dict) -> bool:
    changed = False
    today = datetime.now().strftime("%Y-%m-%d")

    for key, value in updates.items():
        if value is None:
            continue

        if isinstance(value, dict) and "value" not in value:
            target.setdefault(key, {})
            if _merge(target[key], value):
                changed = True

        else:
            raw = value.get("value") if isinstance(value, dict) else value
            new = str(raw)[:MAX_VALUE_LEN].strip()

            old = target.get(key, {}).get("value") if isinstance(target.get(key), dict) else None

            if old != new:
                target[key] = {"value": new, "updated": today}
                changed = True

    return changed






def update_memory(patch: dict) -> dict:
    if not isinstance(patch, dict) or not patch:
        return load_memory()

    with _lock:
        mem = load_memory()

        if _merge(mem, patch):
            save_memory(mem)

        return mem






_CATEGORIES = "identity, preferences, projects, relationships, wishes, notes"

_PROMPT = "Extraia fatos da conversa e retorne apenas JSON:\n"






def _parse_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return None
    return None






async def process_memory_logic(user_text: str, core_text: str) -> None:
    try:
        from engine.ia_router import router

        prompt = f"{_PROMPT}{_CATEGORIES}\n\n{user_text}\n{core_text}"

        resposta = await router.responder(prompt)
        patch = _parse_json(resposta)

        if patch:
            update_memory(patch)

    except Exception:
        pass