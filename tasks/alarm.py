import json
import os
import random
import re
import threading
import time
import unicodedata
from datetime import date, datetime

try:
    import pygame

    PYGAME = True
except ImportError:
    PYGAME = False

DB_ALARMES = "logs/alarmes.json"
lock = threading.Lock()
alarme_ativo = False
falar_callback = None
ultimo_disparo: dict[str, str] = {}
canal_alarme = None
sound_alarme = None
_alarm_loop = None

MESES = {
    "janeiro": 1,
    "jan": 1,
    "fevereiro": 2,
    "fev": 2,
    "marco": 3,
    "março": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "maio": 5,
    "mai": 5,
    "junho": 6,
    "jun": 6,
    "julho": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "setembro": 9,
    "set": 9,
    "outubro": 10,
    "out": 10,
    "novembro": 11,
    "nov": 11,
    "dezembro": 12,
    "dez": 12,
}


def registrar_falar_alarme(fn):
    global falar_callback
    falar_callback = fn


def registrar_loop_alarme(loop):
    global _alarm_loop
    _alarm_loop = loop


def _sem_acentos(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse_alarme_voz(cmd: str) -> tuple[str | None, str | None, str]:
    raw = cmd.strip()
    low = _sem_acentos(raw)
    data_iso: str | None = None
    hora: str | None = None
    m_iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", raw)
    if m_iso:
        try:
            data_iso = date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))).isoformat()
        except ValueError:
            data_iso = None
    if not data_iso:
        m_do = re.search(r"\b(?:dia)?\s*(\d{1,2})\s+do\s+(\d{1,2})(?:\s+de\s+(\d{4}))?\b", low)
        if m_do:
            d0, mth0 = int(m_do.group(1)), int(m_do.group(2))
            yi0 = int(m_do.group(3)) if m_do.group(3) else datetime.now().year
            try:
                data_iso = date(yi0, mth0, d0).isoformat()
            except ValueError:
                data_iso = None
    if not data_iso:
        m_sl = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", raw)
        if m_sl:
            a, b, y = int(m_sl.group(1)), int(m_sl.group(2)), m_sl.group(3)
            if a > 12:
                mth, d = a, b
            elif b > 12:
                d, mth = a, b
            else:
                d, mth = a, b
            yi = int(y) if y else datetime.now().year
            if y and yi < 100:
                yi += 2000
            try:
                data_iso = date(yi, mth, d).isoformat()
            except ValueError:
                data_iso = None
    if not data_iso:
        m_pt = re.search(
            r"(?:^|\s)(?:dia)?\s*(\d{1,2})\s+de\s+([a-z]+)(?:\s+de\s+(\d{2,4}))?",
            low,
        )
        if m_pt:
            d = int(m_pt.group(1))
            mn = m_pt.group(2)
            yraw = m_pt.group(3)
            mi = MESES.get(mn)
            if mi:
                yi = int(yraw) if yraw else datetime.now().year
                if yraw and yi < 100:
                    yi += 2000
                try:
                    data_iso = date(yi, mi, d).isoformat()
                except ValueError:
                    data_iso = None
    m_hm = re.search(r"(\d{1,2})\s*[:h]\s*(\d{2})\b", low)
    if m_hm:
        hora = f"{int(m_hm.group(1)):02d}:{int(m_hm.group(2)):02d}"
    else:
        m_h = re.search(r"\bas\s+(\d{1,2})\s*h?\b", low)
        if m_h:
            hora = f"{int(m_h.group(1)):02d}:00"
        else:
            m_d = re.search(r"\b(\d{1,2})\s*h\b", low)
            if m_d:
                hora = f"{int(m_d.group(1)):02d}:00"
    missao = re.sub(
        r"\s+",
        " ",
        re.sub(
            r"(?i)\b(jarvis|alarme|despertar|agendar|criar|lembrete|dia|as|h|horas|de|maio|janeiro|fevereiro|marco|abril|junho|julho|agosto|setembro|outubro|novembro|dezembro|\d{1,2}[:h]\d{2}|\d{4}-\d{2}-\d{2})\b",
            " ",
            raw,
        ),
    ).strip()[:120]
    if not missao:
        missao = "Alarme"
    return data_iso, hora, missao


