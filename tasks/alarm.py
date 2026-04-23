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


def registrar_falar_alarme(fn):
    global _falar_callback
    _falar_callback = fn


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
        return "Formato de hora inválido. Use HH:MM."
    alarmes = carregar_alarmes()
    alarme = {"hora": hora, "missao": missao, "status": "pendente", "repetir": repetir}
    alarmes.append(alarme)
    salvar_alarmes(alarmes)
    print(f"[ALARME] Agendado: {hora} — {missao}")
    return f"Alarme '{missao}' configurado para {hora}."


def remover_alarme(hora: str, missao: str) -> str:
    alarmes = carregar_alarmes()
    antes = len(alarmes)
    alarmes = [a for a in alarmes if not (a["hora"] == hora and a["missao"] == missao)]
    if len(alarmes) < antes:
        salvar_alarmes(alarmes)
        return f"Alarme '{missao}' removido."
    return "Alarme não encontrado."


def listar_alarmes() -> list:
    return [a for a in carregar_alarmes() if a["status"] == "pendente"]


def _som_alarme() -> None:
    for freq, dur in _BEEP_PATTERN:
        try:
            winsound.Beep(freq, dur)
        except Exception:
            pass


def disparar_alarme(missao: str) -> None:
    _som_alarme()
    texto = f"Chefe, protocolo '{missao}' deve ser iniciado agora."
    if _falar_callback:
        try:
            _falar_callback(texto)
        except Exception as e:
            print(f"[ALARME] Voz indisponivel: {e}")
    else:
        print(f"[ALARME] {texto}")


def verificar_agenda_loop() -> None:
    while True:
        agora = datetime.now().strftime("%H:%M")
        alarmes = carregar_alarmes()
        pendentes, alterou = [], False

        for alarme in alarmes:
            if alarme["hora"] == agora and alarme["status"] == "pendente":
                threading.Thread(
                    target=disparar_alarme, args=(alarme["missao"],), daemon=True
                ).start()
                alarme["status"] = "concluido"
                alterou = True
                if alarme.get("repetir"):
                    pendentes.append({
                        "hora": alarme["hora"],
                        "missao": alarme["missao"],
                        "status": "pendente",
                        "repetir": True,
                    })
            elif alarme["status"] == "pendente":
                pendentes.append(alarme)

        if alterou:
            salvar_alarmes(pendentes)

        time.sleep(30)


def iniciar_sistema_alarmes() -> None:
    threading.Thread(target=verificar_agenda_loop, daemon=True).start()
    print("[ALARMES] Sistema de agenda ativo.")