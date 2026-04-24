import time
import requests
import config
import logging

log = logging.getLogger("CORE.smartthings")


API_BASE       = "https://api.smartthings.com/v1"
DEVICES_TTL    = 60
tv_id_cache:   str | None  = None
devices_cache: list | None = None
devices_cache_ts: float    = 0.0


def headers() -> dict:
    return {"Authorization": f"Bearer {config.SMARTTHINGS_TOKEN}"}


def get(endpoint: str) -> dict | None:
    if not config.SMARTTHINGS_TOKEN:
        log.error("Token SmartThings não configurado.")
        return None
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", headers=headers(), timeout=8)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        log.error("GET %s: %s", endpoint, e)
        return None


def post(endpoint: str, payload: list) -> bool:
    if not config.SMARTTHINGS_TOKEN:
        return False
    try:
        res = requests.post(
            f"{API_BASE}/{endpoint}",
            headers=headers(),
            json=payload,
            timeout=8,
        )
        return res.status_code == 200
    except Exception as e:
        log.error("POST %s: %s", endpoint, e)
        return False


def carregar_devices(forcar: bool = False) -> list:
    global devices_cache, devices_cache_ts

    agora = time.time()
    if devices_cache and not forcar and (agora - devices_cache_ts) < DEVICES_TTL:
        return devices_cache

    dados = get("devices")
    if not dados:
        return devices_cache or []

    devices_cache    = dados.get("items", [])
    devices_cache_ts = agora
    return devices_cache


def buscar_device_por_label(label_busca: str) -> str | None:
    label_busca = label_busca.lower().strip()
    for device in carregar_devices():
        label = device.get("label", "").lower()
        name  = device.get("name", "").lower()
        if label_busca in label or label_busca in name:
            return device["deviceId"]
    return None


def enviar_comando_device(
    device_id: str, comando: str, capacidade: str, argumentos: list | None = None
) -> bool:
    payload = [
        {
            "component":  "main",
            "capability": capacidade,
            "command":    comando,
            "arguments":  argumentos or [],
        }
    ]
    ok = post(f"devices/{device_id}/commands", payload)
    log.info("Comando '%s' → device %s: %s", comando, device_id[:8], "OK" if ok else "FALHOU")
    return ok


def buscar_id_tv(forcar: bool = False) -> str | None:
    global tv_id_cache

    if tv_id_cache and not forcar:
        return tv_id_cache

    for device in carregar_devices(forcar):
        label = device.get("label", "").lower()
        name  = device.get("name", "").lower()
        if "hub" not in label and ("tv" in label or "samsung" in name or "[tv]" in label):
            tv_id_cache = device["deviceId"]
            return tv_id_cache

    log.warning("Nenhuma TV Samsung encontrada.")
    return None


def enviar_comando_tv(comando: str, capacidade: str, argumentos: list | None = None) -> bool:
    device_id = buscar_id_tv()
    if not device_id:
        return False
    return enviar_comando_device(device_id, comando, capacidade, argumentos)


def ligar_tv() -> bool:
    return enviar_comando_tv("on", "switch")


def desligar_tv() -> bool:
    return enviar_comando_tv("off", "switch")


def ajustar_volume_tv(nivel: int) -> bool:
    nivel = max(0, min(100, nivel))
    return enviar_comando_tv("setVolume", "audioVolume", [nivel])


def status_tv() -> str:
    device_id = buscar_id_tv()
    if not device_id:
        return "TV não encontrada na rede."
    dados = get(f"devices/{device_id}/status")
    if not dados:
        return "Não foi possível obter o status da TV."
    switch = dados.get("components", {}).get("main", {}).get("switch", {}).get("switch", {})
    estado = switch.get("value", "desconhecido")
    return f"TV Samsung: {estado.upper()}"


def ligar_lampada(label: str) -> str:
    device_id = buscar_device_por_label(label)
    if not device_id:
        return f"Lâmpada '{label}' não encontrada no SmartThings."
    ok = enviar_comando_device(device_id, "on", "switch")
    return f"Lâmpada '{label}' ligada." if ok else f"Falha ao ligar '{label}'."


def desligar_lampada(label: str) -> str:
    device_id = buscar_device_por_label(label)
    if not device_id:
        return f"Lâmpada '{label}' não encontrada no SmartThings."
    ok = enviar_comando_device(device_id, "off", "switch")
    return f"Lâmpada '{label}' apagada." if ok else f"Falha ao desligar '{label}'."


def ligar_todas_lampadas() -> str:
    devices = carregar_devices()
    ligadas = 0
    for d in devices:
        label = d.get("label", "").lower()
        if any(k in label for k in ("lamp", "luz", "light", "bulb", "led")):
            if enviar_comando_device(d["deviceId"], "on", "switch"):
                ligadas += 1
    return f"{ligadas} lâmpada(s) ligada(s)." if ligadas else "Nenhuma lâmpada encontrada no SmartThings."


def desligar_todas_lampadas() -> str:
    devices  = carregar_devices()
    apagadas = 0
    for d in devices:
        label = d.get("label", "").lower()
        if any(k in label for k in ("lamp", "luz", "light", "bulb", "led")):
            if enviar_comando_device(d["deviceId"], "off", "switch"):
                apagadas += 1
    return f"{apagadas} lâmpada(s) apagada(s)." if apagadas else "Nenhuma lâmpada encontrada."


def ajustar_brilho(label: str, nivel: int) -> str:
    device_id = buscar_device_por_label(label)
    if not device_id:
        return f"Lâmpada '{label}' não encontrada."
    ok = enviar_comando_device(device_id, "setLevel", "switchLevel", [nivel])
    return f"Brilho de '{label}' ajustado para {nivel}%." if ok else "Falha no brilho."


def listar_dispositivos() -> str:
    devices = carregar_devices(forcar=True)
    if not devices:
        return "Nenhum dispositivo encontrado no SmartThings."
    linhas = [
        f"• {d.get('label', d.get('name', 'Sem nome'))} (ID: {d['deviceId'][:8]}...)"
        for d in devices
    ]
    return "Dispositivos SmartThings:\n" + "\n".join(linhas[:20])