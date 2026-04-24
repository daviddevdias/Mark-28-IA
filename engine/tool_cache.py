from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


log = logging.getLogger("jarvis.tool_cache")


@dataclass
class Entrada:
    valor: Any
    criado_em: float
    ttl: float

    @property







    def expirado(self) -> bool:
        return (time.monotonic() - self.criado_em) > self.ttl


@dataclass
class ConfigTool:
    timeout_s: float  = 15.0
    ttl_s: float      = 0.0
    cache: bool       = False
    nome: str         = ""


CONFIGS: dict[str, ConfigTool] = {
    "weather_report":   ConfigTool(10.0,  600.0, True,  "Clima"),
    "web_search":       ConfigTool(20.0,  120.0, True,  "Web"),
    "smart_home":       ConfigTool(8.0,   30.0,  True,  "Casa"),
    "spotify_control":  ConfigTool(8.0,   0.0,   False, "Spotify"),
    "open_app":         ConfigTool(12.0,  0.0,   False, "App"),
    "computer_control": ConfigTool(10.0,  0.0,   False, "PC"),
    "cmd_control":      ConfigTool(20.0,  0.0,   False, "CMD"),
    "youtube_video":    ConfigTool(30.0,  0.0,   False, "YouTube"),
    "screen_analysis":  ConfigTool(25.0,  0.0,   False, "Visão"),
    "file_controller":  ConfigTool(10.0,  0.0,   False, "Arquivos"),
    "set_reminder":     ConfigTool(5.0,   0.0,   False, "Alarme"),
    "save_memory":      ConfigTool(5.0,   0.0,   False, "Memória"),
    "agent_task":       ConfigTool(45.0,  0.0,   False, "Agente"),
    "code_helper":      ConfigTool(30.0,  0.0,   False, "Código"),
    "switch_ia_mode":   ConfigTool(5.0,   0.0,   False, "IA Mode"),
}

DEFAULT = ConfigTool()


class Cache:







    def __init__(self, max_itens: int = 256):
        self._store: dict[str, Entrada] = {}
        self._max   = max_itens
        self._hits  = 0
        self._miss  = 0







    def chave(self, tool: str, args: dict) -> str:
        raw = json.dumps({"t": tool, "a": args}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]







    def get(self, tool: str, args: dict) -> Optional[Any]:
        k = self._chave(tool, args)
        e = self._store.get(k)
        if e is None or e.expirado:
            self._store.pop(k, None)
            self._miss += 1
            return None
        self._hits += 1
        return e.valor







    def set(self, tool: str, args: dict, valor: Any, ttl: float) -> None:
        if len(self._store) >= self._max:
            mais_velho = min(self._store, key=lambda k: self._store[k].criado_em)
            del self._store[mais_velho]
        self._store[self._chave(tool, args)] = Entrada(valor, time.monotonic(), ttl)







    def invalidar(self, tool: str) -> int:
        chaves = [k for k in list(self._store) if tool in k]
        for k in chaves:
            del self._store[k]
        return len(chaves)







    def limpar(self) -> None:
        self._store.clear()





    @property







    def stats(self) -> dict:
        total = self._hits + self._miss
        return {
            "hits": self._hits,
            "misses": self._miss,
            "taxa_hit": f"{(self._hits / total * 100) if total else 0:.1f}%",
            "ativos": sum(1 for e in self._store.values() if not e.expirado),
        }





cache = Cache()







def cfg(nome: str) -> ConfigTool:
    return CONFIGS.get(nome, DEFAULT)







async def despachar(nome: str, args: dict, func: Callable) -> Any:
    c = cfg(nome)

    if c.cache and c.ttl_s > 0:
        cached = cache.get(nome, args)
        if cached is not None:
            return cached

    try:
        resultado = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, func, args),
            timeout=c.timeout_s,
        )




    except asyncio.TimeoutError:
        log.warning("Timeout '%s' (%.0fs)", nome, c.timeout_s)
        return f"Timeout: '{nome}' não respondeu em {c.timeout_s:.0f}s."
    except Exception as e:
        log.error("Erro '%s': %s", nome, e)
        return f"Erro em '{nome}': {e}"




    if c.cache and c.ttl_s > 0:
        if isinstance(resultado, str) and not resultado.startswith(("Erro", "Timeout")):
            cache.set(nome, args, resultado, c.ttl_s)

    return resultado







def stats_cache() -> dict:
    return cache.stats







def invalidar(nome: str) -> str:
    n = cache.invalidar(nome)
    return f"{n} entrada(s) removida(s) de '{nome}'."







def limpar_cache() -> str:
    cache.limpar()
    return "Cache limpo."