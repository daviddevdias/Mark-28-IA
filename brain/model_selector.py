from __future__ import annotations

import re
import requests
import math
import time
import psutil
from dataclasses import dataclass
from enum import Enum
from typing import Any

log = __import__("logging").getLogger("jarvis.model_selector")

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
    "phi3": PerfilModelo("phi3", NivelModelo.RAPIDO, 512, ["saudacao", "comando_simples", "status", "volume", "alarme_simples"]),
    "llama3": PerfilModelo("llama3", NivelModelo.INTERMEDIARIO, 1024, ["busca", "clima", "spotify", "app", "conversa_curta"]),
    "qwen/qwen-vl-max": PerfilModelo("qwen/qwen-vl-max", NivelModelo.PESADO, 2048, ["visao", "codigo", "plano", "analise", "conversa_longa", "agente"]),
}

PADROES_RAPIDOS = re.compile(r"^(oi|ol[aá]|ei|ok|sim|n[aã]o|obrigado|tchau|status|volume|parar|continuar|pr[oó]xim[ao]|anterior|pausar|ligar|desligar|hora|data)\b", re.IGNORECASE)
PADROES_PESADOS = re.compile(r"(codi(go|ficar)|progra(mar|me)|an[aá]l(ise|isa)|plan(eja|o|ejar)|expli(que|ca|ca[cç][aã]o)|resumo|resumir|complexo|detalh|escreva|cri(e|ar)|desenvolv|arquitetura|debug)", re.IGNORECASE)
PADROES_VISAO = re.compile(r"(tela|ecr[aã]|imagem|foto|captur|veja|olh(e|a)|vis[aã]o|mostr[ae])", re.IGNORECASE)







def buscar_modelos_ollama() -> set[str]:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
        if r.status_code == 200:
            return {m["name"] for m in r.json().get("models", [])}
    except Exception:
        pass
    return set()







def modelo_rapido_disponivel(modelos: set[str]) -> str | None:
    for c in ("phi3:mini", "phi3", "llama3:8b", "llama3"):
        if c in modelos: return c
    return None







def modelo_atual() -> str:
    try:
        from engine.ia_router import modelo as modelo_ativo
        return modelo_ativo or "qwen/qwen-vl-max"
    except Exception:
        return "qwen/qwen-vl-max"







def calcular_probabilidade(sucesso_previo, stress_hw, peso_complexidade):
    likelihood = math.exp(-peso_complexidade * stress_hw)
    marginal = (sucesso_previo * likelihood) + ((1 - sucesso_previo) * (1 - likelihood))
    return 0.0 if marginal == 0 else max(0.01, min(0.99, (likelihood * sucesso_previo) / marginal))







def avaliar_monte_carlo(comando: str):
    sucesso_local, sucesso_nuvem = 0, 0
    complexidade = len(comando) * 0.05
    for i in range(50): 
        stress = (time.time() * 1000 % 100) / 100.0
        if calcular_probabilidade(0.65, stress, complexidade) > 0.5: sucesso_local += 1
        if calcular_probabilidade(0.95, 0.1, complexidade * 0.5) > 0.5: sucesso_nuvem += 1
    return sucesso_local / 50.0







def obter_vram_estimada() -> float:
    return psutil.virtual_memory().percent / 100.0







def escolher_modelo(contexto: dict[str, Any]) -> str:
    comando = contexto.get("comando", "")
    tem_imagem = bool(contexto.get("imagem"))
    forcado = contexto.get("modelo_forcado", "")
    historico_len = contexto.get("historico_len", 0)
    if forcado and forcado in PERFIS: return forcado
    if tem_imagem or PADROES_VISAO.search(comando): return "qwen/qwen-vl-max"
    vram = obter_vram_estimada()
    if vram > 0.85:
        return "qwen/qwen-vl-max"
    confianca_local = avaliar_monte_carlo(comando)
    if confianca_local < 0.60:
        return "qwen/qwen-vl-max"
    if PADROES_PESADOS.search(comando) or historico_len > 10: return modelo_atual()
    if PADROES_RAPIDOS.match(comando.strip()) and historico_len < 3:
        rapido = modelo_rapido_disponivel(buscar_modelos_ollama())
        if rapido: return rapido
    return modelo_atual()







def nivel_do_modelo(nome: str) -> NivelModelo:
    perfil = PERFIS.get(nome)
    if perfil: return perfil.nivel
    if "phi" in nome.lower(): return NivelModelo.RAPIDO
    if "llama3" in nome.lower() or "mistral" in nome.lower(): return NivelModelo.INTERMEDIARIO
    return NivelModelo.PESADO