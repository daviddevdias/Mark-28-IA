import asyncio
import inspect
import psutil
import socket
import threading
import time
from datetime import datetime


ALERTAS = {
    "tempo": False,
    "bateria": False,
    "temp": False,
    "cpu": False,
    "rede": False,
    "ram": False,
}

inicio_sessao = datetime.now()
INTERVALO_S = 10
TEMP_CRITICA = 82
TEMP_OK = 70
RAM_CRITICA = 90.0
CPU_CRITICO = 95.0
BAT_CRITICA = 20

falar_callback = None
_monitor_async_loop = None







def registrar_falar(fn):
    global falar_callback
    falar_callback = fn


def registrar_loop_monitor_voz(loop):
    global _monitor_async_loop
    _monitor_async_loop = loop







def falar(texto: str) -> None:
    if not falar_callback:
        return
    try:
        if inspect.iscoroutinefunction(falar_callback):
            loop = _monitor_async_loop
            if loop is None or loop.is_closed():
                print("[SENTINELA] Voz: loop asyncio nao registrado.")
                return

            def _log_err(fut: asyncio.Future) -> None:
                try:
                    fut.result()
                except Exception as e:
                    print(f"[SENTINELA] Voz indisponivel: {e}")

            fut = asyncio.run_coroutine_threadsafe(falar_callback(texto), loop)
            fut.add_done_callback(_log_err)
        else:
            falar_callback(texto)
    except Exception as e:
        print(f"[SENTINELA] Voz indisponivel: {e}")







def check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False







def obter_temperatura_cpu() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        for nome in ("k10temp", "coretemp", "cpu_thermal", "acpitz"):
            if nome in temps and temps[nome]:
                return temps[nome][0].current
    except Exception:
        pass
    return None







def checar_rede() -> None:
    online = check_internet()
    if not online and not ALERTAS["rede"]:
        print("[!] ALERTA: Conexao com a rede perdida.")
        falar("Atencao, Chefe. Perda de conexao detectada.")
        ALERTAS["rede"] = True
    elif online and ALERTAS["rede"]:
        print("[+] Conexao restabelecida.")
        falar("Conexao restaurada. Sistemas online.")
        ALERTAS["rede"] = False







def checar_temperatura() -> None:
    temp = obter_temperatura_cpu()
    if temp is None:
        return
    if temp >= TEMP_CRITICA and not ALERTAS["temp"]:
        print(f"[!] CRITICO: CPU a {temp:.0f}C")
        falar(f"Alerta termico. Nucleo a {int(temp)} graus. Reduza a carga.")
        ALERTAS["temp"] = True
    elif temp < TEMP_OK:
        ALERTAS["temp"] = False







def checar_bateria() -> None:
    bat = psutil.sensors_battery()
    if not bat:
        return
    if bat.percent < BAT_CRITICA and not bat.power_plugged and not ALERTAS["bateria"]:
        falar(f"Bateria em {int(bat.percent)} por cento. Conecte o carregador.")
        ALERTAS["bateria"] = True
    elif bat.power_plugged:
        ALERTAS["bateria"] = False







def monitorar_proativo() -> None:
    CHECKERS = [checar_rede, checar_temperatura, checar_bateria]
    while True:
        for fn in CHECKERS:
            try:
                fn()
            except Exception:
                print(f"[SENTINELA] Erro em {fn.__name__}:")
        time.sleep(INTERVALO_S)







def iniciar_sentinela() -> None:
    t = threading.Thread(target=monitorar_proativo, daemon=True, name="Sentinela")
    t.start()