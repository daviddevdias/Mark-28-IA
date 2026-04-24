import subprocess
import platform
import psutil
from pathlib import Path


try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    PYAUTOGUI = True
except ImportError:
    PYAUTOGUI = False


OS = platform.system()







def fechar_janela() -> str:
    try:
        key = "command" if OS == "Darwin" else "alt"
        action = "q" if OS == "Darwin" else "f4"
        pyautogui.hotkey(key, action)
        return "Janela fechada."
    except Exception as e:
        return f"Erro: {e}"







def minimizar_tudo() -> str:
    try:
        combos = {
            "Windows": ("win", "d"),
            "Darwin":  ("fn", "f11"),
            "Linux":   ("super", "d"),
        }
        pyautogui.hotkey(*combos.get(OS, ("win", "d")))
        return "Janelas minimizadas."
    except Exception as e:
        return f"Erro: {e}"







def print_tela() -> str:
    try:
        combos = {
            "Windows": ("win", "shift", "s"),
            "Darwin":  ("command", "shift", "3"),
            "Linux":   ("ctrl", "print_screen"),
        }
        pyautogui.hotkey(*combos.get(OS, ("win", "shift", "s")))
        return "Captura acionada."
    except Exception as e:
        return f"Erro: {e}"







def bloquear_tela() -> str:
    try:
        cmds = {
            "Windows": ["rundll32.exe", "user32.dll,LockWorkStation"],
            "Darwin":  ["pmset", "displaysleepnow"],
            "Linux":   ["xdg-screensaver", "lock"],
        }
        subprocess.run(cmds.get(OS, []), check=True)
        return "Tela bloqueada."
    except Exception as e:
        return f"Erro: {e}"







def limpar_lixeira() -> str:
    try:
        cmds = {
            "Windows": ["powershell", "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
            "Darwin":  ["rm", "-rf", str(Path.home() / ".Trash" / "*")],
            "Linux":   ["gio", "trash", "--empty"],
        }
        subprocess.run(cmds.get(OS, []), check=True, shell=(OS == "Darwin"))
        return "Lixeira limpa."
    except Exception as e:
        return f"Erro: {e}"







def ajustar_volume(nivel: int) -> str:
    nivel = max(0, min(100, nivel))
    try:
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
        return f"Volume ajustado para {nivel}%."
    except Exception as e:
        return f"Erro ao ajustar volume: {e}"







def desligar_computador(atraso: int = 30) -> str:
    """
    Desliga o computador após `atraso` segundos (padrão 30).
    Passa atraso=0 para desligar imediatamente.
    """
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/s", "/t", str(atraso)], check=True)
        elif OS == "Darwin":
            subprocess.run(["sudo", "shutdown", "-h", f"+{atraso // 60 or 1}"], check=True)
        else:
            subprocess.run(["shutdown", "-h", f"+{atraso // 60 or 1}"], check=True)

        if atraso == 0:
            return "Protocolo de encerramento iniciado. Até logo, Senhor."
        return f"Computador será desligado em {atraso} segundos, Senhor. Para cancelar, diga cancelar desligamento."
    except Exception as e:
        return f"Erro ao desligar: {e}"







def cancelar_desligamento() -> str:
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/a"], check=True)
        else:
            subprocess.run(["sudo", "shutdown", "-c"], check=True)
        return "Desligamento cancelado. Sistemas em operação normal, Senhor."
    except Exception as e:
        return f"Erro ao cancelar: {e}"







def reiniciar_computador(atraso: int = 30) -> str:
    try:
        if OS == "Windows":
            subprocess.run(["shutdown", "/r", "/t", str(atraso)], check=True)
        elif OS == "Darwin":
            subprocess.run(["sudo", "shutdown", "-r", f"+{atraso // 60 or 1}"], check=True)
        else:
            subprocess.run(["shutdown", "-r", f"+{atraso // 60 or 1}"], check=True)
        return f"Reinicialização agendada para {atraso} segundos, Senhor."
    except Exception as e:
        return f"Erro ao reiniciar: {e}"







def computer_settings(parameters: dict) -> str:
    if not PYAUTOGUI and parameters.get("action") not in (
        "desligar", "reiniciar", "cancelar_desligamento", "limpar", "bloqueio", "volume"
    ):
        return "pyautogui não disponível."

    action = parameters.get("action", "").lower()

    actions = {
        "fechar":               fechar_janela,
        "minimizar_tudo":       minimizar_tudo,
        "print":                print_tela,
        "bloqueio":             bloquear_tela,
        "limpar":               limpar_lixeira,
        "desligar":             lambda: desligar_computador(int(parameters.get("atraso", 30))),
        "reiniciar":            lambda: reiniciar_computador(int(parameters.get("atraso", 30))),
        "cancelar_desligamento": cancelar_desligamento,
    }

    if action == "volume":
        return ajustar_volume(int(parameters.get("nivel", 50)))

    fn = actions.get(action)
    return fn() if fn else f"Ação '{action}' não reconhecida."