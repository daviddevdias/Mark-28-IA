from __future__ import annotations

import logging
import re
import requests
from dataclasses import dataclass
from enum import Enum
from typing import Any

log = logging.getLogger("jarvis.model_selector")


class NivelModelo(Enum):
    RAPIDO        = "rapido"
    INTERMEDIARIO = "intermediario"
    PESADO        = "pesado"


@dataclass
class PerfilModelo:
    nome:          str
    nivel:         NivelModelo
    max_tokens:    int
    adequado_para: list[str]


PERFIS: dict[str, PerfilModelo] = {
    "phi3": PerfilModelo(
        nome="phi3",
        nivel=NivelModelo.RAPIDO,
        max_tokens=512,
        adequado_para=["saudacao", "comando_simples", "status", "volume", "alarme_simples"],
    ),
    "llama3": PerfilModelo(
        nome="llama3",
        nivel=NivelModelo.INTERMEDIARIO,
        max_tokens=1024,
        adequado_para=["busca", "clima", "spotify", "app", "conversa_curta"],
    ),
    "qwen/qwen-vl-max": PerfilModelo(
        nome="qwen/qwen-vl-max",
        nivel=NivelModelo.PESADO,
        max_tokens=2048,
        adequado_para=["visao", "codigo", "plano", "analise", "conversa_longa", "agente"],
    ),
}

PADROES_RAPIDOS = re.compile(
    r"^(oi|ol[aá]|ei|ok|sim|n[aã]o|obrigado|tchau|status|volume|parar|continuar|"
    r"pr[oó]xim[ao]|anterior|pausar|ligar|desligar|hora|data)\b",
    re.IGNORECASE,
)

PADROES_PESADOS = re.compile(
    r"(codi(go|ficar)|progra(mar|me)|an[aá]l(ise|isa)|plan(eja|o|ejar)|"
    r"expli(que|ca|ca[cç][aã]o)|resumo|resumir|complexo|detalh|escreva|"
    r"cri(e|ar)|desenvolv|arquitetura|debug)",
    re.IGNORECASE,
)

PADROES_VISAO = re.compile(
    r"(tela|ecr[aã]|imagem|foto|captur|veja|olh(e|a)|vis[aã]o|mostr[ae])",
    re.IGNORECASE,
)


def buscar_modelos_ollama() -> set[str]:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
        if r.status_code == 200:
            return {m["name"] for m in r.json().get("models", [])}
    except Exception:
        pass
    return set()


def modelo_rapido_disponivel(modelos: set[str]) -> str | None:
    candidatos = ("phi3:mini", "phi3", "llama3:8b", "llama3")
    for c in candidatos:
        if c in modelos:
            return c
    return None


def modelo_atual() -> str:
    try:
        from engine.ia_router import modelo as modelo_ativo
        return modelo_ativo or "qwen/qwen-vl-max"
    except Exception:
        return "qwen/qwen-vl-max"


def escolher_modelo(contexto: dict[str, Any]) -> str:
    comando:       str  = contexto.get("comando", "")
    tem_imagem:    bool = bool(contexto.get("imagem"))
    forcado:       str  = contexto.get("modelo_forcado", "")
    historico_len: int  = contexto.get("historico_len", 0)

    if forcado and forcado in PERFIS:
        return forcado

    if tem_imagem or PADROES_VISAO.search(comando):
        return "qwen/qwen-vl-max"

    if PADROES_PESADOS.search(comando) or historico_len > 10:
        return modelo_atual()

    if PADROES_RAPIDOS.match(comando.strip()) and historico_len < 3:
        modelos = buscar_modelos_ollama()
        rapido  = modelo_rapido_disponivel(modelos)
        if rapido:
            return rapido

    return modelo_atual()


def nivel_do_modelo(nome: str) -> NivelModelo:
    perfil = PERFIS.get(nome)
    if perfil:
        return perfil.nivel
    if "phi" in nome.lower():
        return NivelModelo.RAPIDO
    if "llama3" in nome.lower() or "mistral" in nome.lower():
        return NivelModelo.INTERMEDIARIO
    return NivelModelo.PESADO