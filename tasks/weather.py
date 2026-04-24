import requests
import unicodedata
from datetime import datetime, timedelta
from typing import Optional
import json
import re
import config

TIMEOUT = 10
BASE_URL = "https://wttr.in/{cidade}?format=j1&lang=pt"
HEADERS = {"Accept-Language": "pt-BR,pt;q=0.9", "User-Agent": "CORE-Assistant/1.0"}

cache: dict = {}
CACHE_TTL = timedelta(minutes=10)

CIDADE_ALIAS = {
    "porto alegre":      "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "porto alegre rs":   "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "poa":               "Porto+Alegre,Rio+Grande+do+Sul,Brazil",
    "são paulo":         "Sao+Paulo,Brazil",
    "sao paulo":         "Sao+Paulo,Brazil",
    "sp":                "Sao+Paulo,Brazil",
    "rio de janeiro":    "Rio+de+Janeiro,Brazil",
    "rj":                "Rio+de+Janeiro,Brazil",
    "belo horizonte":    "Belo+Horizonte,Brazil",
    "bh":                "Belo+Horizonte,Brazil",
    "curitiba":          "Curitiba,Brazil",
    "brasilia":          "Brasilia,Brazil",
    "brasília":          "Brasilia,Brazil",
    "salvador":          "Salvador,Brazil",
    "fortaleza":         "Fortaleza,Brazil",
    "manaus":            "Manaus,Brazil",
    "recife":            "Recife,Brazil",
    "esteio":            "Esteio,Rio+Grande+do+Sul,Brazil",
    "esteio rs":         "Esteio,Rio+Grande+do+Sul,Brazil",
    "novo hamburgo":     "Novo+Hamburgo,Rio+Grande+do+Sul,Brazil",
    "canoas":            "Canoas,Rio+Grande+do+Sul,Brazil",
    "pelotas":           "Pelotas,Rio+Grande+do+Sul,Brazil",
    "caxias do sul":     "Caxias+do+Sul,Rio+Grande+do+Sul,Brazil",
}







def get_cidade_painel() -> str:
    return getattr(config, "cidade_padrao", "Esteio,RS")







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
        return f"Senhor, falha na conexão com a Nuvem Oracle para '{alvo}'."

    try:
        atual = dados["current_condition"][0]
        temp     = atual.get("temp_C", "??")
        sensacao = atual.get("FeelsLikeC", "??")
        desc     = extrair_descricao(atual)
        umidade  = atual.get("humidity", "??")
        vento    = atual.get("windspeedKmph", "??")
        regiao = dados.get("nearest_area", [{}])[0].get("areaName", [{}])[0].get("value", alvo)

        return (
            f"Senhor, acessando a Nuvem Oracle. "
            f"Em {regiao} temos {desc.lower()}, {temp}°C, "
            f"sensação de {sensacao}°C. "
            f"Humidade em {umidade}% e ventos a {vento} km/h."
        )
    except Exception:
        return "Senhor, dados da Nuvem Oracle inconsistentes."







def verificar_chuva_amanha(cidade_alvo: str = "") -> str:
    alvo = (cidade_alvo or get_cidade_painel()).strip()
    dados = requisitar_telemetria(alvo)
    if not dados or "weather" not in dados or len(dados["weather"]) < 2:
        return "Senhor, projeções Oracle indisponíveis."

    try:
        amanha  = dados["weather"][1]
        horario = amanha["hourly"][4]
        desc    = extrair_descricao(horario)
        chuva   = horario.get("precipMM", "0")
        temp_max = amanha.get("maxtempC", "??")
        temp_min = amanha.get("mintempC", "??")

        return (
            f"Senhor, projeção Oracle para amanhã em {alvo.title()}: "
            f"{desc.lower()} com {chuva}mm de precipitação. "
            f"Temperatura entre {temp_min}°C e {temp_max}°C."
        )
    except Exception:
        return "Senhor, erro nas projeções Oracle."







def limpar_cache_clima() -> None:
    cache.clear()







def obter_clima_raw(cidade_alvo: str) -> str:
    alvo = cidade_alvo if cidade_alvo else get_cidade_painel()
    dados = requisitar_telemetria(alvo)
    return json.dumps(dados if dados else {"error": f"Conexão Oracle falhou para '{alvo}'"})