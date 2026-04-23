import subprocess
import requests
import time
import asyncio


def iniciar_ollama() -> bool:
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        modelos = [m["name"] for m in r.json().get("models", [])]
        print(f"[OLLAMA] Servico ja ativo. Modelos: {modelos}")
        return True
    except Exception:
        pass

    print("[OLLAMA] Iniciando servico...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(15):
        time.sleep(1)
        try:
            r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            modelos = [m["name"] for m in r.json().get("models", [])]
            if modelos:
                print(f"[OLLAMA] Online. Modelos: {modelos}")
            else:
                print("[OLLAMA] Online mas sem modelos. Rode: ollama pull llama3.2")
            return True
        except Exception:
            pass

    print("[OLLAMA] AVISO: servico nao respondeu apos 15s.")
    return False