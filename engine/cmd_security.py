from __future__ import annotations

import re
import shlex
import subprocess
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

log = logging.getLogger("jarvis.cmd_security")







class Categoria(Enum):
    LEITURA    = "leitura"
    SISTEMA    = "sistema"
    REDE       = "rede"
    DESTRUTIVO = "destrutivo"
    BLOQUEADO  = "bloqueado"







@dataclass
class Regra:
    padrao:    re.Pattern
    categoria: Categoria
    shell:     bool = False







@dataclass
class Avaliacao:
    permitido: bool
    confirmar: bool      = False
    categoria: Categoria = Categoria.BLOQUEADO
    motivo:    str       = ""
    cmd:       Optional[str] = None

BLOQUEIOS = [
    r"rm\s+-rf\s+[/~\$]",
    r"mkfs", r"dd\s+if=",
    r":\(\)\{.*\}",
    r"chmod\s+-R\s+777\s+/",
    r"(wget|curl).+\|\s*(bash|sh|python)",
    r">\s*/dev/sda",
    r"format\s+c:", r"del\s+/f\s+/s\s+/q\s+[cC]:",
    r"rd\s+/s\s+/q\s+[cC]:\\",
    r"Remove-Item\s+-Recurse\s+-Force\s+[cC]:",
    r"shutdown\s+/[fsr]",
    r"\b(halt|poweroff|reboot)\b",
    r"systemctl\s+(halt|poweroff|reboot)",
    r"__import__", r"eval\s*\(", r"exec\s*\(",
    r"base64\s+-d.*\|\s*(bash|sh)",
    r"nc\s+-[el]", r"netcat",
    r"/etc/(passwd|shadow)",
    r"sudo\s+(su|-s)",
]

REGRAS: list[Regra] = [
    Regra(re.compile(r"^(ls|dir|echo|pwd|whoami|date|uptime|df|du|free|ps|top|cat\s+\S+\.(txt|log|json)|type\s+\S+)"), Categoria.LEITURA),
    Regra(re.compile(r"^(python3?|node|npm|pip)\s+"),              Categoria.SISTEMA),
    Regra(re.compile(r"^(mkdir|touch|cp|mv)\s+"),                  Categoria.SISTEMA),
    Regra(re.compile(r"^(ping|nslookup|curl\s+https?://|wget\s+https?://)\s+"), Categoria.REDE),
    Regra(re.compile(r"^(tasklist|taskkill|Get-Process|Stop-Process|systemctl\s+status|service\s+\S+\s+status)"), Categoria.SISTEMA, shell=True),
    Regra(re.compile(r"^(rm|del|rmdir|rd|Remove-Item|shred)\s+"),  Categoria.DESTRUTIVO, shell=True),
    Regra(re.compile(r"^(kill|taskkill\s+/f|Stop-Process\s+-Force)\s+"), Categoria.DESTRUTIVO, shell=True),
    Regra(re.compile(r"^(pip\s+install|npm\s+install|apt\s+install|brew\s+install|winget\s+install)"), Categoria.SISTEMA, shell=True),
    Regra(re.compile(r"^(powershell|cmd|bash|sh|zsh|fish)\s+"),    Categoria.SISTEMA, shell=True),
    Regra(re.compile(r"^(netsh|iptables|ufw|firewall-cmd)\s+"),    Categoria.DESTRUTIVO, shell=True),
    Regra(re.compile(r"^(reg\s+|regedit|regedt32)"),               Categoria.DESTRUTIVO, shell=True),
]

BLOQUEIOS_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in BLOQUEIOS]
INJECOES             = [";", "&&", "||", "`", "$(", ">{", "<(", "2>&1 |"]







def sanitizar(cmd: str) -> str:
    return re.sub(r"\s+", " ", cmd.strip())







def tem_injecao(cmd: str) -> bool:
    return any(s in cmd.lower() for s in INJECOES)







def avaliar(comando: str) -> Avaliacao:
    cmd = sanitizar(comando)

    if not cmd:
        return Avaliacao(permitido=False, motivo="Comando vazio.")

    for padrao in BLOQUEIOS_COMPILADOS:
        if padrao.search(cmd):
            log.warning("Bloqueado: %s", cmd[:80])
            return Avaliacao(permitido=False, motivo="Padrão proibido detectado.")

    if tem_injecao(cmd):
        log.warning("Injeção detectada: %s", cmd[:80])
        return Avaliacao(permitido=False, motivo="Operadores de encadeamento suspeitos (;, &&, ||).")

    for regra in REGRAS:
        if regra.padrao.match(cmd):
            return Avaliacao(
                permitido=True,
                confirmar=regra.categoria == Categoria.DESTRUTIVO,
                categoria=regra.categoria,
                cmd=cmd,
            )

    return Avaliacao(
        permitido=True,
        confirmar=True,
        categoria=Categoria.SISTEMA,
        cmd=cmd,
        motivo="Comando não catalogado.",
    )







def executar(comando: str, timeout: int = 15, confirmar_fn: Optional[Callable] = None) -> str:
    av = avaliar(comando)

    if not av.permitido:
        return f"Bloqueado: {av.motivo}"

    if av.confirmar:
        if confirmar_fn is None:
            return (
                f"Comando '{av.categoria.value}' requer confirmação.\n"
                f"Use: executar_confirmado('{comando}')"
            )
        if not confirmar_fn(comando, av):
            return "Execução cancelada."

    cmd        = av.cmd or comando
    usar_shell = any(r.shell and r.padrao.match(cmd) for r in REGRAS)

    try:
        if usar_shell:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            try:
                args = shlex.split(cmd)
            except ValueError:
                args = cmd.split()
            res = subprocess.run(args, shell=False, capture_output=True, text=True, timeout=timeout)

        saida = (res.stdout or res.stderr or "Executado sem saída.").strip()
        if res.returncode != 0:
            log.warning("Código %d: %s", res.returncode, cmd[:60])
        return saida[:600]

    except subprocess.TimeoutExpired:
        return f"Timeout: excedeu {timeout}s."
    except FileNotFoundError as e:
        return f"Comando não encontrado: {e}"
    except Exception as e:
        log.error("Erro ao executar '%s': %s", cmd[:60], e)
        return f"Erro: {e}"

avaliar_comando  = avaliar
executar_seguro  = executar