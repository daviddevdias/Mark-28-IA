from __future__ import annotations

import re
import shlex
import subprocess
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

log = logging.getLogger("jarvis.cmd_security")







class CmdCategoria(Enum):
    LEITURA = "leitura"
    SISTEMA = "sistema"
    REDE = "rede"
    DESTRUTIVO = "destrutivo"
    BLOQUEADO = "bloqueado"







@dataclass
class RegraCmd:
    padrao: re.Pattern
    categoria: CmdCategoria
    shell_permitido: bool = False
    descricao: str = ""







@dataclass
class ResultadoSeguranca:
    permitido: bool
    requer_confirmacao: bool = False
    categoria: CmdCategoria = CmdCategoria.BLOQUEADO
    motivo: str = ""
    comando_sanitizado: Optional[str] = None

_BLOQUEADOS_ABSOLUTOS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\$HOME",
    r"mkfs",
    r"dd\s+if=",
    r":\(\)\{.*\}",
    r"chmod\s+-R\s+777\s+/",
    r"wget.+\|\s*(bash|sh|python)",
    r"curl.+\|\s*(bash|sh|python)",
    r">\s*/dev/sda",
    r"format\s+c:",
    r"del\s+/f\s+/s\s+/q\s+[cC]:",
    r"rd\s+/s\s+/q\s+[cC]:\\",
    r"Remove-Item\s+-Recurse\s+-Force\s+[cC]:",
    r"shutdown\s+/[fsr]",
    r"halt\b",
    r"poweroff\b",
    r"reboot\b",
    r"systemctl\s+(halt|poweroff|reboot)",
    r"import\s+os.*system",
    r"__import__",
    r"eval\s*\(",
    r"exec\s*\(",
    r"base64\s+-d.*\|\s*(bash|sh)",
    r"nc\s+-[el]",
    r"netcat",
    r"/etc/passwd",
    r"/etc/shadow",
    r"sudo\s+su",
    r"sudo\s+-s",
]

_REGRAS: list[RegraCmd] = [
    RegraCmd(re.compile(r"^(ls|dir|echo|pwd|whoami|date|uptime|df|du|free|ps|top|cat\s+\S+\.txt|cat\s+\S+\.log|cat\s+\S+\.json|type\s+\S+)"), CmdCategoria.LEITURA, shell_permitido=False, descricao="leitura segura"),
    RegraCmd(re.compile(r"^(python|python3|node|npm|pip)\s+"), CmdCategoria.SISTEMA, shell_permitido=False, descricao="runtime"),
    RegraCmd(re.compile(r"^(mkdir|touch|cp|mv)\s+"), CmdCategoria.SISTEMA, shell_permitido=False, descricao="manipulação de arquivos"),
    RegraCmd(re.compile(r"^(ping|nslookup|curl\s+https?://|wget\s+https?://)\s+"), CmdCategoria.REDE, shell_permitido=False, descricao="rede básica"),
    RegraCmd(re.compile(r"^(tasklist|taskkill|Get-Process|Stop-Process|systemctl\s+status|service\s+\S+\s+status)"), CmdCategoria.SISTEMA, shell_permitido=True, descricao="processos"),
    RegraCmd(re.compile(r"^(rm|del|rmdir|rd|Remove-Item|shred)\s+"), CmdCategoria.DESTRUTIVO, shell_permitido=True, descricao="remoção de arquivos"),
    RegraCmd(re.compile(r"^(kill|taskkill\s+/f|Stop-Process\s+-Force)\s+"), CmdCategoria.DESTRUTIVO, shell_permitido=True, descricao="encerrar processo"),
    RegraCmd(re.compile(r"^(pip\s+install|npm\s+install|apt\s+install|brew\s+install|winget\s+install)"), CmdCategoria.SISTEMA, shell_permitido=True, descricao="instalação de pacotes"),
    RegraCmd(re.compile(r"^(powershell|cmd|bash|sh|zsh|fish)\s+"), CmdCategoria.SISTEMA, shell_permitido=True, descricao="subshell"),
    RegraCmd(re.compile(r"^(netsh|iptables|ufw|firewall-cmd)\s+"), CmdCategoria.DESTRUTIVO, shell_permitido=True, descricao="firewall/rede"),
    RegraCmd(re.compile(r"^(reg\s+|regedit|regedt32)"), CmdCategoria.DESTRUTIVO, shell_permitido=True, descricao="registro Windows"),
]

