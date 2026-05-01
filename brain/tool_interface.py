from __future__ import annotations

import asyncio
import logging
import re
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, AsyncIterator

log = logging.getLogger("jarvis.core")

INTERVALO_CHECK = 30.0
MAX_FALHAS      = 3
COOLDOWN_RESET  = 60.0
SEPARADORES     = re.compile(r"(?<=[.!?;:])\s+|(?<=,)\s{2,}")
MIN_CHUNK       = 20







class StatusModulo(Enum):
    OK          = "ok"
    DEGRADADO   = "degradado"
    FALHOU      = "falhou"
    REINICIANDO = "reiniciando"







@dataclass
class ToolResult:
    status:   str         = "ok"
    mensagem: str         = ""
    dados:    dict        = field(default_factory=dict)
    duracao:  float       = 0.0
    erro:     str         = ""







    @property
    def sucesso(self) -> bool:
        return self.status == "ok"







    def para_texto(self) -> str:
        if self.erro:
            return f"Erro: {self.erro}"
        return self.mensagem or str(self.dados)







    @staticmethod
    def ok(mensagem: str, dados: dict | None = None) -> "ToolResult":
        return ToolResult(status="ok", mensagem=mensagem, dados=dados or {})







    @staticmethod
    def falhou(erro: str, mensagem: str = "") -> "ToolResult":
        return ToolResult(status="erro", erro=erro, mensagem=mensagem)







    @staticmethod
    def pendente(mensagem: str) -> "ToolResult":
        return ToolResult(status="pendente", mensagem=mensagem)







ToolFn = Callable[[dict, dict], ToolResult]
REGISTRY: dict[str, ToolFn] = {}







def registrar_tool(nome: str, fn: ToolFn) -> None:
    REGISTRY[nome] = fn
    log.debug("Tool '%s' registrada.", nome)







def tool(nome: str):
    def decorator(fn: ToolFn) -> ToolFn:
        registrar_tool(nome, fn)
        return fn
    return decorator







async def executar_tool(nome: str, entrada: dict, contexto: dict | None = None) -> ToolResult:
    ctx = contexto or {}
    try:
        from brain.tool_cache import carregar_config, cache as tool_cache
        cfg       = carregar_config(nome)
        timeout_s = cfg.timeout_s
        if cfg.cache and cfg.ttl_s > 0:
            cached = tool_cache.get(nome, entrada)
            if cached is not None:
                log.debug("Tool '%s' respondeu do cache.", nome)
                return ToolResult(status="ok", mensagem=str(cached), duracao=0.0)
    except Exception:
        cfg       = None
        timeout_s = 15.0
    try:
        from storage.observability import registrar_acao, registrar_metrica
        obs_ok = True
    except Exception:
        obs_ok = False
    fn     = REGISTRY.get(nome)
    inicio = time.time()
    sucesso = True
    resultado: ToolResult
    try:
        if fn is None:
            from engine.tools_mapper import despachar as despachar_legacy
            try:
                resultado_str = await asyncio.wait_for(
                    despachar_legacy(nome, entrada), timeout=timeout_s
                )
                resultado = ToolResult(
                    status="ok",
                    mensagem=str(resultado_str),
                    duracao=time.time() - inicio,
                )
            except asyncio.TimeoutError:
                resultado = ToolResult(
                    status="erro",
                    erro=f"Timeout: '{nome}' excedeu {timeout_s:.0f}s.",
                    duracao=time.time() - inicio,
                )
                sucesso = False
            except Exception as exc:
                resultado = ToolResult(status="erro", erro=str(exc), duracao=time.time() - inicio)
                sucesso = False
        else:
            try:
                if asyncio.iscoroutinefunction(fn):
                    raw = await asyncio.wait_for(fn(entrada, ctx), timeout=timeout_s)
                else:
                    loop = asyncio.get_event_loop()
                    raw  = await asyncio.wait_for(
                        loop.run_in_executor(None, fn, entrada, ctx), timeout=timeout_s
                    )
                if isinstance(raw, ToolResult):
                    raw.duracao = time.time() - inicio
                    resultado   = raw
                else:
                    resultado = ToolResult(
                        status="ok", mensagem=str(raw), duracao=time.time() - inicio
                    )
            except asyncio.TimeoutError:
                resultado = ToolResult(
                    status="erro",
                    erro=f"Timeout: '{nome}' excedeu {timeout_s:.0f}s.",
                    duracao=time.time() - inicio,
                )
                sucesso = False
            except Exception as exc:
                log.error("Tool '%s' lançou exceção: %s", nome, exc)
                resultado = ToolResult(status="erro", erro=str(exc), duracao=time.time() - inicio)
                sucesso = False
        if (
            cfg is not None
            and cfg.cache
            and cfg.ttl_s > 0
            and resultado.sucesso
            and not resultado.mensagem.startswith(("Erro", "Timeout"))
        ):
            try:
                from brain.tool_cache import cache as tool_cache_set
                tool_cache_set.set(nome, entrada, resultado.mensagem, cfg.ttl_s)
            except Exception:
                pass
        return resultado
    finally:
        if obs_ok:
            try:
                duracao_ms = int((time.time() - inicio) * 1000)
                registrar_acao(
                    tipo="tool_exec",
                    modulo=nome,
                    descricao=str(entrada)[:200],
                    duracao_ms=duracao_ms,
                    sucesso=sucesso,
                )
                registrar_metrica(f"tool.{nome}.duracao_ms", duracao_ms, "ms")
            except Exception:
                pass







def listar_tools() -> list[str]:
    try:
        from engine.tools_mapper import EXECUTOR_FERRAMENTAS
        externas = set(EXECUTOR_FERRAMENTAS.keys())
    except (ImportError, AttributeError):
        externas = set()
    return sorted(set(REGISTRY.keys()) | externas)