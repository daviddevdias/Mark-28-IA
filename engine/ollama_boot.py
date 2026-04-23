import subprocess
import requests
import time


def iniciar_ollama():
    try:
        requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        print("[OLLAMA] Servico ja estava ativo.")
        return True
    except Exception:
        pass

    print("[OLLAMA] Iniciando servico...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for i in range(10):
        time.sleep(1)
        try:
            requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            print("[OLLAMA] Online.")
            return True
        except Exception:
            pass

    print("[OLLAMA] AVISO: servico nao respondeu apos 10s. IA pode ficar muda.")
    return False