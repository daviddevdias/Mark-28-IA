import time
import threading
import json
import os
import random
from datetime import datetime

try:
    import pygame
    _PYGAME = True
except ImportError:
    _PYGAME = False


DB_ALARMES = "logs/alarmes.json"
lock = threading.Lock()
alarme_ativo = False

falar_callback = None
ultimo_disparo = {}

_canal_alarme = None
_sound_alarme = None


def registrar_falar_alarme(fn):
    global falar_callback
    falar_callback = fn


# ──────────────────────────────────────────────
# Persistência
# ──────────────────────────────────────────────

def carregar_alarmes() -> list:
    if not os.path.exists(DB_ALARMES):
        return []
    with lock:
        try:
            with open(DB_ALARMES, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


def salvar_alarmes(alarmes: list) -> None:
    os.makedirs(os.path.dirname(DB_ALARMES), exist_ok=True)
    with lock:
        with open(DB_ALARMES, "w", encoding="utf-8") as f:
            json.dump(alarmes, f, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────

def adicionar_alarme(hora: str, missao: str, repetir: bool = False, musica: str = "") -> str:
    if not hora or ":" not in hora:
        return "Senhor, o formato de tempo parece inconsistente. Poderia repetir?"
    alarmes = carregar_alarmes()
    alarme = {
        "hora": hora,
        "missao": missao,
        "status": "pendente",
        "repetir": repetir,
        "musica": musica,
        "criado_em": datetime.now().isoformat(),
        "ultimo_disparo": None,
    }
    alarmes.append(alarme)
    salvar_alarmes(alarmes)
    confirmacoes = [
        f"Protocolo de agendamento concluído. Alarme definido para às {hora}, Senhor.",
        f"Entendido. Cronômetro sincronizado para às {hora}. Estarei atento.",
        f"Sistema atualizado. Alerta de proximidade agendado para às {hora}."
    ]
    return random.choice(confirmacoes)


def remover_alarme(hora: str, missao: str) -> str:
    alarmes = carregar_alarmes()
    novos = [a for a in alarmes if not (a["hora"] == hora and a["missao"] == missao)]
    if len(novos) == len(alarmes):
        return "Senhor, não encontrei nenhum registro correspondente nos meus arquivos."
    salvar_alarmes(novos)
    return f"Diretriz cancelada. O alarme das {hora} foi removido do sistema."


def listar_alarmes() -> list:
    return [a for a in carregar_alarmes() if a["status"] == "pendente"]


# ──────────────────────────────────────────────
# Música via Channel dedicado
# ──────────────────────────────────────────────

def _caminho_musica() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "assets", "despertar.mp3"),
        os.path.join(os.getcwd(), "assets", "despertar.mp3"),
        os.path.join(base, "despertar.mp3"),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return ""


def tocar_musica_canal():
    """
    Toca despertar.mp3 em Channel(1) em loop.
    Channel(1) é separado do pygame.mixer.music usado pelo TTS — sem conflito.
    """
    global _canal_alarme, _sound_alarme, alarme_ativo

    caminho = _caminho_musica()
    if not caminho:
        print("[ALARME] despertar.mp3 nao encontrado!")
        return

    if not _PYGAME:
        print("[ALARME] pygame nao instalado!")
        return

    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), 4))

        _sound_alarme = pygame.mixer.Sound(caminho)
        _sound_alarme.set_volume(1.0)
        _canal_alarme = pygame.mixer.Channel(1)
        _canal_alarme.play(_sound_alarme, loops=-1)
        print(f"[ALARME] Tocando: {caminho}")

        while alarme_ativo and _canal_alarme.get_busy():
            time.sleep(0.3)

        _canal_alarme.stop()

    except Exception as e:
        print(f"[ALARME] Erro ao tocar musica: {e}")
    finally:
        _canal_alarme = None
        _sound_alarme = None


# ──────────────────────────────────────────────
# Disparar alarme
# ──────────────────────────────────────────────

def disparar_alarme(alarme: dict):
    global alarme_ativo
    alarme_ativo = True

    # Toca a música direto — sem beep, sem esperar TTS
    tocar_musica_canal()


# ──────────────────────────────────────────────
# Parar alarme
# ──────────────────────────────────────────────

def parar_alarme_total():
    global alarme_ativo, _canal_alarme
    alarme_ativo = False

    try:
        if _canal_alarme is not None:
            _canal_alarme.stop()
    except Exception:
        pass

    encerrar = [
        "Protocolo de despertar encerrado. Tenha um dia produtivo, Senhor.",
        "Sistemas de audio silenciados. Estou em prontidao para sua proxima ordem.",
        "Entendido, Senhor. Desejo-lhe um excelente dia de trabalho."
    ]
    return random.choice(encerrar)


# ──────────────────────────────────────────────
# Loop de verificação
# ──────────────────────────────────────────────

def verificar_agenda_loop():
    while True:
        agora = datetime.now().strftime("%H:%M")
        alarmes = carregar_alarmes()
        for alarme in alarmes:
            if alarme["status"] != "pendente":
                continue
            chave = f"{alarme['hora']}-{alarme['missao']}"
            if ultimo_disparo.get(chave) == agora:
                continue
            if alarme["hora"] == agora:
                ultimo_disparo[chave] = agora
                threading.Thread(target=disparar_alarme, args=(alarme,), daemon=True).start()
                if not alarme.get("repetir"):
                    alarme["status"] = "concluido"
                salvar_alarmes(alarmes)
        time.sleep(1)


def iniciar_sistema_alarmes():
    threading.Thread(target=verificar_agenda_loop, daemon=True).start()
    print("[JARVIS] Protocolos de agendamento online.")