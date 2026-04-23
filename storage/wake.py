import re
import random

WAKE_WORDS = {
    "jarvis", "core", "assistente", "acorda", "acorde",
    "modo escuta", "ativar sistema", "ei jarvis", "hey jarvis",
    "ola jer", "ola je", "ola jar", "jar", "jers", "james",
    "ola jarvis", "jefferson", "germes", "jabes", "germe",
    "chaves", "chave",
}

RESPOSTAS_ATIVACAO = [
    "Sim, senhor. Estou disponível.",
    "Às suas ordens, David.",
    "Sistema ativo. Como posso ajudar?",
    "Online e aguardando comandos.",
    "Jarvis operacional. Diga.",
]


def processar_wake(texto: str) -> tuple[bool, str]:
    if not texto:
        return False, ""

    frase_limpa = re.sub(r"[.,!?]", "", texto.lower()).strip()

    if frase_limpa in WAKE_WORDS:
        return True, random.choice(RESPOSTAS_ATIVACAO)

    for word in sorted(WAKE_WORDS, key=len, reverse=True):
        if frase_limpa.startswith(word):
            comando = frase_limpa.replace(word, "", 1).strip()
            return True, (comando if comando else random.choice(RESPOSTAS_ATIVACAO))

    return False, ""