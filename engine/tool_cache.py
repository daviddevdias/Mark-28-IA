from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger("jarvis.tool_cache")


@dataclass
class EntradaCache:
    valor: Any
    criado_em: float
    ttl: float

    @property
    def expirado(self) -> bool:
        return (time.monotonic() - self.criado_em) > self.ttl

    @property
    def idade_s(self) -> float:
        return time.monotonic() - self.criado_em


@dataclass
class ConfigFerramenta:
    timeout_s: float = 15.0
    ttl_cache_s: float = 0.0
    cache_ativo: bool = False
    nome: str = ""


_CONFIGS: dict[str, ConfigFerramenta] = {
    "weather_report":   ConfigFerramenta(timeout_s=10.0, ttl_cache_s=600.0,  cache_ativo=True,  nome="Clima"),
    "web_search":       ConfigFerramenta(timeout_s=20.0, ttl_cache_s=120.0,  cache_ativo=True,  nome="Web"),
    "smart_home":       ConfigFerramenta(timeout_s=8.0,  ttl_cache_s=30.0,   cache_ativo=True,  nome="Casa"),
    "spotify_control":  ConfigFerramenta(timeout_s=8.0,  ttl_cache_s=0.0,    cache_ativo=False, nome="Spotify"),
    "open_app":         ConfigFerramenta(timeout_s=12.0, ttl_cache_s=0.0,    cache_ativo=False, nome="App"),
    "computer_control": ConfigFerramenta(timeout_s=10.0, ttl_cache_s=0.0,    cache_ativo=False, nome="PC"),
    "cmd_control":      ConfigFerramenta(timeout_s=20.0, ttl_cache_s=0.0,    cache_ativo=False, nome="CMD"),
    "youtube_video":    ConfigFerramenta(timeout_s=30.0, ttl_cache_s=0.0,    cache_ativo=False, nome="YouTube"),
    "screen_analysis":  ConfigFerramenta(timeout_s=25.0, ttl_cache_s=0.0,    cache_ativo=False, nome="Visão"),
    "file_controller":  ConfigFerramenta(timeout_s=10.0, ttl_cache_s=0.0,    cache_ativo=False, nome="Arquivos"),
    "set_reminder":     ConfigFerramenta(timeout_s=5.0,  ttl_cache_s=0.0,    cache_ativo=False, nome="Alarme"),
    "save_memory":      ConfigFerramenta(timeout_s=5.0,  ttl_cache_s=0.0,    cache_ativo=False, nome="Memória"),
    "agent_task":       ConfigFerramenta(timeout_s=45.0, ttl_cache_s=0.0,    cache_ativo=False, nome="Agente"),
    "code_helper":      ConfigFerramenta(timeout_s=30.0, ttl_cache_s=0.0,    cache_ativo=False, nome="Código"),
    "switch_ia_mode":   ConfigFerramenta(timeout_s=5.0,  ttl_cache_s=0.0,    cache_ativo=False, nome="IA Mode"),
}

_DEFAULT_CONFIG = ConfigFerramenta(timeout_s=15.0, ttl_cache_s=0.0, cache_ativo=False, nome="Desconhecida")


class CacheFerramenta:
    def __init__(self, max_entradas: int = 256):
        self._store: dict[str, EntradaCache] = {}
        self._max = max_entradas
        self._hits = 0
        self._misses = 0

    def _chave(self, tool: str, args: dict) -> str:
        payload = json.dumps({"t": tool, "a": args}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def get(self, tool: str, args: dict) -> Optional[Any]:
        k = self._chave(tool, args)
        entrada = self._store.get(k)
        if entrada is None or entrada.expirado:
            if entrada:
                del self._store[k]
            self._misses += 1
            return None
        self._hits += 1
        log.debug("Cache HIT '%s' (%.0fs de idade)", tool, entrada.idade_s)
        return entrada.valor

    def set(self, tool: str, args: dict, valor: Any, ttl: float) -> None:
        if len(self._store) >= self._max:
            mais_antigo = min(self._store, key=lambda k: self._store[k].criado_em)
            del self._store[mais_antigo]
        k = self._chave(tool, args)
        self._store[k] = EntradaCache(valor=valor, criado_em=time.monotonic(), ttl=ttl)

    def invalidar(self, tool: str) -> int:
        removidos = [k for k in list(self._store) if tool in k]
        for k in removidos:
            del self._store[k]
        return len(removidos)

    def limpar(self) -> None:
        self._store.clear()

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        taxa = (self._hits / total * 100) if total else 0
        vivos = sum(1 for e in self._store.values() if not e.expirado)
        return {
            "hits": self._hits,
            "misses": self._misses,
            "taxa_hit": f"{taxa:.1f}%",
            "entradas_vivas": vivos,
        }


_cache_global = CacheFerramenta()


def config_da_ferramenta(nome: str) -> ConfigFerramenta:
    return _CONFIGS.get(nome, _DEFAULT_CONFIG)


def executar_com_timeout(
    func: Callable[[dict], Any],
    args: dict,
    timeout_s: float,
    nome_tool: str,
) -> Any:
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(func, args)
        try:
            return future.result(timeout=timeout_s)
        except concurrent.futures.TimeoutError:
            log.warning("Timeout na ferramenta '%s' (%.0fs)", nome_tool, timeout_s)
            return f"Timeout: '{nome_tool}' não respondeu em {timeout_s:.0f}s."
        except Exception as e:
            log.error("Erro na ferramenta '%s': %s", nome_tool, e)
            return f"Erro em '{nome_tool}': {e}"


async def executar_com_timeout_async(
    func: Callable[[dict], Any],
    args: dict,
    timeout_s: float,
    nome_tool: str,
) -> Any:
    loop = asyncio.get_event_loop()
    try:
        resultado = await asyncio.wait_for(
            loop.run_in_executor(None, func, args),
            timeout=timeout_s,
        )
        return resultado
    except asyncio.TimeoutError:
        log.warning("Timeout async na ferramenta '%s' (%.0fs)", nome_tool, timeout_s)
        return f"Timeout: '{nome_tool}' não respondeu em {timeout_s:.0f}s."
    except Exception as e:
        log.error("Erro async na ferramenta '%s': %s", nome_tool, e)
        return f"Erro em '{nome_tool}': {e}"


async def despachar_ferramenta(nome: str, args: dict, func: Callable) -> Any:
    cfg = config_da_ferramenta(nome)

    if cfg.cache_ativo and cfg.ttl_cache_s > 0:
        cached = _cache_global.get(nome, args)
        if cached is not None:
            return cached

    resultado = await executar_com_timeout_async(func, args, cfg.timeout_s, nome)

    if cfg.cache_ativo and cfg.ttl_cache_s > 0:
        if isinstance(resultado, str) and not resultado.startswith(("Erro", "Timeout")):
            _cache_global.set(nome, args, resultado, cfg.ttl_cache_s)

    return resultado


def stats_cache() -> dict:
    return _cache_global.stats


def invalidar_cache_tool(nome: str) -> str:
    n = _cache_global.invalidar(nome)
    return f"{n} entrada(s) removida(s) do cache de '{nome}'."


def limpar_cache() -> str:
    _cache_global.limpar()
    return "Cache limpo."