import winsound
import time
import threading
import json
import os
from datetime import datetime

DB_ALARMES = "logs/alarmes.json"

_lock = threading.Lock()

_BEEP_PATTERN = [(1800, 200), (1200, 200), (1600, 300)]

_falar_callback = None
_notificar_callback = None

_ultimo_disparo = {}


def registrar_falar_alarme(fn):
    global _falar_callback
    _falar_callback = fn


def registrar_notificar_alarme(fn):
    global _notificar_callback
    _notificar_callback = fn


def carregar_alarmes() -> list:
    if not os.path.exists(DB_ALARMES):
        return []
    with _lock:
        try:
            with open(DB_ALARMES, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


def salvar_alarmes(alarmes: list) -> None:
    os.makedirs(os.path.dirname(DB_ALARMES), exist_ok=True)
    with _lock:
        with open(DB_ALARMES, "w", encoding="utf-8") as f:
            json.dump(alarmes, f, indent=2, ensure_ascii=False)


def adicionar_alarme(hora: str, missao: str, repetir: bool = False) -> str:
    if not hora or ":" not in hora:
        return "Formato inválido. Use HH:MM."

    alarmes = carregar_alarmes()

    alarme = {
        "hora": hora,
        "missao": missao,
        "status": "pendente",
        "repetir": repetir,
        "criado_em": datetime.now().isoformat(),
        "ultimo_disparo": None,
    }

    alarmes.append(alarme)
    salvar_alarmes(alarmes)

    return f"Alarme '{missao}' criado para {hora}."


def remover_alarme(hora: str, missao: str) -> str:
    alarmes = carregar_alarmes()

    novos = [
        a for a in alarmes
        if not (a["hora"] == hora and a["missao"] == missao)
    ]

    if len(novos) == len(alarmes):
        return "Alarme não encontrado."

    salvar_alarmes(novos)
    return f"Alarme '{missao}' removido."


def listar_alarmes() -> list:
    return [a for a in carregar_alarmes() if a["status"] == "pendente"]


def _som_alarme():
    for freq, dur in _BEEP_PATTERN:
        try:
            winsound.Beep(freq, dur)
        except Exception:
            pass


def disparar_alarme(alarme: dict):
    _som_alarme()

    texto = f"Chefe, protocolo '{alarme['missao']}' iniciado agora."

    if _falar_callback:
        try:
            _falar_callback(texto)
        except Exception as e:
            print(f"[ALARME] erro voz: {e}")

    if _notificar_callback:
        try:
            _notificar_callback(texto)
        except Exception as e:
            print(f"[ALARME] erro notificação: {e}")

    print(f"[ALARME] {texto}")


def verificar_agenda_loop():
    while True:
        agora = datetime.now().strftime("%H:%M")

        alarmes = carregar_alarmes()
        alterou = False

        for alarme in alarmes:
            if alarme["status"] != "pendente":
                continue

            chave = f"{alarme['hora']}-{alarme['missao']}"

            if _ultimo_disparo.get(chave) == agora:
                continue

            if alarme["hora"] == agora:
                _ultimo_disparo[chave] = agora

                threading.Thread(
                    target=disparar_alarme,
                    args=(alarme,),
                    daemon=True,
                ).start()

                alarme["ultimo_disparo"] = agora

                if alarme.get("repetir"):
                    alarme["status"] = "pendente"
                else:
                    alarme["status"] = "concluido"

                alterou = True

        if alterou:
            salvar_alarmes(alarmes)

        time.sleep(1)


def iniciar_sistema_alarmes():
    threading.Thread(
        target=verificar_agenda_loop,
        daemon=True,
    ).start()

    print("[ALARMES] sistema ativo")