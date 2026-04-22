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
    """Salva dados no arquivo JSON. Retorna True em sucesso, False em falha."""
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
        return True  # FIX: estava retornando None, gerenciador_memoria checava o retorno
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

NOME_MESTRE = _dados.get("nome_mestre", "Usuário")
voz_atual = _dados.get("voz", "pt-BR-AntonioNeural")
DEVICE_INDEX = _dados.get("device_index", 0)
modo_silencioso = _dados.get("modo_silencioso", False)
tema_ativo = _dados.get("tema_ativo", "default")
notas = _dados.get("notas", "// ÁREA DE NOTAS TÁTICAS\n")


COMANDOS_JARVIS = {
    # ── SISTEMA ──────────────────────────────────────────────────────────────
    "jarvis, encerrar": {
        "desc": "Desliga todos os sistemas e encerra o C.O.R.E.",
        "cat": "SISTEMA",
        "poder": "⚡⚡⚡",
        "handler": "encerrar",
        "passos": [
            'Dizer: "jarvis, encerrar"',
            "Sistema salva estado atual",
            "Todos os módulos são finalizados com segurança",
            "Interface é encerrada",
        ],
    },
    "jarvis, silenciar": {
        "desc": "Interrompe a fala imediatamente e entra em modo silencioso.",
        "cat": "SISTEMA",
        "poder": "⚡⚡",
        "handler": "silencio",
        "passos": [
            'Dizer: "jarvis, silenciar" ou "para" / "chega"',
            "Motor TTS é interrompido instantaneamente",
            "Fila de falas é limpa",
            "Sistema aguarda próximo comando",
        ],
    },
    "jarvis, reativar": {
        "desc": "Sai do modo silencioso e reativa todos os módulos.",
        "cat": "SISTEMA",
        "poder": "⚡",
        "handler": "reativar",
        "passos": [
            'Dizer: "jarvis, reativar"',
            "Sistema detecta o wake-word",
            "Módulos são recarregados",
            "Interface retorna ao estado anterior",
        ],
    },
    "jarvis, bloquear": {
        "desc": "Bloqueia a estação de trabalho instantaneamente (Win + L).",
        "cat": "SISTEMA",
        "poder": "⚡⚡",
        "handler": "bloquear",
        "passos": [
            'Dizer: "jarvis, bloquear"',
            "Executa Win + L automaticamente",
            "Sessão é bloqueada imediatamente",
            "Requer senha para retorno",
        ],
    },
    # ── INTERFACE ─────────────────────────────────────────────────────────────
    "jarvis, abrir painel": {
        "desc": "Abre o painel de diagnóstico C.O.R.E.",
        "cat": "INTERFACE",
        "poder": "⚡",
        "handler": "abrir painel",
        "passos": [
            'Dizer: "jarvis, abrir painel"',
            "Módulo GUI é inicializado",
            "Painel de diagnóstico é exibido",
            "Telemetria começa a atualizar",
        ],
    },
    "jarvis, minimizar tudo": {
        "desc": "Recolhe todas as janelas abertas (Win + D).",
        "cat": "INTERFACE",
        "poder": "⚡",
        "handler": "minimizar tudo",
        "passos": [
            'Dizer: "jarvis, minimizar tudo"',
            "Executa Win + D",
            "Todas as janelas são minimizadas",
            "Desktop fica exposto",
        ],
    },
    "jarvis, fechar janela": {
        "desc": "Fecha a janela ativa (Alt + F4).",
        "cat": "INTERFACE",
        "poder": "⚡",
        "handler": "fechar janela",
        "passos": [
            'Dizer: "jarvis, fechar janela"',
            "Executa Alt + F4 na janela em foco",
            "Se houver diálogo de confirmação, aguarda input",
            "Janela é encerrada",
        ],
    },
    "jarvis, captura de tela": {
        "desc": "Aciona a ferramenta de captura de tela (Win + Shift + S).",
        "cat": "INTERFACE",
        "poder": "⚡",
        "handler": "captura",
        "passos": [
            'Dizer: "jarvis, captura" ou "print"',
            "Executa Win + Shift + S",
            "Ferramenta de recorte é aberta",
            "Selecione a área desejada",
        ],
    },
    "jarvis, limpar lixeira": {
        "desc": "Executa limpeza profunda do lixo do sistema.",
        "cat": "INTERFACE",
        "poder": "⚡⚡",
        "handler": "limpar lixeira",
        "passos": [
            'Dizer: "jarvis, limpar lixeira"',
            "PowerShell executa Clear-RecycleBin",
            "Lixeira esvaziada sem confirmação",
            "Espaço em disco é recuperado",
        ],
    },
    # ── TERMINAL ──────────────────────────────────────────────────────────────
    "jarvis, terminal [tarefa]": {
        "desc": "Ollama converte a ordem em comando CMD/PowerShell e executa.",
        "cat": "TERMINAL",
        "poder": "⚡⚡⚡",
        "handler": "terminal",
        "passos": [
            'Dizer: "jarvis, terminal [sua tarefa em português]"',
            "IA interpreta a tarefa e gera o comando",
            "Comando é exibido no console",
            "Executado automaticamente e resultado lido em voz",
        ],
    },
    "jarvis, modo trabalho": {
        "desc": "Protocolo Dev: abre VS Code e Chrome simultaneamente.",
        "cat": "TERMINAL",
        "poder": "⚡⚡",
        "handler": "modo trabalho",
        "passos": [
            'Dizer: "jarvis, modo trabalho"',
            "VS Code é aberto",
            "Chrome é aberto",
            "Ambiente de dev pronto",
        ],
    },
    # ── WEB ───────────────────────────────────────────────────────────────────
    "jarvis, pesquisar [termo]": {
        "desc": "Busca no Google e lê o resumo em voz.",
        "cat": "WEB",
        "poder": "⚡⚡",
        "handler": "pesquisar",
        "passos": [
            'Dizer: "jarvis, pesquisar [seu termo]"',
            "Google é consultado via navegador",
            "IA sintetiza os principais resultados",
            "Resposta é lida em voz alta",
        ],
    },
    "jarvis, o que é [termo]": {
        "desc": "Consulta rápida sobre definições ou pessoas.",
        "cat": "WEB",
        "poder": "⚡",
        "handler": "pesquisar",
        "passos": [
            'Dizer: "jarvis, o que é [termo]" ou "quem é [nome]"',
            "Busca contextual é realizada",
            "Resultado resumido pela IA",
            "Resposta objetiva é fornecida",
        ],
    },
    "jarvis, fechar aba": {
        "desc": "Fecha a aba atual do navegador (Ctrl + W).",
        "cat": "WEB",
        "poder": "⚡",
        "handler": "fechar aba",
        "passos": [
            'Dizer: "jarvis, fechar aba"',
            "Executa Ctrl + W no navegador ativo",
            "Aba atual é fechada",
            "Foco vai para a aba anterior",
        ],
    },
    # ── MÍDIA ─────────────────────────────────────────────────────────────────
    "jarvis, tocar [música/artista]": {
        "desc": "Busca e reproduz áudio no Spotify.",
        "cat": "MÍDIA",
        "poder": "⚡⚡",
        "handler": "tocar",
        "passos": [
            'Dizer: "jarvis, tocar [nome da música ou artista]"',
            "Spotify API recebe a requisição",
            "Música mais relevante é selecionada",
            "Reprodução inicia automaticamente",
        ],
    },
    "jarvis, playlist [nome]": {
        "desc": "Inicia uma playlist específica no Spotify.",
        "cat": "MÍDIA",
        "poder": "⚡⚡",
        "handler": "playlist",
        "passos": [
            'Dizer: "jarvis, playlist [nome]"',
            "Playlists são consultadas via API",
            "Playlist correspondente é encontrada",
            "Reprodução começa do início",
        ],
    },
    "jarvis, minhas favoritas": {
        "desc": "Toca suas músicas curtidas no Spotify em modo aleatório.",
        "cat": "MÍDIA",
        "poder": "⚡",
        "handler": "favoritas",
        "passos": [
            'Dizer: "jarvis, minhas favoritas"',
            "Acessa biblioteca de músicas curtidas",
            "Reprodução em modo aleatório ativada",
            "Favoritas começam a tocar",
        ],
    },
    "jarvis, no youtube [termo]": {
        "desc": "Abre e dá play automático no YouTube.",
        "cat": "MÍDIA",
        "poder": "⚡⚡",
        "handler": "youtube",
        "passos": [
            'Dizer: "jarvis, no youtube [busca]"',
            "YouTube é aberto no navegador",
            "Busca é inserida automaticamente",
            "Primeiro resultado é reproduzido",
        ],
    },
    "jarvis, pausar / continuar": {
        "desc": "Controla a reprodução de mídia (pausa ou retoma).",
        "cat": "MÍDIA",
        "poder": "⚡",
        "handler": "pausar",
        "passos": [
            'Dizer: "jarvis, pausar" ou "jarvis, continuar"',
            "Tecla de mídia é simulada",
            "Player ativo responde ao comando",
            "Funciona com Spotify, YouTube e outros",
        ],
    },
    "jarvis, próxima / anterior": {
        "desc": "Pula ou volta faixas de áudio.",
        "cat": "MÍDIA",
        "poder": "⚡",
        "handler": "proxima",
        "passos": [
            'Dizer: "jarvis, próxima" ou "jarvis, anterior"',
            "Tecla de mídia correspondente é acionada",
            "Track muda imediatamente",
            "Novo título é anunciado em voz",
        ],
    },
    # ── SMART HOME ────────────────────────────────────────────────────────────
    "jarvis, ligar tv": {
        "desc": "Liga a TV Samsung via SmartThings.",
        "cat": "SMART HOME",
        "poder": "⚡⚡",
        "handler": "ligar tv",
        "passos": [
            'Dizer: "jarvis, ligar tv"',
            "SmartThings API recebe comando Power ON",
            "TV Samsung é ligada via rede local",
            "Confirmação de status recebida",
        ],
    },
    "jarvis, desligar tv": {
        "desc": "Desliga a TV Samsung via SmartThings.",
        "cat": "SMART HOME",
        "poder": "⚡⚡",
        "handler": "desligar tv",
        "passos": [
            'Dizer: "jarvis, desligar tv"',
            "SmartThings API recebe comando Power OFF",
            "TV é desligada remotamente",
            "Status confirmado via API",
        ],
    },
    "jarvis, tv volume [número]": {
        "desc": "Ajusta o volume da TV. Ex: 'tv volume 30'.",
        "cat": "SMART HOME",
        "poder": "⚡",
        "handler": "tv volume",
        "passos": [
            'Dizer: "jarvis, tv volume 30"',
            "Valor numérico é extraído da fala",
            "SmartThings API ajusta o volume",
            "TV confirma novo nível de áudio",
        ],
    },
    # ── CLIMA ─────────────────────────────────────────────────────────────────
    "jarvis, clima": {
        "desc": "Consulta temperatura, umidade e condição atual.",
        "cat": "CLIMA",
        "poder": "⚡",
        "handler": "clima",
        "passos": [
            'Dizer: "jarvis, clima"',
            "API climática é consultada",
            "Temperatura, umidade e condição coletados",
            "Resumo é lido em voz alta",
        ],
    },
    "jarvis, chuva amanhã": {
        "desc": "Verifica previsão de chuva para as próximas 24h.",
        "cat": "CLIMA",
        "poder": "⚡",
        "handler": "chuva",
        "passos": [
            'Dizer: "jarvis, chuva amanhã"',
            "Previsão de 24h é consultada",
            "Probabilidade de precipitação calculada",
            "Resposta objetiva: vai ou não chover",
        ],
    },
    # ── UTILIDADES ────────────────────────────────────────────────────────────
    "jarvis, alarme [hora]": {
        "desc": "Agenda um lembrete ou despertador. Ex: 'alarme 07:30'.",
        "cat": "UTILIDADES",
        "poder": "⚡",
        "handler": "alarme",
        "passos": [
            'Dizer: "jarvis, alarme 07:30"',
            "Horário é extraído da fala",
            "Timer interno configurado",
            "Alarme dispara com voz no horário",
        ],
    },
    "jarvis, abrir [app]": {
        "desc": "Abre qualquer aplicativo instalado no sistema.",
        "cat": "UTILIDADES",
        "poder": "⚡",
        "handler": "abrir",
        "passos": [
            'Dizer: "jarvis, abrir [nome do app]"',
            "Nome é normalizado e localizado",
            "Aplicativo é lançado",
            "Confirmação em voz",
        ],
    },
    "jarvis, minha memória": {
        "desc": "Lê o que o C.O.R.E tem salvo sobre você na memória.",
        "cat": "UTILIDADES",
        "poder": "⚡",
        "handler": "minha memoria",
        "passos": [
            'Dizer: "jarvis, minha memória"',
            "Arquivo long_term.json é lido",
            "Resumo das informações salvas",
            "Lido em voz alta",
        ],
    },
    "jarvis, o que você faz": {
        "desc": "Lista as capacidades do C.O.R.E em voz.",
        "cat": "UTILIDADES",
        "poder": "⚡",
        "handler": "ajuda",
        "passos": [
            'Dizer: "jarvis, o que você faz" ou "ajuda"',
            "Sistema lista categorias disponíveis",
            "Resposta em voz",
        ],
    },
    "para / chega / silêncio": {
        "desc": "Interrompe a fala do C.O.R.E imediatamente.",
        "cat": "UTILIDADES",
        "poder": "⚡⚡",
        "handler": "silencio",
        "passos": [
            'Dizer: "para", "chega" ou "silêncio"',
            "Motor TTS interrompido instantaneamente",
            "Fila de falas é limpa",
            "Sistema aguarda próximo comando",
        ],
    },
    # ── MONITOR DE TELA ───────────────────────────────────────────────────────
    "jarvis, monitorar tela": {
        "desc": "Ativa monitoramento contínuo: detecta erros e sugere soluções.",
        "cat": "MONITOR",
        "poder": "⚡⚡",
        "handler": "monitorar tela",
        "passos": [
            'Dizer: "jarvis, monitorar tela"',
            "C.O.R.E captura frames a cada 5 segundos",
            "IA identifica erros, warnings e sugere correções",
            'Dizer "jarvis, desligar monitor" para parar',
        ],
    },
    "jarvis, desativar monitor": {
        "desc": "Desativa o monitoramento contínuo de tela.",
        "cat": "MONITOR",
        "poder": "⚡⚡⚡",
        "handler": "desligar monitor",
        "passos": [
            'Dizer: "jarvis, desligar monitor"',
            "Loop de captura é encerrado",
            "Estatísticas de uso são lidas em voz",
            "Chamadas de API economizadas são informadas",
        ],
    },
    "jarvis, monitor status": {
        "desc": "Informa quantas capturas e análises o monitor já fez.",
        "cat": "MONITOR",
        "poder": "⚡⚡⚡",
        "handler": "monitor status",
        "passos": [
            'Dizer: "jarvis, monitor status"',
            "Total de capturas e chamadas API lidas",
            "Última análise reproduzida em voz",
        ],
    },
    "jarvis, olha a tela": {
        "desc": "Análise pontual: C.O.R.E descreve o que está na tela agora.",
        "cat": "MONITOR",
        "poder": "⚡⚡",
        "handler": "olha a tela",
        "passos": [
            'Dizer: "jarvis, olha a tela" ou "analisa a tela"',
            "Frame é capturado imediatamente",
            "IA descreve o conteúdo em até 25 palavras",
            "Resposta lida em voz",
        ],
    },
}