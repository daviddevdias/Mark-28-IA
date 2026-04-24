import re
import random
import unicodedata


WAKE_WORDS = {
    "jarvis", "core", "assistente", "acorda", "acorde",
    "modo escuta", "ativar sistema", "ei jarvis", "hey jarvis",
    "ola jer", "ola je", "ola jar", "jar", "jers", "james",
    "ola jarvis", "jefferson", "germes", "jabes", "germe",
    "chaves", "chave", "j", "jota",
}

COMANDOS_MONITORAMENTO = {
    "monitorar tela", "monitorar", "iniciar monitoramento",
    "ligar monitoramento", "ativar monitoramento",
    "monitorar sistema", "vigiar tela",
}

COMANDOS_PARAR_MONITOR = {
    "parar monitoramento", "desligar monitoramento",
    "desativar monitoramento", "parar monitor",
}

RESPOSTAS_ATIVACAO = [
    "Sim, senhor. Estou disponível.",
    "Às suas ordens, David.",
    "Sistema ativo. Como posso ajudar?",
    "Online e aguardando comandos.",
    "Jarvis operacional. Diga.",
    "Protocolos ativos. O que precisa?",
    "Aqui, senhor.",
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[.,!?;:'\"-]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _distancia_levenshtein(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 3:
        return 99
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    linha_anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        linha_atual = [i + 1]
        for j, cb in enumerate(b):
            insercao  = linha_anterior[j + 1] + 1
            delecao   = linha_atual[j] + 1
            substituicao = linha_anterior[j] + (0 if ca == cb else 1)
            linha_atual.append(min(insercao, delecao, substituicao))
        linha_anterior = linha_atual

    return linha_anterior[len(b)]


def _e_wake_fuzzy(token: str) -> bool:
    for wake in WAKE_WORDS:
        if len(wake) <= 3:
            if token == wake:
                return True
            continue
        if _distancia_levenshtein(token, wake) <= 1:
            return True
    return False


def processar_wake(texto: str) -> tuple[bool, str]:
    if not texto:
        return False, ""

    frase = _normalizar(texto)

    for cmd in sorted(COMANDOS_MONITORAMENTO, key=len, reverse=True):
        cmd_n = _normalizar(cmd)
        if cmd_n in frase:
            return True, frase

    for cmd in sorted(COMANDOS_PARAR_MONITOR, key=len, reverse=True):
        cmd_n = _normalizar(cmd)
        if cmd_n in frase:
            return True, frase

    for wake in sorted(WAKE_WORDS, key=len, reverse=True):
        wake_n = _normalizar(wake)
        if frase == wake_n:
            return True, random.choice(RESPOSTAS_ATIVACAO)
        if frase.startswith(wake_n + " "):
            comando = frase[len(wake_n):].strip()
            return True, (comando if comando else random.choice(RESPOSTAS_ATIVACAO))

    tokens = frase.split()
    for i, tok in enumerate(tokens):
        if _e_wake_fuzzy(tok):
            comando = " ".join(tokens[i + 1:]).strip()
            return True, (comando if comando else random.choice(RESPOSTAS_ATIVACAO))

    return False, ""


def e_comando_monitoramento(texto: str) -> bool:
    frase = _normalizar(texto)
    for cmd in COMANDOS_MONITORAMENTO:
        if _normalizar(cmd) in frase:
            return True
    return False


def e_comando_parar_monitor(texto: str) -> bool:
    frase = _normalizar(texto)
    for cmd in COMANDOS_PARAR_MONITOR:
        if _normalizar(cmd) in frase:
            return True
    return False