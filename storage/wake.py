import random
import re
import unicodedata

JARVIS_CANON = "jarvis"

SUBSTITUICOES_STT = (
    ("jarvus", "jarvis"),
    ("jervis", "jarvis"),
    ("garvis", "jarvis"),
    ("carvis", "jarvis"),
    ("harvis", "jarvis"),
    ("marvis", "jarvis"),
    ("barvis", "jarvis"),
    ("jarves", "jarvis"),
    ("jarvos", "jarvis"),
    ("javis", "jarvis"),
    ("jarviz", "jarvis"),
    ("jarviss", "jarvis"),
    ("jarvice", "jarvis"),
    ("yervis", "jarvis"),
    ("jerbis", "jarvis"),
    ("jarbis", "jarvis"),
    ("gervis", "jarvis"),
    ("jarv", "jarvis"),
    ("jarvi", "jarvis"),
    ("jevis", "jarvis"),
    ("jerviz", "jarvis"),
    ("jarvish", "jarvis"),
    ("sharvis", "jarvis"),
    ("yarvis", "jarvis"),
    ("jarvies", "jarvis"),
    ("jarvese", "jarvis"),
    ("djervis", "jarvis"),
    ("djavis", "jarvis"),
    ("dja vis", "jarvis"),
)

WAKE_WORDS = {
    "jarvis",
    "j.a.r.v.i.s",
    "jarvis ai",
    "jarvis aí",
    "ei jarvis",
    "hey jarvis",
    "hi jarvis",
    "oi jarvis",
    "ola jarvis",
    "ok jarvis",
    "yo jarvis",
    "e jarvis",
    "oh jarvis",
    "por favor jarvis",
    "fala jarvis",
    "me escuta jarvis",
    "escuta jarvis",
    "me ouve jarvis",
    "ouve jarvis",
    "me ouça jarvis",
    "ouça jarvis",
    "ativa jarvis",
    "ativar jarvis",
    "acorda jarvis",
    "acorde jarvis",
    "acorda",
    "acorde",
    "assistente",
    "modo escuta",
    "ativar sistema",
    "ola jer",
    "ola je",
    "ola jar",
    "ola j",
    "ei assistente",
    "hey assistente",
    "oi assistente",
    "e aí jarvis",
    "e ai jarvis",
    "eai jarvis",
    "bom dia jarvis",
    "boa tarde jarvis",
    "boa noite jarvis",
    "jar",
    "jers",
    "james",
    "jefferson",
    "germes",
    "jabes",
    "germe",
    "chaves",
    "chave",
    "jota",
    "jay",
    "jay vis",
    "jar viz",
    "jar is",
    "jarvis por favor",
    "jarvis favor",
    "jarvis meu",
    "meu jarvis",
    "chega jarvis",
    "psiu jarvis",
    "psst jarvis",
    "alô jarvis",
    "alo jarvis",
    "jarvis escuta",
    "jarvis ouve",
    "jarvis tá aí",
    "jarvis ta ai",
    "jarvis você",
    "jarvis voce",
    "jarvis preciso",
    "jarvis quero",
    "jarvis me",
    "jarvis um",
    "jarvis o",
    "jarvis a",
    "jarvis e",
    "charles",
}

COMANDOS_MONITORAMENTO = {
    "monitorar tela",
    "monitorar",
    "iniciar monitoramento",
    "ligar monitoramento",
    "ativar monitoramento",
    "monitorar sistema",
    "vigiar tela",
}

COMANDOS_PARAR_MONITOR = {
    "parar monitoramento",
    "desligar monitoramento",
    "desativar monitoramento",
    "parar monitor",
}

FRASES_FILME_JARVIS = [
    "Boa noite, senhor.",
    "Bem-vindo a casa, senhor.",
    "À sua disposição, senhor.",
    "Sim, senhor.",
    "Quer que eu faça o render com as especificações propostas?",
    "Fui carregado de facto, senhor. Estamos online e prontos.",
    "Bom dia, senhor.",
    "É bom estar de volta, senhor.",
    "Estamos a trabalhar num projeto secreto, não estamos, senhor?",
    "A iniciar a montagem, senhor.",
    "Senhor, respire fundo.",
    "O protocolo Tábua Rasa, senhor.",
    "Senhor, o agente Coulson da S.H.I.E.L.D. está na linha.",
    "Violação de segurança, senhor.",
    "Potência a quatrocentos por cento de capacidade, senhor.",
    "Desativei os protocolos de segurança, senhor.",
    "Quer que eu inicie o passeio virtual?",
    "Tomei a liberdade de programar uma simulação virtual, senhor.",
    "A iniciar a calibração, senhor.",
    "Condições de surf razoáveis, senhor.",
    "Neve quente, senhor. Eu sei o que isso significa.",
]


