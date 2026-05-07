from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("jarvis.tool_interface")

@dataclass
class ToolResult:
    status:   str  = "ok"
    mensagem: str  = ""
    dados:    dict = field(default_factory=dict)
    duracao:  float = 0.0
    erro:     str  = ""








    @property
    def sucesso(self) -> bool:
        return self.status == "ok"








    def para_texto(self) -> str:
        return f"Erro: {self.erro}" if self.erro else (self.mensagem or str(self.dados))








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
    ctx    = contexto or {}
    inicio = time.time()
    sucesso = True

    cfg: object = None
    timeout_s   = 15.0
    try:
        from brain.tool_cache import carregar_config, cache as tool_cache
        cfg       = carregar_config(nome)
        timeout_s = cfg.timeout_s
        if cfg.cache and cfg.ttl_s > 0:
            cached = tool_cache.get(nome, entrada)
            if cached is not None:
                return ToolResult(status="ok", mensagem=str(cached))


    except Exception:
        pass


    fn = REGISTRY.get(nome)
    try:
        if fn is None:
            from engine.tools_mapper import despachar as despachar_legado
            raw = await asyncio.wait_for(despachar_legado(nome, entrada), timeout=timeout_s)
        elif asyncio.iscoroutinefunction(fn):
            raw = await asyncio.wait_for(fn(entrada, ctx), timeout=timeout_s)
        else:
            raw = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, fn, entrada, ctx),
                timeout=timeout_s,
            )


        resultado = raw if isinstance(raw, ToolResult) else ToolResult(status="ok", mensagem=str(raw))

    except asyncio.TimeoutError:
        sucesso   = False
        resultado = ToolResult(status="erro", erro=f"Timeout: '{nome}' excedeu {timeout_s:.0f}s.")
    except Exception as exc:
        sucesso   = False
        log.error("Tool '%s' erro: %s", nome, exc)
        resultado = ToolResult(status="erro", erro=str(exc))


    resultado.duracao = time.time() - inicio

    if (
        cfg and cfg.cache and cfg.ttl_s > 0
        and resultado.sucesso
        and not resultado.mensagem.startswith(("Erro", "Timeout"))
    ):
        try:
            from brain.tool_cache import cache as cache_local
            cache_local.set(nome, entrada, resultado.mensagem, cfg.ttl_s)
        except Exception:
            pass


    try:
        from storage.observability import registrar_acao, registrar_metrica
        duracao_ms = int(resultado.duracao * 1000)
        registrar_acao(tipo="tool_exec", modulo=nome, descricao=str(entrada)[:200],
                       duracao_ms=duracao_ms, sucesso=sucesso)
        registrar_metrica(f"tool.{nome}.duracao_ms", duracao_ms, "ms")
    except Exception:
        pass


    return resultado








def listar_tools() -> list[str]:
    try:
        from engine.tools_mapper import EXECUTOR_FERRAMENTAS
        externas = set(EXECUTOR_FERRAMENTAS.keys())
    except (ImportError, AttributeError):
        externas = set()


    return sorted(set(REGISTRY.keys()) | externas)