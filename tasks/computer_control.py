import subprocess
import platform
from pathlib import Path

from engine.cmd_security import avaliar

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    PYAUTOGUI = True
except ImportError:
    PYAUTOGUI = False

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

OS = platform.system()

def fechar_janela() -> str:
    if not PYAUTOGUI:
        return "Interação de interface indisponível."

    try:
        key    = "command" if OS == "Darwin" else "alt"
        action = "q" if OS == "Darwin" else "f4"
        pyautogui.hotkey(key, action)
        return "A janela prioritária foi fechada."
    except Exception:
        return "O sistema não pôde encerrar a janela solicitada."

def minimizar_tudo() -> str:
    if not PYAUTOGUI:
        return "Interação de interface indisponível."

    try:
        combos = {
            "Windows": ("win", "d"),
            "Darwin":  ("fn", "f11"),
            "Linux":   ("super", "d"),
        }
        pyautogui.hotkey(*combos.get(OS, ("win", "d")))
        return "Área de trabalho limpa. Janelas recolhidas."
    except Exception:
        return "Erro na requisição de interface."

def print_tela() -> str:
    if not PYAUTOGUI:
        return "Interação de interface indisponível."

    try:
        combos = {
            "Windows": ("win", "shift", "s"),
            "Darwin":  ("command", "shift", "3"),
            "Linux":   ("ctrl", "print_screen"),
        }
        pyautogui.hotkey(*combos.get(OS, ("win", "shift", "s")))
        return "Ferramenta de captura estática acionada."
    except Exception:
        return "Erro ao acionar buffer de tela."

def bloquear_tela() -> str:
    try:
        cmds = {
            "Windows": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "Darwin":  ["pmset", "displaysleepnow"],
            "Linux":   ["xdg-screensaver", "lock"],
        }
        av = avaliar(" ".join(cmds.get(OS, [])))
        if not av.permitido:
            return f"Bloqueio defensivo por restrição: {av.motivo}"

        subprocess.run(cmds.get(OS, []), check=True)
        return "Sessão do sistema trancada com sucesso."
    except Exception:
        return "A solicitação de segurança falhou em nível de OS."

def limpar_lixeira() -> str:
    try:
        cmds = {
            "Windows": ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
            "Darwin":  ["rm", "-rf", str(Path.home() / ".Trash" / "*")],
            "Linux":   ["gio", "trash", "--empty"],
        }
        subprocess.run(cmds.get(OS, []), check=True, shell=(OS == "Darwin"))
        return "Registro de descartes do sistema totalmente purgado."
    except Exception:
        return "Conflito de privilégios ao expurgar a lixeira."

def injetar_volume_pycaw(nivel: int) -> bool:
    if not PYCAW_AVAILABLE or OS != "Windows":
        return False

    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(nivel / 100.0, None)
        return True
    except Exception:
        return False

def ajustar_volume(nivel: int) -> str:
    nivel = max(0, min(100, nivel))
    try:
        if injetar_volume_pycaw(nivel):
            return f"Parâmetros de áudio ajustados com precisão via hardware interno para {nivel}%."

        if OS == "Windows":
            nircmd = Path("nircmd.exe")
            if nircmd.exists():
                vol = int(nivel / 100 * 65535)
                subprocess.run([str(nircmd), "setsysvolume", str(vol)], capture_output=True)
            else:
                script = (
                    "$obj = New-Object -ComObject WScript.Shell;"
                    "1..50 | ForEach-Object { $obj.SendKeys([char]174) };"
                    f"1..{nivel // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
                )
                subprocess.run(["powershell", "-Command", script], capture_output=True)

        return f"A injeção de evento confirmou a alteração para {nivel}%."
    except Exception:
        return "Os drivers de áudio não acataram a modificação solicitada."

def desligar_computador(atraso: int = 30) -> str:
    try:
        if OS == "Windows":
            cmd = ["shutdown", "/s", "/t", str(atraso)]
        elif OS == "Darwin":
            cmd = ["sudo", "shutdown", "-h", f"+{atraso // 60 or 1}"]
        else:
            cmd = ["shutdown", "-h", f"+{atraso // 60 or 1}"]

        av = avaliar(" ".join(cmd))
        if not av.permitido:
            return f"Ação barreada: {av.motivo}"

        subprocess.run(cmd, check=True)
        if atraso == 0:
            return "Iniciando sequência de queda imediata. Foi uma honra, Senhor."

        return f"Desligamento programado. Tempo restante: {atraso} segundos."
    except Exception:
        return "O processo mestre impediu a queda do sistema."

def cancelar_desligamento() -> str:
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/a"], check=True)
        else:
            subprocess.run(["sudo", "shutdown", "-c"], check=True)

        return "A queda programada foi suspensa. Reestabelecendo operações padrão."
    except Exception:
        return "Falha grave. O contador de desligamento não responde ao cancelamento."

def reiniciar_computador(atraso: int = 30) -> str:
    try:
        if OS == "Windows":
            cmd = ["shutdown", "/r", "/t", str(atraso)]
        elif OS == "Darwin":
            cmd = ["sudo", "shutdown", "-r", f"+{atraso // 60 or 1}"]
        else:
            cmd = ["shutdown", "-r", f"+{atraso // 60 or 1}"]

        av = avaliar(" ".join(cmd))
        if not av.permitido:
            return f"Tentativa interceptada: {av.motivo}"

        subprocess.run(cmd, check=True)
        return f"Ciclo de força agendado para daqui a {atraso} segundos, Senhor."
    except Exception:
        return "O kernel recusou a solicitação de reinício."

def computer_settings(parameters: dict) -> str:
    action = parameters.get("action", "").lower()
    if action == "volume":
        return ajustar_volume(int(parameters.get("nivel", 50)))

    actions = {
        "fechar":                fechar_janela,
        "minimizar_tudo":        minimizar_tudo,
        "print":                 print_tela,
        "bloqueio":              bloquear_tela,
        "limpar":                limpar_lixeira,
        "desligar":              lambda: desligar_computador(int(parameters.get("atraso", 30))),
        "reiniciar":             lambda: reiniciar_computador(int(parameters.get("atraso", 30))),
        "cancelar_desligamento": cancelar_desligamento,
    }
    fn = actions.get(action)
    return fn() if fn else f"O registro de ações '{action}' não consta nos meus protocolos."