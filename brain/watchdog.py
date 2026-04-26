from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

log = logging.getLogger("jarvis.watchdog")

INTERVALO_CHECK = 30.0
MAX_FALHAS      = 3
COOLDOWN_RESET  = 60.0


class StatusModulo(Enum):
    OK          = "ok"
    DEGRADADO   = "degradado"
    FALHOU      = "falhou"
    REINICIANDO = "reiniciando"


@dataclass
class RegistroModulo:
    nome:         str
    check_fn:     Callable[[], bool]
    reset_fn:     Callable[[], None] | None = None
    falhas:       int                       = 0
    status:       StatusModulo              = StatusModulo.OK
    ultimo_check: float                     = 0.0
    ultimo_reset: float                     = 0.0
    historico:    list[dict]                = field(default_factory=list)


class Watchdog:

    def __init__(self) -> None:
        self.modulos: dict[str, RegistroModulo] = {}
        self.lock     = threading.Lock()
        self.rodando  = False
        self.thread:  threading.Thread | None   = None

    def registrar(
        self,
        nome: str,
        check_fn: Callable[[], bool],
        reset_fn: Callable[[], None] | None = None,
    ) -> None:
        with self.lock:
            self.modulos[nome] = RegistroModulo(
                nome=nome, check_fn=check_fn, reset_fn=reset_fn
            )
        log.info("[Watchdog] Módulo '%s' registrado.", nome)

    def checar_modulo(self, reg: RegistroModulo) -> None:
        agora         = time.time()
        reg.ultimo_check = agora

        try:
            ok = reg.check_fn()
        except Exception as exc:
            ok = False
            log.warning("[Watchdog] check '%s' lançou exceção: %s", reg.nome, exc)

        if ok:
            if reg.falhas > 0:
                log.info("[Watchdog] '%s' recuperado após %d falha(s).", reg.nome, reg.falhas)
                try:
                    from brain.event_bus import bus, MODULO_RECUPERADO
                    bus.publicar(MODULO_RECUPERADO, {"modulo": reg.nome})
                except Exception:
                    pass
            reg.falhas = 0
            reg.status = StatusModulo.OK
            reg.historico.append({"ts": agora, "ok": True})
        else:
            reg.falhas += 1
            reg.historico.append({"ts": agora, "ok": False})
            log.warning("[Watchdog] '%s' falhou (%d/%d).", reg.nome, reg.falhas, MAX_FALHAS)

            if reg.falhas == 1:
                reg.status = StatusModulo.DEGRADADO
            elif reg.falhas >= MAX_FALHAS:
                reg.status = StatusModulo.FALHOU
                try:
                    from brain.event_bus import bus, ERRO_MODULO
                    bus.publicar(ERRO_MODULO, {"modulo": reg.nome, "falhas": reg.falhas})
                except Exception:
                    pass
                if reg.reset_fn and (agora - reg.ultimo_reset) > COOLDOWN_RESET:
                    self.tentar_reset(reg)

        if len(reg.historico) > 50:
            reg.historico = reg.historico[-50:]

    def tentar_reset(self, reg: RegistroModulo) -> None:
        reg.status = StatusModulo.REINICIANDO
        log.info("[Watchdog] Reiniciando '%s'...", reg.nome)
        try:
            reg.reset_fn()
            reg.falhas       = 0
            reg.ultimo_reset = time.time()
            reg.status       = StatusModulo.OK
            log.info("[Watchdog] '%s' reiniciado com sucesso.", reg.nome)
        except Exception as exc:
            log.error("[Watchdog] Falha ao reiniciar '%s': %s", reg.nome, exc)
            reg.status = StatusModulo.FALHOU

    def loop_verificacao(self) -> None:
        while self.rodando:
            with self.lock:
                modulos = list(self.modulos.values())
            for reg in modulos:
                try:
                    self.checar_modulo(reg)
                except Exception as exc:
                    log.error("[Watchdog] Erro interno ao checar '%s': %s", reg.nome, exc)
            time.sleep(INTERVALO_CHECK)

    def iniciar(self) -> None:
        if self.rodando:
            return
        self.rodando = True
        self.thread  = threading.Thread(target=self.loop_verificacao, daemon=True, name="Watchdog")
        self.thread.start()
        log.info("[Watchdog] Iniciado.")

    def parar(self) -> None:
        self.rodando = False

    def get_status(self) -> dict:
        with self.lock:
            return {
                nome: {
                    "status":       reg.status.value,
                    "falhas":       reg.falhas,
                    "ultimo_check": reg.ultimo_check,
                }
                for nome, reg in self.modulos.items()
            }

    def todos_ok(self) -> bool:
        with self.lock:
            return all(r.status == StatusModulo.OK for r in self.modulos.values())


watchdog = Watchdog()


def check_ia() -> bool:
    try:
        import requests
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def reset_ia() -> None:
    try:
        from engine.ia_router import detectar_modelo
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(asyncio.wait_for(detectar_modelo(), timeout=10))
        loop.close()
    except Exception as exc:
        raise RuntimeError(f"reset IA: {exc}")


def check_audio() -> bool:
    try:
        import audio.audio as _audio_mod
        return hasattr(_audio_mod, "falar") and callable(_audio_mod.falar)
    except Exception:
        return False


def check_browser() -> bool:
    try:
        from tasks.browser import jarvis_web
        return jarvis_web is not None
    except Exception:
        return False


def registrar_modulos_padrao() -> None:
    watchdog.registrar("ia",      check_ia,      reset_ia)
    watchdog.registrar("audio",   check_audio,   None)
    watchdog.registrar("browser", check_browser, None)