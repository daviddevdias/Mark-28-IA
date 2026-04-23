import requests
from datetime import datetime, timedelta
from typing import Optional


TIMEOUT = 8
BASE_URL = "https://wttr.in/{cidade}?format=j1"
HEADERS = {"Accept-Language": "pt-br", "User-Agent": "CORE-Assistant/1.0"}
cache: dict = {}
CACHE_TTL = timedelta(minutes=10)


def requisitar_telemetria(cidade: str = "") -> Optional[dict]:
    now = datetime.now()
    if cidade in cache:
        dados, ts = cache[cidade]
        if now - ts < CACHE_TTL:
            return dados

    try:
        res = requests.get(
            BASE_URL.format(cidade=cidade), headers=HEADERS, timeout=TIMEOUT
        )
        res.raise_for_status()
        dados = res.json()
        cache[cidade] = (dados, now)
        return dados
    except requests.exceptions.Timeout:
        print(f"[WEATHER] Timeout ao buscar dados de {cidade}.")
        return cache.get(cidade, (None, None))[0]
    except Exception as e:
        print(f"[WEATHER] Erro: {e}")
        return None


def extrair_descricao(bloco: dict) -> str:
    return bloco.get("lang_pt", [{}])[0].get("value", "Estável")


def obter_previsao_hoje(cidade_alvo: str = "") -> str:
    alvo = (cidade_alvo or "").strip()
    dados = requisitar_telemetria(alvo)

    if not dados:
        return "ERRO: Verifique a conexão com o satélite."

    try:
        atual = dados["current_condition"][0]
        hoje = dados["weather"][0]
        temp = atual.get("temp_C", "??")
        sensacao = atual.get("FeelsLikeC", "??")
        desc = extrair_descricao(atual)
        umidade = atual.get("humidity", "??")
        vento_kmh = atual.get("windspeedKmph", "??")
        max_t = hoje.get("maxtempC", "??")
        min_t = hoje.get("mintempC", "??")

        return (
            f"ALVO: {alvo.upper()} | STATUS: {desc.upper()}\n"
            f"TEMP: {temp}°C (SENTE {sensacao}°C) | EXTREMOS: {min_t}°C–{max_t}°C\n"
            f"UMIDADE: {umidade}% | VENTO: {vento_kmh} km/h"
        )
    except (KeyError, IndexError) as e:
        return f"ERRO: Dados climáticos incompletos. ({e})"


def verificar_chuva_amanha(cidade_alvo: str = "") -> str:
    alvo = (cidade_alvo or "").strip()
    dados = requisitar_telemetria(alvo)

    if not dados or "weather" not in dados or len(dados["weather"]) < 2:
        return "SISTEMA: Dados de previsão futura indisponíveis."

    try:
        amanha = dados["weather"][1]
        max_t = amanha.get("maxtempC", "??")
        min_t = amanha.get("mintempC", "??")
        desc = extrair_descricao(amanha["hourly"][4])
        chuva_mm = amanha.get("hourly", [{}])[4].get("precipMM", "0")

        return (
            f"PREVISÃO AMANHÃ ({alvo}): {desc} | "
            f"Oscilação {min_t}°C–{max_t}°C | Precipitação: {chuva_mm} mm"
        )
    except (KeyError, IndexError) as e:
        return f"ERRO: Previsão futura indisponível. ({e})"


def limpar_cache_clima() -> None:
    cache.clear()
    print("[WEATHER] Cache limpo.")