def carregar_alarmes() -> list:
    if not os.path.exists(DB_ALARMES):
        return []
    with lock:
        try:
            with open(DB_ALARMES, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


def salvar_alarmes(alarmes: list) -> None:
    os.makedirs(os.path.dirname(DB_ALARMES), exist_ok=True)
    with lock:
        with open(DB_ALARMES, "w", encoding="utf-8") as f:
            json.dump(alarmes, f, indent=2, ensure_ascii=False)


def adicionar_alarme(
    hora: str,
    missao: str,
    repetir: bool = False,
    musica: str = "",
    data: str | None = None,
) -> str:
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
        "data": (data or "").strip() or None,
    }
    alarmes.append(alarme)
    salvar_alarmes(alarmes)
    rotulo = f"{data} " if data else ""
    confirmacoes = [
        f"Protocolo concluido. Alarme {rotulo}as {hora}, Senhor.",
        f"Cronometro sincronizado para {rotulo}{hora}. Estarei atento.",
        f"Alerta agendado para {rotulo}{hora}.",
    ]
    return random.choice(confirmacoes)


def remover_alarme(hora: str, missao: str, data: str | None = None) -> str:
    alarmes = carregar_alarmes()
    novos = [
        a
        for a in alarmes
        if not (
            a.get("hora") == hora
            and a.get("missao") == missao
            and (data is None or (a.get("data") or "") == data)
        )
    ]
    if len(novos) == len(alarmes):
        return "Senhor, nao encontrei esse alarme."
    salvar_alarmes(novos)
    return f"Alarme das {hora} removido."


def listar_alarmes() -> list:
    return [a for a in carregar_alarmes() if a["status"] == "pendente"]


def caminho_musica() -> str:
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
    global canal_alarme, sound_alarme, alarme_ativo
    caminho = caminho_musica()
    if not caminho:
        print("[ALARME] despertar.mp3 nao encontrado!")
        return
    if not PYGAME:
        print("[ALARME] pygame nao instalado!")
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), 4))
        sound_alarme = pygame.mixer.Sound(caminho)
        sound_alarme.set_volume(1.0)
        canal_alarme = pygame.mixer.Channel(1)
        canal_alarme.play(sound_alarme, loops=-1)
        while alarme_ativo and canal_alarme.get_busy():
            time.sleep(0.3)
        canal_alarme.stop()
    except Exception as e:
        print(f"[ALARME] Erro ao tocar musica: {e}")
    finally:
        canal_alarme = None
        sound_alarme = None


def _thread_tv():
    try:
        from tasks.smart_home import ligar_tv

        ligar_tv()
    except Exception:
        pass


def _tts_alarme(missao: str):
    import asyncio

    fn = falar_callback
    loop = _alarm_loop
    texto = (
        f"Senhor. Alarme. {missao or 'Hora de acordar'}. "
        "Liguei a TV se estiver disponivel. Protocolo de despertar ativo."
    )
    if fn and loop and not loop.is_closed():
        try:
            fut = asyncio.run_coroutine_threadsafe(fn(texto), loop)
            fut.result(timeout=180)
        except Exception:
            pass


def disparar_alarme(alarme: dict):
    global alarme_ativo
    alarme_ativo = True
    threading.Thread(target=_thread_tv, daemon=True).start()
    threading.Thread(target=lambda: _tts_alarme(str(alarme.get("missao", ""))), daemon=True).start()
    threading.Thread(target=tocar_musica_canal, daemon=True).start()


def parar_alarme_total():
    global alarme_ativo, canal_alarme
    alarme_ativo = False
    try:
        if canal_alarme is not None:
            canal_alarme.stop()
    except Exception:
        pass
    encerrar = [
        "Protocolo de despertar encerrado. Tenha um dia produtivo, Senhor.",
        "Sistemas de audio silenciados. Estou em prontidao.",
        "Entendido, Senhor. Bom dia de trabalho.",
    ]
    return random.choice(encerrar)


def verificar_agenda_loop():
    while True:
        agora_dt = datetime.now()
        hoje_iso = agora_dt.date().isoformat()
        agora_hm = agora_dt.strftime("%H:%M")
        alarmes = carregar_alarmes()
        for alarme in alarmes:
            if alarme["status"] != "pendente":
                continue
            d = (alarme.get("data") or "").strip()
            if d and d != hoje_iso:
                continue
            if alarme["hora"] != agora_hm:
                continue
            chave = f"{d or '*'}|{alarme['hora']}|{alarme['missao']}"
            if ultimo_disparo.get(chave) == hoje_iso:
                continue
            ultimo_disparo[chave] = hoje_iso
            threading.Thread(target=disparar_alarme, args=(alarme,), daemon=True).start()
            if not alarme.get("repetir"):
                alarme["status"] = "concluido"
            salvar_alarmes(alarmes)
        time.sleep(1)


def iniciar_sistema_alarmes():
    threading.Thread(target=verificar_agenda_loop, daemon=True).start()
    print("[JARVIS] Protocolos de agendamento online.")
