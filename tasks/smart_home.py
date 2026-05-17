import time
import requests
import config
import logging

log = logging.getLogger("CORE.smartthings")

API_BASE = "https://api.smartthings.com/v1"
DEVICES_TTL = 60
tv_id_cache: str | None = None
devices_cache: list | None = None
devices_cache_ts: float = 0.0

PISTAS_TV = (
    "tv", "televis", "qled", "oled", "the frame", "crystal uhd",
    "neo qled", "smart tv", "4k uhd", "8k", "tizen", "uhd",
)

EXCLUIR_TIPO = (
    "sensor", "motion", "button", "tag", "lock", "thermostat",
    "temp", "vibration", "moisture", "siren", "dimmer",
)


def remover_acentos(s: str) -> str:
    t = (s or "").lower()
    for src, dst in [("ã", "a"), ("â", "a"), ("á", "a"), ("à", "a"), ("ê", "e"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("õ", "o"), ("ú", "u"), ("ç", "c")]:
        t = t.replace(src, dst)
    return t


def montar_headers() -> dict:
    return {"Authorization": f"Bearer {config.SMARTTHINGS_TOKEN}"}


def solicitar_api(endpoint: str) -> dict | None:
    if not config.SMARTTHINGS_TOKEN:
        return None
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", headers=montar_headers(), timeout=8)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None


def enviar_post(endpoint: str, payload: list) -> bool:
    if not config.SMARTTHINGS_TOKEN:
        return False
    try:
        res = requests.post(f"{API_BASE}/{endpoint}", headers=montar_headers(), json=payload, timeout=8)
        return 200 <= res.status_code < 300
    except Exception:
        return False


def carregar_devices(forcar: bool = False) -> list:
    global devices_cache, devices_cache_ts
    agora = time.time()
    if devices_cache and not forcar and (agora - devices_cache_ts) < DEVICES_TTL:
        return devices_cache
    dados = solicitar_api("devices")
    if not dados:
        return devices_cache or []
    devices_cache = dados.get("items", [])
    devices_cache_ts = agora
    return devices_cache


def enviar_comando_device(
    device_id: str,
    comando: str,
    capacidade: str,
    argumentos: list | None = None,
    component: str = "main",
) -> bool:
    payload = [
        {
            "component": component,
            "command": comando,
            "arguments": argumentos or [],
        }
    ]
    return enviar_post(f"devices/{device_id}/commands", payload)


def calcular_pontuacao_tv(device: dict) -> int:
    label = remover_acentos(device.get("label", ""))
    name = remover_acentos(device.get("name", ""))
    dtype = remover_acentos(str(device.get("deviceTypeName", "") or device.get("type", "") or ""))
    blob = f"{label} {name} {dtype}"
    if "hub" in label and "tv" not in label and "televis" not in label:
        return 0
    for ex in EXCLUIR_TIPO:
        if ex in label or ex in name:
            if "tv" not in blob and "samsung" not in dtype:
                return 0
    score = 0
    for p in PISTAS_TV:
        if p in blob:
            score += 12 if p == "tv" else 8
    if "samsung" in name or "samsung" in label:
        score += 4
    return score


def gerar_amostra_devices(n: int = 5) -> str:
    try:
        nomes: list[str] = []
        for d in carregar_devices(True)[:25]:
            nomes.append(d.get("label") or d.get("name") or "?")
        if not nomes:
            return "(nenhum listado)"
        return ", ".join(nomes[:n]) + ("…" if len(nomes) > n else "")
    except Exception:
        return "(erro amostra)"


def diagnosticar_falha_tv() -> str:
    return f"A TV está offline na rede SmartThings. Aparelhos detectados agora: {gerar_amostra_devices(6)}"


def buscar_id_tv(forcar: bool = False) -> str | None:
    global tv_id_cache
    if forcar:
        tv_id_cache = None
    manual = str(getattr(config, "SMARTTHINGS_TV_DEVICE_ID", "")).strip()
    if manual:
        return manual
    if tv_id_cache and not forcar:
        return tv_id_cache
    devices = carregar_devices(forcar)
    best_id, best = None, 0
    for device in devices:
        sc = calcular_pontuacao_tv(device)
        if sc > best:
            best, best_id = sc, device.get("deviceId")
    if best_id and best >= 8:
        tv_id_cache = best_id
        return tv_id_cache
    return None


def energia_tv(ligar: bool) -> bool:
    device_id = buscar_id_tv()
    if not device_id:
        return False
    on = "on" if ligar else "off"
    for comando, cap in [("switch", "switch"), ("switch", "samsungce.power")]:
        if enviar_comando_device(device_id, comando, cap, []):
            return True
    return False


def ligar_tv() -> bool:
    return energia_tv(True)


def desligar_tv() -> bool:
    """Alias explícito — usado em controller.py."""
    return energia_tv(False)


def enviar_comando_tv(
    comando: str,
    capacidade: str,
    argumentos: list | None = None,
) -> bool:
    """Wrapper de conveniência que resolve o device_id da TV automaticamente."""
    device_id = buscar_id_tv()
    if not device_id:
        return False
    return enviar_comando_device(device_id, comando, capacidade, argumentos)


def abrir_youtube_tv() -> str:
    """Abre o aplicativo do YouTube na TV Samsung via SmartThings."""
    device_id = buscar_id_tv()
    if not device_id:
        return diagnosticar_falha_tv()
    # Tenta via mediaPlayback / applicationId; fallback por inputSource
    tentativas = [
        ("setInputSource", "mediaInputSource", ["YouTube"]),
        ("launchApp",      "samsungce.appIdentification", ["com.samsung.app.livetv.youtube"]),
    ]
    for cmd, cap, args in tentativas:
        if enviar_comando_device(device_id, cmd, cap, args):
            return "YouTube aberto na TV, Senhor."
    return "Não consegui abrir o YouTube na TV. Verifique se o app está instalado."


def status_tv() -> str:
    device_id = buscar_id_tv()
    if not device_id:
        return diagnosticar_falha_tv()
    dados = solicitar_api(f"devices/{device_id}/status")
    if not dados:
        return "Conexão de diagnóstico falhou."
    sw = dados.get("components", {}).get("main", {}).get("switch", {}).get("switch", {})
    if isinstance(sw, dict) and "value" in sw:
        return f"A TV reporta estado: {str(sw.get('value')).upper()}."
    return "Dispositivo presente, porém silencioso quanto à energia."