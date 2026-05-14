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
        res = requests.post(
            f"{API_BASE}/{endpoint}",
            headers=montar_headers(),
            json=payload,
            timeout=8,
        )
        if 200 <= res.status_code < 300:
            return True
        return False
    except Exception:
        return False

def solicitar_ha(endpoint: str) -> dict | None:
    ha_url = getattr(config, "HOME_ASSISTANT_URL", "")
    ha_token = getattr(config, "HOME_ASSISTANT_TOKEN", "")
    if not ha_url or not ha_token:
        return None
    try:
        head = {"Authorization": f"Bearer {ha_token}", "Content-Type": "application/json"}
        res = requests.get(f"{ha_url}/api/{endpoint}", headers=head, timeout=8)
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None

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

def buscar_device_por_label(label_busca: str) -> str | None:
    label_busca = label_busca.lower().strip()
    for device in carregar_devices():
        label = device.get("label", "").lower()
        name = device.get("name", "").lower()
        if label_busca in label or label_busca in name:
            return device["deviceId"]
    return None

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
            "capability": capacidade,
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
    if "hub" in label and "tv" not in label and "televis" not in label and "qled" not in label:
        if not any(p in blob for p in PISTAS_TV):
            return 0
    for ex in EXCLUIR_TIPO:
        if ex in label or ex in name:
            if "tv" not in blob and "televis" not in blob and "qled" not in blob and "samsung" not in dtype:
                return 0
    score = 0
    for p in PISTAS_TV:
        if p in blob:
            score += 12 if p == "tv" else 8
    if "samsung" in name or "samsung" in label:
        score += 4
    if "televis" in label or "televis" in name or "televis" in dtype:
        score += 16
    if "tv" in label.split() or f" {name} ".find(" tv ") >= 0 or name.endswith(" tv") or name.startswith("tv "):
        score += 10
    if "television" in dtype or "tv" in dtype:
        score += 14
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
    return (
        "O monitor do sistema indica que a TV está offline na rede SmartThings. "
        f"Aparelhos detectados agora: {gerar_amostra_devices(6)}"
    )


def buscar_id_tv(forcar: bool = False) -> str | None:
    global tv_id_cache
    if forcar:
        tv_id_cache = None
    manual = getattr(config, "SMARTTHINGS_TV_DEVICE_ID", "") or ""
    manual = str(manual).strip()
    if manual:
        return manual
    if tv_id_cache and not forcar:
        return tv_id_cache
    devices = carregar_devices(forcar)
    if not devices:
        return None
    best_id: str | None = None
    best = 0
    for device in devices:
        sc = calcular_pontuacao_tv(device)
        if sc > best:
            best = sc
            best_id = device.get("deviceId")
    if best_id and best >= 8:
        tv_id_cache = best_id
        return tv_id_cache
    
    for device in devices:
        label = remover_acentos(device.get("label", ""))
        name = remover_acentos(device.get("name", ""))
        if "hub" not in label and ("[tv]" in label or "[tv]" in name):
            tv_id_cache = device["deviceId"]
            return tv_id_cache
    return None

def energia_tv(ligar: bool) -> bool:
    device_id = buscar_id_tv()
    if not device_id:
        return False
    on = "on" if ligar else "off"
    sequencia: list[tuple[str, str, list]] = [
        (on, "switch", []),
        (on, "samsungce.power", []),
    ]
    for comando, cap, args in sequencia:
        if enviar_comando_device(device_id, comando, cap, args):
            return True
    return False


def enviar_comando_tv(comando: str, capacidade: str, argumentos: list | None = None) -> bool:
    device_id = buscar_id_tv()
    if not device_id:
        return False
    return enviar_comando_device(device_id, comando, capacidade, argumentos)


def ligar_tv() -> bool:
    return energia_tv(True)

def desligar_tv() -> bool:
    return energia_tv(False)

def ajustar_volume_tv(nivel: int) -> bool:
    nivel = max(0, min(100, nivel))
    return enviar_comando_tv("setVolume", "audioVolume", [nivel])


def verificar_luz_acesa(dados: dict) -> bool | None:
    if not dados:
        return None
    sw = (
        dados.get("components", {})
        .get("main", {})
        .get("switch", {})
        .get("switch", {})
    )
    if not isinstance(sw, dict):
        return None
    v = str(sw.get("value", "")).lower()
    if v in ("on", "off"):
        return v == "on"
    return None




def abrir_youtube_tv() -> str:
    device_id = buscar_id_tv(True)
    if not device_id:
        return diagnosticar_falha_tv()
    st = solicitar_api(f"devices/{device_id}/status")
    on = verificar_luz_acesa(st) if st else None
    if on is False:
        if not energia_tv(True):
            return "Comando negado pois a TV encontra-se sem energia contínua."
    yids = ("org.tizen.youtube", "YouTube", "111299001912")
    for yid in yids:
        if enviar_comando_device(device_id, "openApp", "samsungce.appControl", [yid]):
            return "YouTube inicializado na TV."
    for yid in yids:
        if enviar_comando_device(device_id, "open", "samsungim.launcher", [yid]):
            return "YouTube inicializado na TV via protocolo legado."
    return "A TV existe, mas rejeitou a execução do App."

def status_tv() -> str:
    device_id = buscar_id_tv()
    if not device_id:
        return diagnosticar_falha_tv()
    dados = solicitar_api(f"devices/{device_id}/status")
    if not dados:
        return "Conexão de diagnóstico falhou."
    sw = (
        dados.get("components", {})
        .get("main", {})
        .get("switch", {})
        .get("switch", {})
    )
    if isinstance(sw, dict) and "value" in sw:
        estado = str(sw.get("value", "desconhecido")).upper()
        return f"A TV reporta estado: {estado}."
    return "Dispositivo presente, porém silencioso quanto à energia."


def listar_dispositivos() -> str:
    devices = carregar_devices(forcar=True)
    if not devices:
        return "Radar limpo. Sem dispositivos encontrados."
    linhas = [
        f"• {d.get('label', d.get('name', 'Sem nome'))} (ID: {d['deviceId'][:8]}...)"
        for d in devices
    ]
    return "Acesso aos dispositivos:\n" + "\n".join(linhas[:20])