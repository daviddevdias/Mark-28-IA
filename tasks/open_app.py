import time
import subprocess
import platform
import shutil
import psutil

APP_ALIASES = {
    "whatsapp": {"Windows": "WhatsApp", "Darwin": "WhatsApp", "Linux": "whatsapp"},
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "spotify": {"Windows": "Spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "visual studio code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "discord": {"Windows": "Discord", "Darwin": "Discord", "Linux": "discord"},
    "telegram": {"Windows": "Telegram", "Darwin": "Telegram", "Linux": "telegram"},
    "instagram": {"Windows": "Instagram", "Darwin": "Instagram", "Linux": "instagram"},
    "tiktok": {"Windows": "TikTok", "Darwin": "TikTok", "Linux": "tiktok"},
    "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "calculator": {"Windows": "calc.exe", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "terminal": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "gnome-terminal"},
    "cmd": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "file explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "paint": {"Windows": "mspaint.exe", "Darwin": "Preview", "Linux": "gimp"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word", "Linux": "libreoffice --writer"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel", "Linux": "libreoffice --calc"},
    "powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "vlc": {"Windows": "vlc", "Darwin": "VLC", "Linux": "vlc"},
    "zoom": {"Windows": "Zoom", "Darwin": "zoom.us", "Linux": "zoom"},
    "slack": {"Windows": "Slack", "Darwin": "Slack", "Linux": "slack"},
    "steam": {"Windows": "steam", "Darwin": "Steam", "Linux": "steam"},
    "task manager": {"Windows": "taskmgr.exe", "Darwin": "Activity Monitor", "Linux": "gnome-system-monitor"},
    "settings": {"Windows": "ms-settings:", "Darwin": "System Preferences", "Linux": "gnome-control-center"},
    "powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave-browser"},
    "obsidian": {"Windows": "Obsidian", "Darwin": "Obsidian", "Linux": "obsidian"},
    "notion": {"Windows": "Notion", "Darwin": "Notion", "Linux": "notion"},
    "blender": {"Windows": "blender", "Darwin": "Blender", "Linux": "blender"},
    "capcut": {"Windows": "CapCut", "Darwin": "CapCut", "Linux": "capcut"},
    "postman": {"Windows": "Postman", "Darwin": "Postman", "Linux": "postman"},
    "figma": {"Windows": "Figma", "Darwin": "Figma", "Linux": "figma"},
}







def verificar_processo_ativo(app_name: str) -> bool:
    target = app_name.lower().replace(".exe", "")
    for proc in psutil.process_iter(['name']):
        try:
            if target in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False







def padronizar_nome(raw: str) -> str:
    system = platform.system()
    key = raw.lower().strip()
    if key in APP_ALIASES:
        return APP_ALIASES[key].get(system, raw)
    for alias_key, os_map in APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(system, raw)
    return raw







def disparar_no_windows(app_name: str) -> bool:
    if shutil.which(app_name):
        try:
            subprocess.Popen([app_name], shell=False,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    try:
        subprocess.Popen(app_name, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        pass
    try:
        import pyautogui
        pyautogui.press("win")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        return True
    except Exception:
        return False







def disparar_no_mac(app_name: str) -> bool:
    try:
        res = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if res.returncode == 0:
            return True
        res = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if res.returncode == 0:
            return True
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        return True
    except Exception:
        return False







def disparar_no_linux(app_name: str) -> bool:
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        pass
    return False







def open_app(parameters=None, **kwargs) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "Qual aplicativo devo providenciar a abertura?"

    if verificar_processo_ativo(app_name):
        return f"O processo ligado a {app_name} já se encontra ativo na memória."

    system = platform.system()
    normalized = padronizar_nome(app_name)

    launchers = {
        "Windows": disparar_no_windows,
        "Darwin": disparar_no_mac,
        "Linux": disparar_no_linux,
    }

    launcher = launchers.get(system)
    if not launcher:
        return f"Sistema {system} rejeitou a operação."

    success = launcher(normalized)
    if not success and normalized != app_name:
        success = launcher(app_name)

    return (
        f"Ação concluída. {app_name} disparado."
        if success
        else f"Falha sistêmica ao localizar o atalho para {app_name}."
    )