_BLOQUEADOS_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in _BLOQUEADOS_ABSOLUTOS]







def _contem_injecao(cmd: str) -> bool:
    suspeitos = [";", "&&", "||", "`", "$(",  "$(", ">{", "<(", "2>&1 |"]
    cmd_lower = cmd.lower()
    return any(s in cmd_lower for s in suspeitos)







def _sanitizar(cmd: str) -> str:
    cmd = cmd.strip()
    cmd = re.sub(r"\s+", " ", cmd)
    return cmd







def avaliar_comando(comando: str) -> ResultadoSeguranca:
    cmd = _sanitizar(comando)

    if not cmd:
        return ResultadoSeguranca(permitido=False, motivo="Comando vazio.")

    for padrao in _BLOQUEADOS_COMPILADOS:
        if padrao.search(cmd):
            log.warning("Comando bloqueado (padrão absoluto): %s", cmd[:80])
            return ResultadoSeguranca(
                permitido=False,
                categoria=CmdCategoria.BLOQUEADO,
                motivo=f"Comando bloqueado por política de segurança: padrão proibido detectado.",
            )

    if _contem_injecao(cmd):
        log.warning("Possível injeção detectada: %s", cmd[:80])
        return ResultadoSeguranca(
            permitido=False,
            categoria=CmdCategoria.BLOQUEADO,
            motivo="Comando contém operadores de encadeamento suspeitos (;, &&, ||, backtick).",
        )

    for regra in _REGRAS:
        if regra.padrao.match(cmd):
            requer_conf = regra.categoria == CmdCategoria.DESTRUTIVO
            return ResultadoSeguranca(
                permitido=True,
                requer_confirmacao=requer_conf,
                categoria=regra.categoria,
                motivo=regra.descricao,
                comando_sanitizado=cmd,
            )

    log.info("Comando não mapeado, requer confirmação: %s", cmd[:80])
    return ResultadoSeguranca(
        permitido=True,
        requer_confirmacao=True,
        categoria=CmdCategoria.SISTEMA,
        motivo="Comando não catalogado — confirmação necessária.",
        comando_sanitizado=cmd,
    )







def executar_seguro(
    comando: str,
    timeout: int = 15,
    confirmar_fn=None,
) -> str:
    avaliacao = avaliar_comando(comando)

    if not avaliacao.permitido:
        return f"Bloqueado: {avaliacao.motivo}"

    if avaliacao.requer_confirmacao:
        if confirmar_fn is None:
            return (
                f"Comando '{avaliacao.categoria.value}' requer confirmação explícita.\n"
                f"Motivo: {avaliacao.motivo}\n"
                f"Para executar, confirme com: executar_confirmado('{comando}')"
            )
        if not confirmar_fn(comando, avaliacao):
            return "Execução cancelada pelo usuário."

    cmd = avaliacao.comando_sanitizado or comando

    usar_shell = any(r.shell_permitido and r.padrao.match(cmd) for r in _REGRAS)

    try:
        if usar_shell:
            resultado = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            try:
                args = shlex.split(cmd)
            except ValueError:
                args = cmd.split()
            resultado = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

        saida = (resultado.stdout or resultado.stderr or "Comando executado sem saída.").strip()
        if resultado.returncode != 0:
            log.warning("Comando retornou código %d: %s", resultado.returncode, cmd[:60])
        return saida[:600]

    except subprocess.TimeoutExpired:
        return f"Timeout: comando excedeu {timeout}s."
    except FileNotFoundError as e:
        return f"Comando não encontrado: {e}"
    except Exception as e:
        log.error("Erro ao executar '%s': %s", cmd[:60], e)
        return f"Erro na execução: {e}"