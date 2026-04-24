import json
from pathlib import Path


BASE_DIR   = Path(__file__).resolve().parent
API_DIR    = BASE_DIR / "api"
ASSETS_DIR = BASE_DIR / "assets"
API_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)
F_MAIN = "Orbitron"
F_DATA = "Consolas"
COMANDOS_JARVIS = {}







def ler_json(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[CONFIG] Erro ao ler {caminho.name}: {e}")
        return {}







def salvar_json(nome_arquivo: str, dados: dict) -> bool:
    caminho = API_DIR / nome_arquivo
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
    arquivos = ["config_smart.json", "api_keys.json", "config_core.json", "notas.json"]
    dados = {}
    for nome in arquivos:
        dados.update(ler_json(API_DIR / nome))
    return dados







cfg = carregar_tudo()
QWEN_API_KEY       = cfg.get("qwen", "")
GEMINI_API_KEY     = cfg.get("gemini", "")
CURRENT_MODEL      = cfg.get("current_model", "qwen/qwen-vl-max")
BASE_URL           = "https://openrouter.ai/api/v1"
SPOTIFY_ID         = cfg.get("spotify_id", "")
SPOTIFY_SECRET     = cfg.get("spotify_sec", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SMARTTHINGS_TOKEN  = cfg.get("smartthings", "")
TELEGRAM_TOKEN     = cfg.get("telegram_token", "")
NOME_MESTRE        = cfg.get("nome_mestre", "Usuário")
voz_atual          = cfg.get("voz", "pt-BR-AntonioNeural")
DEVICE_INDEX       = cfg.get("device_index", 0)
modo_silencioso    = cfg.get("modo_silencioso", False)
tema_ativo         = cfg.get("tema_ativo", "default")
notas              = cfg.get("notas", "// ÁREA DE NOTAS TÁTICAS\n")
cidade_padrao      = cfg.get("cidade_padrao", "")