import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

import requests

import config

TIMEOUT = 10
BASE_URL = "https://wttr.in/{cidade}?format=j1&lang=pt"
HEADERS = {"Accept-Language": "pt-BR,pt;q=0.9", "User-Agent": "CORE-Assistant/1.0"}

cache: dict = {}
CACHE_TTL = timedelta(minutes=10)

CIDADE_ALIAS = {
    "porto alegre": "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "porto alegre rs": "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "poa": "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "são paulo": "Sao+Paulo,Brazil",
    "sao paulo": "Sao+Paulo,Brazil",
    "sp": "Sao+Paulo,Brazil",
    "rio de janeiro": "Rio+de+Janeiro,Brazil",
    "rj": "Rio+de+Janeiro,Brazil",
    "belo horizonte": "Belo+Horizonte,Brazil",
    "bh": "Belo+Horizonte,Brazil",
    "curitiba": "Curitiba,Brazil",
    "brasilia": "Brasilia,Brazil",
    "brasília": "Brasilia,Brazil",
    "salvador": "Salvador,Brazil",
    "fortaleza": "Fortaleza,Brazil",
    "manaus": "Manaus,Brazil",
    "recife": "Recife,Brazil",
    "esteio": "Esteio,Rio+Grande+do+Sul,Brazil",
    "esteio rs": "Esteio,Rio+Grande+do+Sul,Brazil",
    "novo hamburgo": "Novo+Hamburgo,Rio+Grande+do+Sul,Brazil",
    "canoas": "Canoas,Rio+Grande+do+Sul,Brazil",
    "pelotas": "Pelotas,Rio+Grande+do+Sul,Brazil",
    "caxias do sul": "Caxias+do+Sul,Rio+Grande+do+Sul,Brazil",
}


def get_cidade_memoria() -> str:
    try:
        from storage.memory_manager import get_cidade

        return get_cidade() or ""
    except Exception:
        return ""


def get_cidade_painel() -> str:
    c = (getattr(config, "cidade_padrao", None) or "").strip()
    if c:
        return c
    mem = (get_cidade_memoria() or "").strip()
    if mem:
        return mem
    return "Esteio, RS"


def menciona_clima(texto_normalizado: str) -> bool:
    n = texto_normalizado
    if not n:
        return False
    if any(x in n for x in ("clima", "previsao", "temperatura", "meteorolog", "chuvisco")):
        return True
    if "do tempo" in n or "o tempo" in n or "tempo hoje" in n or "tempo amanh" in n:
        return True
    if "chuva" in n and ("amanh" in n or "hoje" in n or "clima" in n or "previs" in n):
        return True
    return False


_PLACEHOLDER_LOCAL = frozenset(
    {
        "este",
        "esta",
        "isto",
        "isso",
        "aqui",
        "mesma",
        "mesmo",
        "casa",
        "lar",
        "padrao",
        "minha",
        "cidade",
        "lugar",
        "moro",
        "vivo",
        "moramos",
        "onde",
        "eu",
        "o",
        "a",
    }
)


def extrair_cidade_do_utterance(texto: str) -> str:
    raw = (texto or "").strip()
    if not raw:
        return ""
    low = remover_acentos(raw.lower())
    low = re.sub(r"[^\w\s,]", " ", low)
    low = re.sub(r"\s+", " ", low).strip()
    chaves = (
        " na cidade de ",
        " cidade de ",
        " em que cidade ",
        " na cidade ",
        " para a cidade de ",
        " para cidade de ",
        " para ",
        " em ",
        " no ",
        " na ",
    )
    for key in chaves:
        if key in low:
            tail = low.rsplit(key, 1)[-1].strip()
            toks = [t for t in tail.split() if t]
            if not toks:
                return ""
            if len(toks) == 1 and toks[0] in _PLACEHOLDER_LOCAL:
                return ""
            if all(t in _PLACEHOLDER_LOCAL for t in toks):
                return ""
            return tail.strip(" .,!?")[:80]
    lixo = {
        "jarvis",
        "qual",
        "e",
        "a",
        "o",
        "de",
        "da",
        "do",
        "das",
        "dos",
        "me",
        "diz",
        "dig",
        "informe",
        "quero",
        "saber",
        "por",
        "favor",
        "please",
        "como",
        "esta",
        "hoje",
        "amanha",
        "agora",
        "previsao",
        "previsao",
        "tempo",
        "clima",
        "temperatura",
        "qual",
        "o",
        "a",
        "do",
        "no",
        "na",
        "em",
        "para",
        "que",
        "foi",
        "sera",
        "vai",
        "fazer",
        "mostra",
        "mostre",
        "daqui",
        "nessa",
        "nesta",
        "nessa",
        "cidade",
    }
    toks = [t for t in low.split() if t and t not in lixo]
    tail = " ".join(toks).strip()
    if not tail:
        return ""
    if tail in _PLACEHOLDER_LOCAL or all(t in _PLACEHOLDER_LOCAL for t in tail.split()):
        return ""
    if len(tail) < 2 or len(tail) > 60:
        return ""
    return tail


