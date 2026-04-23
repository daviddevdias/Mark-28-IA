import psutil
import time
import threading
import socket
from datetime import datetime


_ALERTAS = {
    "tempo": False,
    "bateria": False,
    "temp": False,
    "cpu": False,
    "rede": False,
    "ram": False,
}
_inicio_sessao = datetime.now()
_INTERVALO_S = 10
_TEMP_CRITICA = 82
_TEMP_OK = 70
_RAM_CRITICA = 90.0
_CPU_CRITICO = 95.0
_BAT_CRITICA = 20

_falar_callback = None


def registrar_falar(fn):
    global _falar_callback
    _falar_callback = fn


def _falar(texto: str) -> None:
    if _falar_callback:
        try:
            _falar_callback(texto)
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


def _checar_rede() -> None:
    online = check_internet()
    if not online and not _ALERTAS["rede"]:
        print("[!] ALERTA: Conexao com a rede perdida.")
        _falar("Atencao, Chefe. Perda de conexao detectada.")
        _ALERTAS["rede"] = True
    elif online and _ALERTAS["rede"]:
        print("[+] Conexao restabelecida.")
        _falar("Conexao restaurada. Sistemas online.")
        _ALERTAS["rede"] = False


def _checar_temperatura() -> None:
    temp = obter_temperatura_cpu()
    if temp is None:
        return
    if temp >= _TEMP_CRITICA and not _ALERTAS["temp"]:
        print(f"[!] CRITICO: CPU a {temp:.0f}C")
        _falar(f"Alerta termico. Nucleo a {int(temp)} graus. Reduza a carga.")
        _ALERTAS["temp"] = True
    elif temp < _TEMP_OK:
        _ALERTAS["temp"] = False


def _checar_ram() -> None:
    pct = psutil.virtual_memory().percent
    if pct >= _RAM_CRITICA and not _ALERTAS["ram"]:
        print(f"[!] RAM critica: {pct:.0f}%")
        _falar(f"Memoria RAM em {int(pct)} por cento. Considere fechar aplicativos.")
        _ALERTAS["ram"] = True
    elif pct < _RAM_CRITICA - 5:
        _ALERTAS["ram"] = False


def _checar_bateria() -> None:
    bat = psutil.sensors_battery()
    if not bat:
        return
    if bat.percent < _BAT_CRITICA and not bat.power_plugged and not _ALERTAS["bateria"]:
        _falar(f"Bateria em {int(bat.percent)} por cento. Conecte o carregador.")
        _ALERTAS["bateria"] = True
    elif bat.power_plugged:
        _ALERTAS["bateria"] = False


def monitorar_proativo() -> None:
    _CHECKERS = [_checar_rede, _checar_temperatura, _checar_ram, _checar_bateria]
    while True:
        for fn in _CHECKERS:
            try:
                fn()
            except Exception as e:
                print(f"[SENTINELA] Erro em {fn.__name__}: {e}")
        time.sleep(_INTERVALO_S)


def iniciar_sentinela() -> None:
    print(
        "-                                             -\n"
        "-                                              -\n"
        "-                                               -\n"
        "-                                                -\n"
        "[Jarvis] Motor Sentinela - Ativado verificando tudo\n"
        "-                                                  -\n"
        "-                                                   -\n"
        "-                                                    -\n"
        "-                                                     -\n"
        "-                                                      -\n"
    )
    t = threading.Thread(target=monitorar_proativo, daemon=True, name="Sentinela")
    t.start()