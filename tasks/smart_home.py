import requests
import config
import logging

log = logging.getLogger("CORE.smartthings")


_API_BASE = "https://api.smartthings.com/v1"
_tv_id_cache: str | None = None
_devices_cache: list | None = None







def _headers() -> dict:
    return {"Authorization": f"Bearer {config.SMARTTHINGS_TOKEN}"}


def _get(endpoint: str) -> dict | None:
    if not config.SMARTTHINGS_TOKEN:
        log.error("Token SmartThings não configurado.")
        return None

    try:
        res = requests.get(f"{_API_BASE}/{endpoint}", headers=_headers(), timeout=8)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        log.error("GET %s: %s", endpoint, e)
        return None


def _post(endpoint: str, payload: list) -> bool:
    if not config.SMARTTHINGS_TOKEN:
        return False

    try:
        res = requests.post(
            f"{_API_BASE}/{endpoint}",
            headers=_headers(),
            json=payload,
            timeout=8,
        )
        return res.status_code == 200
    except Exception as e:
        log.error("POST %s: %s", endpoint, e)
        return False







def _carregar_devices(forcar: bool = False) -> list:
    global _devices_cache

    if _devices_cache and not forcar:
        return _devices_cache

    dados = _get("devices")

    if not dados:
        return []

    _devices_cache = dados.get("items", [])
    return _devices_cache


def _buscar_device_por_label(label_busca: str) -> str | None:
    label_busca = label_busca.lower().strip()

    for device in _carregar_devices():
        label = device.get("label", "").lower()
        name = device.get("name", "").lower()

        if label_busca in label or label_busca in name:
            return device["deviceId"]

    return None







def enviar_comando_device(
    device_id: str, comando: str, capacidade: str, argumentos: list | None = None
) -> bool:

    payload = [
        {
            "component": "main",
            "capability": capacidade,
            "command": comando,
            "arguments": argumentos or [],
        }
    ]

    ok = _post(f"devices/{device_id}/commands", payload)

    log.info(
        "Comando '%s' → device %s: %s", comando, device_id[:8], "OK" if ok else "FALHOU"
    )

    return ok







def buscar_id_tv(forcar: bool = False) -> str | None:
    global _tv_id_cache

    if _tv_id_cache and not forcar:
        return _tv_id_cache

    for device in _carregar_devices(forcar):
        label = device.get("label", "").lower()
        name = device.get("name", "").lower()

        if "hub" not in label and (
            "tv" in label or "samsung" in name or "[tv]" in label
        ):
            _tv_id_cache = device["deviceId"]
            return _tv_id_cache

    log.warning("Nenhuma TV Samsung encontrada.")
    return None


def enviar_comando_tv(
    comando: str, capacidade: str, argumentos: list | None = None
) -> bool:
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

    dados = _get(f"devices/{device_id}/status")

    if not dados:
        return "Não foi possível obter o status da TV."

    switch = (
        dados.get("components", {}).get("main", {}).get("switch", {}).get("switch", {})
    )
    estado = switch.get("value", "desconhecido")

    return f"TV Samsung: {estado.upper()}"







def ligar_lampada(label: str) -> str:
    device_id = _buscar_device_por_label(label)

    if not device_id:
        return f"Lâmpada '{label}' não encontrada no SmartThings."

    ok = enviar_comando_device(device_id, "on", "switch")

    return f"Lâmpada '{label}' ligada." if ok else f"Falha ao ligar '{label}'."


def desligar_lampada(label: str) -> str:
    device_id = _buscar_device_por_label(label)

    if not device_id:
        return f"Lâmpada '{label}' não encontrada no SmartThings."

    ok = enviar_comando_device(device_id, "off", "switch")

    return f"Lâmpada '{label}' apagada." if ok else f"Falha ao desligar '{label}'."


def ligar_todas_lampadas() -> str:
    devices = _carregar_devices()

    ligadas = 0

    for d in devices:
        label = d.get("label", "").lower()

        if any(k in label for k in ("lamp", "luz", "light", "bulb", "led")):
            if enviar_comando_device(d["deviceId"], "on", "switch"):
                ligadas += 1

    return (
        f"{ligadas} lâmpada(s) ligada(s)."
        if ligadas
        else "Nenhuma lâmpada encontrada no SmartThings."
    )


def desligar_todas_lampadas() -> str:
    devices = _carregar_devices()

    apagadas = 0

    for d in devices:
        label = d.get("label", "").lower()

        if any(k in label for k in ("lamp", "luz", "light", "bulb", "led")):
            if enviar_comando_device(d["deviceId"], "off", "switch"):
                apagadas += 1

    return (
        f"{apagadas} lâmpada(s) apagada(s)."
        if apagadas
        else "Nenhuma lâmpada encontrada."
    )


def ajustar_brilho(label: str, nivel: int) -> str:
    device_id = _buscar_device_por_label(label)

    if not device_id:
        return f"Lâmpada '{label}' não encontrada."

    ok = enviar_comando_device(device_id, "setLevel", "switchLevel", [nivel])

    return (
        f"Brilho de '{label}' ajustado para {nivel}%." if ok else "Falha no brilho."
    )


def listar_dispositivos() -> str:
    devices = _carregar_devices(forcar=True)

    if not devices:
        return "Nenhum dispositivo encontrado no SmartThings."

    linhas = [
        f"• {d.get('label', d.get('name', 'Sem nome'))} (ID: {d['deviceId'][:8]}...)"
        for d in devices
    ]

    return "Dispositivos SmartThings:\n" + "\n".join(linhas[:20])