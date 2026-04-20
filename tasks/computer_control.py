import subprocess
import platform
import psutil
from pathlib import Path







try:
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False










_OS = platform.system()










def fechar_janela() -> str:
    try:
        key = "command" if _OS == "Darwin" else "alt"
        action = "q" if _OS == "Darwin" else "f4"
        pyautogui.hotkey(key, action)
        return "Janela fechada."
    except Exception as e:
        return f"Erro: {e}"








def minimizar_tudo() -> str:
    try:
        combos = {
            "Windows": ("win", "d"),
            "Darwin": ("fn", "f11"),
            "Linux": ("super", "d"),
        }
        pyautogui.hotkey(*combos.get(_OS, ("win", "d")))
        return "Janelas minimizadas."
    except Exception as e:
        return f"Erro: {e}"










def print_tela() -> str:
    try:
        combos = {
            "Windows": ("win", "shift", "s"),
            "Darwin": ("command", "shift", "3"),
            "Linux": ("ctrl", "print_screen"),
        }
        pyautogui.hotkey(*combos.get(_OS, ("win", "shift", "s")))
        return "Captura acionada."
    except Exception as e:
        return f"Erro: {e}"








def bloquear_tela() -> str:
    try:
        cmds = {
            "Windows": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "Darwin": ["pmset", "displaysleepnow"],
            "Linux": ["xdg-screensaver", "lock"],
        }
        subprocess.run(cmds.get(_OS, []), check=True)
        return "Tela bloqueada."
    except Exception as e:
        return f"Erro: {e}"
    







def limpar_lixeira() -> str:
    try:
        cmds = {
            "Windows": [
                "powershell",
                "-Command",
                "Clear-RecycleBin -Force -ErrorAction SilentlyContinue",
            ],
            "Darwin": ["rm", "-rf", str(Path.home() / ".Trash" / "*")],
            "Linux": ["gio", "trash", "--empty"],
        }
        subprocess.run(cmds.get(_OS, []), check=True, shell=(_OS == "Darwin"))
        return "Lixeira limpa."
    except Exception as e:
        return f"Erro: {e}"
    





def ajustar_volume(nivel: int) -> str:
    nivel = max(0, min(100, nivel))
    try:
        if _OS == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"(New-Object -ComObject WScript.Shell).SendKeys([char]174 * {nivel // 2})",
                ],
                capture_output=True,
            )
        return f"Volume ajustado para {nivel}%."
    except Exception as e:
        return f"Erro ao ajustar volume: {e}"




def computer_settings(parameters: dict) -> str:
    if not _PYAUTOGUI:
        return "pyautogui não disponível."

    action = parameters.get("action", "").lower()
    actions = {
        "fechar": fechar_janela,
        "minimizar_tudo": minimizar_tudo,
        "print": print_tela,
        "bloqueio": bloquear_tela,
        "limpar": limpar_lixeira,
    }

    if action == "volume":
        return ajustar_volume(int(parameters.get("nivel", 50)))

    fn = actions.get(action)
    return fn() if fn else f"Ação '{action}' não reconhecida."
