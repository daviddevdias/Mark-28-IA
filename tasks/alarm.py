import json
import os
import random
import re
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta

try:
    import pygame
    PYGAME = True
except ImportError:
    PYGAME = False

DB_ALARMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "api", "alarme.json")
lock = threading.Lock()
alarme_ativo = False
falar_callback = None
ultimo_disparo: dict[str, str] = {}
canal_alarme = None
sound_alarme = None
alarm_loop_ativo = None

DIAS_SEMANA = {
    "segunda": 0, "segunda-feira": 0,
    "terca": 1, "terça": 1, "terca-feira": 1, "terça-feira": 1,
    "quarta": 2, "quarta-feira": 2,
    "quinta": 3, "quinta-feira": 3,
    "sexta": 4, "sexta-feira": 4,
    "sabado": 5, "sábado": 5,
    "domingo": 6,
}

MESES = {
    "janeiro": 1, "jan": 1, "fevereiro": 2, "fev": 2,
    "marco": 3, "março": 3, "mar": 3, "abril": 4, "abr": 4,
    "maio": 5, "mai": 5, "junho": 6, "jun": 6,
    "julho": 7, "jul": 7, "agosto": 8, "ago": 8,
    "setembro": 9, "set": 9, "outubro": 10, "out": 10,
    "novembro": 11, "nov": 11, "dezembro": 12, "dez": 12,
}

SNOOZE_MINUTOS = 10


def registrar_falar_alarme(fn):
    global falar_callback
    falar_callback = fn


def registrar_loop_alarme(loop):
    global alarm_loop_ativo
    alarm_loop_ativo = loop


def limpar_acentos(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse_alarme_voz(cmd: str) -> tuple[str | None, str | None, str, list[int] | None]:
    raw = cmd.strip()
    low = limpar_acentos(raw)
    data_iso: str | None = None
    hora: str | None = None
    dias_semana: list[int] | None = None

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
        m_pt = re.search(r"(?:^|\s)(?:dia)?\s*(\d{1,2})\s+de\s+([a-z]+)(?:\s+de\s+(\d{2,4}))?", low)
        if m_pt:
            d = int(m_pt.group(1))
            mi = MESES.get(m_pt.group(2))
            if mi:
                yraw = m_pt.group(3)
                yi = int(yraw) if yraw else datetime.now().year
                if yraw and yi < 100:
                    yi += 2000
                try:
                    data_iso = date(yi, mi, d).isoformat()
                except ValueError:
                    data_iso = None

    if not data_iso:
        encontrados = [idx for nome, idx in DIAS_SEMANA.items() if nome in low]
        if encontrados:
            dias_semana = list(set(encontrados))

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
        r"\s+", " ",
        re.sub(
            r"(?i)\b(jarvis|alarme|despertar|agendar|criar|lembrete|dia|as|h|horas|de|"
            r"maio|janeiro|fevereiro|marco|abril|junho|julho|agosto|setembro|outubro|novembro|dezembro|"
            r"segunda|terca|quarta|quinta|sexta|sabado|domingo|feira|"
            r"\d{1,2}[:h]\d{2}|\d{4}-\d{2}-\d{2})\b",
            " ", raw,
        ),
    ).strip()[:120]
    if not missao:
        missao = "Alarme"

    return data_iso, hora, missao, dias_semana


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


def limpar_alarmes_concluidos() -> int:
    alarmes = carregar_alarmes()
    antes = len(alarmes)
    ativos = [a for a in alarmes if a.get("status") != "concluido"]
    if len(ativos) < antes:
        salvar_alarmes(ativos)
    return antes - len(ativos)


def adicionar_alarme(
    hora: str,
    missao: str,
    repetir: bool = False,
    musica: str = "",
    data: str | None = None,
    dias_semana: list[int] | None = None,
) -> str:
    if not hora or ":" not in hora:
        return "Senhor, o formato de tempo parece inconsistente. Poderia repetir?"
    alarmes = carregar_alarmes()
    alarmes.append({
        "hora": hora,
        "missao": missao,
        "status": "pendente",
        "repetir": repetir or bool(dias_semana),
        "musica": musica,
        "criado_em": datetime.now().isoformat(),
        "ultimo_disparo": None,
        "data": (data or "").strip() or None,
        "dias_semana": dias_semana,
    })
    salvar_alarmes(alarmes)
    return "Senhor, despertador configurado."


