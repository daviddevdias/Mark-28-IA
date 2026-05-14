"""
config.py — Configurações globais do Jarvis
Carrega tudo dos arquivos JSON na pasta /api e expõe como variáveis globais.
"""

import json
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
API_DIR    = BASE_DIR / "api"
ASSETS_DIR = BASE_DIR / "assets"
API_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


# ── Helpers de leitura/escrita JSON ──────────────────────────────────────────

def ler_json(caminho: Path) -> dict:
    """Lê um arquivo JSON. Retorna {} se não existir ou falhar."""
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CONFIG] Erro ao ler {caminho.name}: {e}")
        return {}


def salvar_json(nome_arquivo: str, dados: dict) -> bool:
    """Faz merge dos dados com o arquivo existente e salva."""
    caminho   = API_DIR / nome_arquivo
    existente = ler_json(caminho)
    if isinstance(existente, dict):
        existente.update(dados)
    else:
        existente = dados
    try:
        caminho.write_text(
            json.dumps(existente, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"[CONFIG] {nome_arquivo} salvo.")
        return True
    except Exception as e:
        print(f"[CONFIG] Erro ao salvar {nome_arquivo}: {e}")
        return False


def carregar_tudo() -> dict:
    """Carrega e mescla todos os arquivos de configuração."""
    arquivos = ["config_smart.json", "api_keys.json", "config_core.json", "notas.json"]
    dados = {}
    for nome in arquivos:
        dados.update(ler_json(API_DIR / nome))
    return dados


# ── Atualização de valores vindos do painel (UI) ──────────────────────────────

def definir_valor_ui(chave: str, valor: str) -> None:
    """Atualiza uma variável global a partir do painel de configuração."""
    # Mapa: nome do campo no painel → nome da variável global
    nomes = {
        "gemini":            "GEMINI_API_KEY",
        "qwen":              "QWEN_API_KEY",
        "spotify_id":        "SPOTIFY_ID",
        "spotify_sec":       "SPOTIFY_SECRET",
        "smartthings":       "SMARTTHINGS_TOKEN",
        "smartthings_tv_id": "SMARTTHINGS_TV_DEVICE_ID",
        "nome_mestre":       "NOME_MESTRE",
        "voz":               "voz_atual",
        "device_index":      "DEVICE_INDEX",
    }
    alvo = nomes.get(chave, chave)

    if alvo == "DEVICE_INDEX":
        try:
            globals()["DEVICE_INDEX"] = int(valor)
        except ValueError:
            globals()["DEVICE_INDEX"] = 0
        return

    globals()[alvo if alvo in globals() else chave] = valor

    # Se mudou nome do mestre, persiste na memória
    if chave == "nome_mestre":
        try:
            from storage.memory_manager import update_memory
            update_memory({"identity": {"mestre": {"value": str(valor).strip()[:256]}}})
        except Exception:
            pass

    # Se mudou cidade padrão, persiste na memória
    if chave == "cidade_padrao":
        try:
            from storage.memory_manager import update_memory
            update_memory({"preferences": {"cidade": {"value": str(valor).strip()[:256]}}})
        except Exception:
            pass


# ── Callback de voz para o painel ─────────────────────────────────────────────

voz_ui_cb = None  # Função registrada pelo painel para receber eventos de voz

def registrar_callback_voz_painel(cb):
    """O painel chama isso para saber quando a voz liga/desliga."""
    global voz_ui_cb
    voz_ui_cb = cb

def notificar_voz_painel(on: bool, vol: float = 1.0) -> None:
    """Avisa o painel que a voz mudou de estado."""
    if voz_ui_cb:
        try:
            voz_ui_cb(bool(on), float(vol))
        except Exception:
            pass


# ── Recarga de identidade em runtime ─────────────────────────────────────────

def recarregar_identidade_painel() -> None:
    """Relê nome do mestre e cidade do arquivo de configuração (chamado no loop principal)."""
    dados = ler_json(API_DIR / "config_core.json")
    nm = dados.get("nome_mestre")
    if nm and str(nm).strip():
        globals()["NOME_MESTRE"] = str(nm).strip()[:256]
    cp = dados.get("cidade_padrao")
    if cp is not None:
        globals()["cidade_padrao"] = str(cp).strip()[:256]


# ── Carrega tudo e expõe como variáveis ──────────────────────────────────────

cfg = carregar_tudo()

# APIs
QWEN_API_KEY   = cfg.get("qwen", "")
GEMINI_API_KEY = cfg.get("gemini", "")
CURRENT_MODEL  = cfg.get("current_model", "qwen/qwen-vl-max")
BASE_URL       = "https://openrouter.ai/api/v1"

# Spotify
SPOTIFY_ID           = cfg.get("spotify_id", "")
SPOTIFY_SECRET       = cfg.get("spotify_sec", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

# SmartThings (TV)
SMARTTHINGS_TOKEN      = cfg.get("smartthings", "")
SMARTTHINGS_TV_DEVICE_ID = str(cfg.get("smartthings_tv_id", "")).strip()

# Telegram
TELEGRAM_TOKEN      = cfg.get("telegram_token", "")
TELEGRAM_AUTH_TOKEN = cfg.get("telegram_auth_token", "")
TELEGRAM_ALLOWED_IDS = cfg.get("telegram_allowed_ids", [])

# Clima
OPENWEATHER_API_KEY = cfg.get("openweather_api_key", "")

# Preferências gerais
NOME_MESTRE   = cfg.get("nome_mestre", "Chefe")
voz_atual     = cfg.get("voz", "pt-BR-AntonioNeural")
DEVICE_INDEX  = cfg.get("device_index", 1)
tema_ativo    = cfg.get("tema_ativo", "MIDNIGHT_MINIMAL")
notas         = cfg.get("notas", "")
cidade_padrao = cfg.get("cidade_padrao", "")

# Caminho do arquivo de clone de voz
voz_referencia = str(ASSETS_DIR / "voz_clone.wav")