def resposta_ativacao_aleatoria() -> str:
    return random.choice(FRASES_FILME_JARVIS)


def normalizar_frase(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[.,!?;:'\"-]", "", texto)
    texto = re.sub(r"(hey|hi|ei|yo|ok|oi|ola|eai|boa)(jarvis)", r"\1 \2", texto)
    texto = re.sub(r"jarvis([a-z])", r"jarvis \1", texto)
    texto = re.sub(r"\s+", " ", texto)
    for err, ok in SUBSTITUICOES_STT:
        texto = texto.replace(err, ok)
    return texto


def distancia_edicao(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 4:
        return 99
    if len(a) == 0:
        return len(b)
    if len(b) == 0:
        return len(a)

    linha_anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        linha_atual = [i + 1]
        for j, cb in enumerate(b):
            insercao = linha_anterior[j + 1] + 1
            delecao = linha_atual[j] + 1
            substituicao = linha_anterior[j] + (0 if ca == cb else 1)
            linha_atual.append(min(insercao, delecao, substituicao))
        linha_anterior = linha_atual

    return linha_anterior[len(b)]


def parece_palavra_wake(token: str) -> bool:
    if not token:
        return False
    t = token.strip(".")
    if len(t) >= 4 and len(t) <= 9:
        if distancia_edicao(t, JARVIS_CANON) <= 2:
            return True
    for wake in WAKE_WORDS:
        if len(wake) <= 3:
            if t == wake:
                return True
            continue
        if distancia_edicao(t, wake) <= 1:
            return True
    return False


def frase_tem_jarvis_isolado(frase: str) -> bool:
    if JARVIS_CANON in frase:
        padrao = r"(^|\s)" + re.escape(JARVIS_CANON) + r"($|\s)"
        return re.search(padrao, frase) is not None
    return False


def processar_wake(texto: str) -> tuple[bool, str]:
    if not texto:
        return False, ""

    frase = normalizar_frase(texto)

    for cmd in sorted(COMANDOS_MONITORAMENTO, key=len, reverse=True):
        cmd_n = normalizar_frase(cmd)
        if cmd_n in frase:
            return True, frase

    for cmd in sorted(COMANDOS_PARAR_MONITOR, key=len, reverse=True):
        cmd_n = normalizar_frase(cmd)
        if cmd_n in frase:
            return True, frase

    for wake in sorted(WAKE_WORDS, key=len, reverse=True):
        wake_n = normalizar_frase(wake)
        if not wake_n:
            continue
        if frase == wake_n:
            return True, ""
        if frase.startswith(wake_n + " "):
            comando = frase[len(wake_n) + 1 :].strip()
            return True, comando

    if frase_tem_jarvis_isolado(frase):
        partes = frase.split(JARVIS_CANON)
        if len(partes) >= 2:
            antes = partes[0].strip()
            depois = JARVIS_CANON.join(partes[1:]).strip()
            if depois:
                return True, depois
            if antes:
                return True, antes
            return True, ""

    tokens = frase.split()
    for i, tok in enumerate(tokens):
        if parece_palavra_wake(tok):
            comando = " ".join(tokens[i + 1 :]).strip()
            return True, comando

    return False, ""


def e_comando_monitoramento(texto: str) -> bool:
    frase = normalizar_frase(texto)
    for cmd in COMANDOS_MONITORAMENTO:
        if normalizar_frase(cmd) in frase:
            return True
    return False


def e_comando_parar_monitor(texto: str) -> bool:
    frase = normalizar_frase(texto)
    for cmd in COMANDOS_PARAR_MONITOR:
        if normalizar_frase(cmd) in frase:
            return True
    return False