def remover_alarme(hora: str, missao: str, data: str | None = None) -> str:
    alarmes = carregar_alarmes()
    novos = [
        a for a in alarmes
        if not (
            a.get("hora") == hora
            and a.get("missao") == missao
            and (data is None or (a.get("data") or "") == data)
        )
    ]
    if len(novos) == len(alarmes):
        return "Senhor, nao encontrei esse alarme."
    salvar_alarmes(novos)
    return f"Alarme das {hora} foi desativado."


def listar_alarmes() -> list:
    return [a for a in carregar_alarmes() if a["status"] == "pendente"]


def snooze_alarme() -> str:
    agora = datetime.now()
    nova = agora + timedelta(minutes=SNOOZE_MINUTOS)
    hora_nova = nova.strftime("%H:%M")
    adicionar_alarme(hora_nova, "Soneca", data=agora.date().isoformat())
    return f"Soneca ativada por {SNOOZE_MINUTOS} minutos. Voltarei a chamar as {hora_nova}."


def buscar_arquivo_musica() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "assets", "despertar.wav"),
        os.path.join(os.getcwd(), "assets", "despertar.wav"),
        os.path.join(base, "despertar.wav"),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return ""


def invocar_som_alarme():
    global canal_alarme, sound_alarme, alarme_ativo
    caminho = buscar_arquivo_musica()
    if not caminho or not PYGAME:
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
        if canal_alarme:
            canal_alarme.stop()
    except Exception:
        pass
    finally:
        canal_alarme = None
        sound_alarme = None


def ligar_tela_tv():
    try:
        from tasks.smart_home import ligar_tv
        ligar_tv()
    except Exception:
        pass


def avisar_voz_alarme(missao: str):
    import asyncio
    fn = falar_callback
    loop = alarm_loop_ativo
    texto = f"Senhor, agora estou despertando. {missao}"
    if fn and loop and not loop.is_closed():
        try:
            fut = asyncio.run_coroutine_threadsafe(fn(texto), loop)
            fut.result(timeout=180)
        except Exception:
            pass


def deflagrar_rotina_alarme(alarme: dict):
    global alarme_ativo
    alarme_ativo = True
    threading.Thread(target=ligar_tela_tv, daemon=True).start()
    threading.Thread(target=lambda: avisar_voz_alarme(str(alarme.get("missao", ""))), daemon=True).start()
    threading.Thread(target=invocar_som_alarme, daemon=True).start()


def parar_alarme_total():
    global alarme_ativo, canal_alarme
    alarme_ativo = False
    try:
        if canal_alarme is not None:
            canal_alarme.stop()
    except Exception:
        pass
    return random.choice([
        "Protocolo encerrado. Mantenha o foco, Senhor.",
        "Ameaça neutralizada. Estou na escuta.",
        "Comando aceito. Alarme silenciado.",
    ])


def checagem_temporizador_loop():
    ciclo = 0
    while True:
        agora_dt = datetime.now()
        hoje_iso = agora_dt.date().isoformat()
        agora_hm = agora_dt.strftime("%H:%M")
        dia_semana_atual = agora_dt.weekday()
        alarmes = carregar_alarmes()
        modificados = False

        for alarme in alarmes:
            if alarme["status"] != "pendente":
                continue
            d = (alarme.get("data") or "").strip()
            dias = alarme.get("dias_semana")
            if dias is not None:
                if dia_semana_atual not in dias:
                    continue
            elif d and d != hoje_iso:
                continue
            if alarme["hora"] != agora_hm:
                continue
            chave = f"{d or str(dia_semana_atual)}|{alarme['hora']}|{alarme['missao']}"
            if ultimo_disparo.get(chave) == hoje_iso:
                continue
            ultimo_disparo[chave] = hoje_iso
            threading.Thread(target=deflagrar_rotina_alarme, args=(alarme,), daemon=True).start()
            if not alarme.get("repetir") and dias is None:
                alarme["status"] = "concluido"
                modificados = True

        if modificados:
            salvar_alarmes(alarmes)

        ciclo += 1
        if ciclo >= 3600:
            limpar_alarmes_concluidos()
            try:
                import asyncio
                from storage.optimizer import comprimir_banco_auditoria, purgar_resumos_antigos
                asyncio.run(comprimir_banco_auditoria())
                purgar_resumos_antigos(dias=365)
            except Exception:
                pass
            ciclo = 0

        time.sleep(1)


def iniciar_sistema_alarmes():
    threading.Thread(target=checagem_temporizador_loop, daemon=True).start()