def remover_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def sanitizar_localidade(cidade: str) -> str:
    if not cidade:
        cidade = get_cidade_painel()

    cidade = cidade.strip().lower()
    alias = CIDADE_ALIAS.get(cidade)
    if not alias:
        alias = CIDADE_ALIAS.get(remover_acentos(cidade))
    if alias:
        return alias

    cidade = re.sub(r"[^\w\s,]", " ", cidade)
    cidade = re.sub(r"\s+", " ", cidade).strip()
    if "brazil" not in cidade and "brasil" not in cidade:
        cidade = cidade + ",Brazil"
    return cidade.replace(" ", "+")


def requisitar_telemetria(cidade: str = "") -> Optional[dict]:
    now = datetime.now()
    if not cidade:
        cidade = get_cidade_painel()

    cidade_alvo = sanitizar_localidade(cidade)
    if not cidade_alvo:
        return None

    if cidade_alvo in cache:
        dados, ts = cache[cidade_alvo]
        if now - ts < CACHE_TTL:
            return dados

    try:
        url = BASE_URL.format(cidade=cidade_alvo)
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        dados = res.json()
        if isinstance(dados, dict) and "current_condition" in dados:
            cache[cidade_alvo] = (dados, now)
            return dados
        return None
    except Exception:
        return None


def extrair_descricao(bloco: dict) -> str:
    try:
        return bloco.get("lang_pt", [{}])[0].get("value", "Estável")
    except Exception:
        return "Estável"


def obter_previsao_hoje(cidade_alvo: str = "") -> str:
    alvo = (cidade_alvo or get_cidade_painel()).strip()
    dados = requisitar_telemetria(alvo)
    if not dados:
        return f"Não consegui obter o clima para '{alvo}'."

    try:
        atual = dados["current_condition"][0]
        temp = atual.get("temp_C", "??")
        sensacao = atual.get("FeelsLikeC", "??")
        desc = extrair_descricao(atual)
        umidade = atual.get("humidity", "??")
        vento = atual.get("windspeedKmph", "??")
        regiao = dados.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", alvo)

        return (
            f"Em {regiao}: {desc.lower()}, {temp}°C, "
            f"sensação de {sensacao}°C, "
            f"umidade {umidade}%, vento {vento} km/h."
        )
    except Exception:
        return "Dados meteorológicos incompletos."


def verificar_chuva_amanha(cidade_alvo: str = "") -> str:
    alvo = (cidade_alvo or get_cidade_painel()).strip()
    dados = requisitar_telemetria(alvo)
    if not dados or "weather" not in dados or len(dados["weather"]) < 2:
        return "Previsão indisponível."

    try:
        amanha = dados["weather"][1]
        horario = amanha["hourly"][4]
        desc = extrair_descricao(horario)
        chuva = horario.get("precipMM", "0")
        temp_max = amanha.get("maxtempC", "??")
        temp_min = amanha.get("mintempC", "??")

        return (
            f"Amanhã em {alvo.title()}: {desc.lower()}, "
            f"{chuva} mm de chuva, "
            f"mínima {temp_min}°C e máxima {temp_max}°C."
        )
    except Exception:
        return "Erro ao montar a previsão."


def limpar_cache_clima() -> None:
    cache.clear()


def obter_clima_raw(cidade_alvo: str) -> str:
    alvo = cidade_alvo if cidade_alvo else get_cidade_painel()
    dados = requisitar_telemetria(alvo)
    return json.dumps(dados if dados else {"error": f"Falha ao obter clima para '{alvo}'."})
