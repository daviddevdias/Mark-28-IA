from __future__ import annotations

import asyncio
import inspect
import os
import sqlite3
import psutil
import socket
import threading
import time
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "monitor.db")

ALERTAS = {
    "tempo":   False,
    "bateria": False,
    "temp":    False,
    "cpu":     False,
    "rede":    False,
    "ram":     False,
    "disco":   False,
}

inicio_sessao  = datetime.now()
INTERVALO_S    = 10
TEMP_CRITICA   = 82
TEMP_OK        = 70
RAM_CRITICA    = 85.0
RAM_OK         = 75.0
CPU_CRITICO    = 90.0
CPU_OK         = 80.0
BAT_CRITICA    = 20
DISCO_CRITICO  = 90.0
DISCO_OK       = 80.0

falar_callback     = None
monitor_async_loop = None


def conectar_banco_monitor() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT NOT NULL,
            tipo      TEXT NOT NULL,
            mensagem  TEXT NOT NULL,
            valor     REAL
        )
    """)
    conn.commit()
    return conn


def registrar_log_alerta(tipo: str, mensagem: str, valor: float = 0.0) -> None:
    try:
        with conectar_banco_monitor() as conn:
            conn.execute(
                "INSERT INTO alertas (ts, tipo, mensagem, valor) VALUES (?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), tipo, mensagem, valor),
            )
            conn.commit()
    except Exception:
        pass


def registrar_falar(fn):
    global falar_callback
    falar_callback = fn


def registrar_loop_monitor_voz(loop):
    global monitor_async_loop
    monitor_async_loop = loop


def falar(texto: str) -> None:
    if not falar_callback:
        return
    try:
        if inspect.iscoroutinefunction(falar_callback):
            loop = monitor_async_loop
            if loop is None or loop.is_closed():
                return
            fut = asyncio.run_coroutine_threadsafe(falar_callback(texto), loop)
            fut.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
        else:
            falar_callback(texto)
    except Exception:
        pass


def check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def obter_temperatura_cpu() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for nome in ("k10temp", "coretemp", "cpu_thermal", "acpitz"):
                if nome in temps and temps[nome]:
                    return temps[nome][0].current
    except Exception:
        pass
    try:
        import wmi
        w = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
        cpu_temps = [s.Value for s in w.Sensor() if s.SensorType == "Temperature" and "CPU" in s.Name]
        if cpu_temps:
            return max(cpu_temps)
    except Exception:
        pass
    return None


def finalizar_processos_gargalo(limite_pct: float = 80.0) -> None:
    try:
        procs = [
            p for p in psutil.process_iter(["pid", "name", "cpu_percent"])
            if p.info["cpu_percent"] and p.info["cpu_percent"] > limite_pct
        ]
        for p in procs[:2]:
            nome = p.info["name"]
            if nome.lower() not in ("jarvis", "python", "python3", "pythonw"):
                try:
                    p.kill()
                    registrar_log_alerta("cpu_kill", f"Processo {nome} (pid {p.info['pid']}) encerrado por CPU alta.", p.info["cpu_percent"])
                except Exception:
                    pass
    except Exception:
        pass


def checar_rede() -> None:
    online = check_internet()
    if not online and not ALERTAS["rede"]:
        registrar_log_alerta("rede", "Conexão perdida.")
        falar("Atencao, Chefe. Perda de conexao detectada.")
        ALERTAS["rede"] = True
    elif online and ALERTAS["rede"]:
        registrar_log_alerta("rede", "Conexão restaurada.")
        falar("Conexao restaurada. Sistemas online.")
        ALERTAS["rede"] = False


def checar_temperatura() -> None:
    temp = obter_temperatura_cpu()
    if temp is None:
        return
    if temp >= TEMP_CRITICA and not ALERTAS["temp"]:
        registrar_log_alerta("temperatura", f"CPU a {temp:.0f}°C", temp)
        falar(f"Alerta termico. Nucleo a {int(temp)} graus. Reduza a carga.")
        ALERTAS["temp"] = True
    elif temp < TEMP_OK:
        ALERTAS["temp"] = False


def checar_bateria() -> None:
    bat = psutil.sensors_battery()
    if not bat:
        return
    if bat.percent < BAT_CRITICA and not bat.power_plugged and not ALERTAS["bateria"]:
        registrar_log_alerta("bateria", f"Bateria em {bat.percent:.0f}%", bat.percent)
        falar(f"Bateria em {int(bat.percent)} por cento. Conecte o carregador.")
        ALERTAS["bateria"] = True
    elif bat.power_plugged:
        ALERTAS["bateria"] = False


def checar_cpu() -> None:
    uso = psutil.cpu_percent(interval=1)
    if uso >= CPU_CRITICO and not ALERTAS["cpu"]:
        registrar_log_alerta("cpu", f"CPU em {uso:.0f}%", uso)
        falar(f"Processador em {int(uso)} por cento. Sistema sobrecarregado.")
        ALERTAS["cpu"] = True
        finalizar_processos_gargalo(limite_pct=85.0)
    elif uso < CPU_OK and ALERTAS["cpu"]:
        ALERTAS["cpu"] = False


def checar_disco() -> None:
    try:
        uso = psutil.disk_usage("/").percent
    except Exception:
        try:
            uso = psutil.disk_usage("C:\\").percent
        except Exception:
            return
    if uso >= DISCO_CRITICO and not ALERTAS["disco"]:
        registrar_log_alerta("disco", f"Disco em {uso:.0f}%", uso)
        falar(f"Disco em {int(uso)} por cento. Libere espaco em disco.")
        ALERTAS["disco"] = True
    elif uso < DISCO_OK and ALERTAS["disco"]:
        ALERTAS["disco"] = False


CHECKERS = [checar_rede, checar_temperatura, checar_bateria, checar_cpu, checar_disco]


def monitorar_proativo() -> None:
    while True:
        for fn in CHECKERS:
            try:
                fn()
            except Exception as e:
                print(f"[SENTINELA] Erro em {fn.__name__}: {e}")
        time.sleep(INTERVALO_S)


def iniciar_sentinela() -> None:
    threading.Thread(target=monitorar_proativo, daemon=True, name="Sentinela").start()


def status_hardware() -> dict:
    bat  = psutil.sensors_battery()
    temp = obter_temperatura_cpu()
    try:
        disco = psutil.disk_usage("/").percent
    except Exception:
        try:
            disco = psutil.disk_usage("C:\\").percent
        except Exception:
            disco = None
    return {
        "cpu_percent":     psutil.cpu_percent(interval=None),
        "ram_percent":     psutil.virtual_memory().percent,
        "temp_cpu":        round(temp, 1) if temp else None,
        "disco_percent":   disco,
        "bateria_percent": bat.percent if bat else None,
        "carregando":      bat.power_plugged if bat else None,
        "alertas":         {k: v for k, v in ALERTAS.items() if v},
    }


def alertas_recentes(limite: int = 50) -> list[dict]:
    try:
        with conectar_banco_monitor() as conn:
            rows = conn.execute(
                "SELECT ts, tipo, mensagem, valor FROM alertas ORDER BY id DESC LIMIT ?",
                (limite,),
            ).fetchall()
            return [dict(zip(("ts", "tipo", "mensagem", "valor"), r)) for r in rows]
    except Exception:
        return []