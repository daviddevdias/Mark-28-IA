import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
API_DIR = BASE_DIR / "api"
ASSETS_DIR = BASE_DIR / "assets"

API_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


CONFIG_FILES = {
    "smart": API_DIR / "config_smart.json",
    "api_keys": API_DIR / "api_keys.json",
    "core": API_DIR / "config_core.json",
    "notas": API_DIR / "notas.json",
}

CONFIG_SMART_PATH = API_DIR / "config_smart.json"

F_MAIN = "Orbitron"
F_DATA = "Consolas"


def _carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERRO] Falha ao ler {caminho.name}: {e}")
        return {}


def load_memory() -> dict:
    memoria = {}
    for caminho in CONFIG_FILES.values():
        memoria.update(_carregar_json(caminho))
    return memoria


def update_memory(nome_arquivo: str, dados: dict) -> bool:
    caminho = API_DIR / nome_arquivo
    dados_existentes = _carregar_json(caminho)
    if isinstance(dados_existentes, dict) and isinstance(dados, dict):
        dados_existentes.update(dados)
    else:
        dados_existentes = dados
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados_existentes, f, indent=4, ensure_ascii=False)
        print(f"> [MEMÓRIA] {nome_arquivo} salvo em {caminho}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao salvar {nome_arquivo}: {e}")
        return False


_dados = load_memory()


QWEN_API_KEY = _dados.get("qwen", "")
GEMINI_API_KEY = _dados.get("gemini", "")
CURRENT_MODEL = _dados.get("current_model", "qwen/qwen-vl-max")

BASE_URL = "https://openrouter.ai/api/v1"

SPOTIFY_ID = _dados.get("spotify_id", "")
SPOTIFY_SECRET = _dados.get("spotify_sec", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

SMARTTHINGS_TOKEN = _dados.get("smartthings", "")

TELEGRAM_TOKEN = _dados.get("telegram_token", "")

NOME_MESTRE = _dados.get("nome_mestre", "Usuário")
voz_atual = _dados.get("voz", "pt-BR-AntonioNeural")
DEVICE_INDEX = _dados.get("device_index", 0)
modo_silencioso = _dados.get("modo_silencioso", False)
tema_ativo = _dados.get("tema_ativo", "default")
notas = _dados.get("notas", "// ÁREA DE NOTAS TÁTICAS\n")
cidade_padrao = _dados.get("cidade_padrao", "")

