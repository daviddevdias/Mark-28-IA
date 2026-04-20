import subprocess
import requests
import time


def iniciar_ollama():
    try:
        requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        return
    except:
        pass

    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    for _ in range(10):
        try:
            requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            return
        except:
            time.sleep(1)