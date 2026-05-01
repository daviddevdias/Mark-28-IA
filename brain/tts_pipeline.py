from __future__ import annotations

import logging
import threading
import time
import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, AsyncIterator

log = logging.getLogger("jarvis.core")

INTERVALO_CHECK = 30.0
MAX_FALHAS      = 3
COOLDOWN_RESET  = 60.0
SEPARADORES     = re.compile(r"(?<=[.!?;:])\s+|(?<=,)\s{2,}")
MIN_CHUNK       = 20







class StatusModulo(Enum):
    OK          = "ok"
    DEGRADADO   = "degradado"
    FALHOU      = "falhou"
    REINICIANDO = "reiniciando"







@dataclass
class RegistroModulo:
    nome:          str
    check_fn:      Callable[[], bool]
    reset_fn:      Callable[[], None] | None = None
    falhas:        int                       = 0
    status:        StatusModulo              = StatusModulo.OK
    ultimo_check:  float                     = 0.0
    ultimo_reset:  float                     = 0.0
    historico:     list[dict]                = field(default_factory=list)







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
        agora = time.time()
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







class FilaTTS:







    def __init__(self) -> None:
        self.fila:    asyncio.Queue[str | None] = asyncio.Queue(maxsize=20)
        self.rodando: bool                      = False
        self.task:    asyncio.Task | None       = None
        self.falar:   Callable | None           = None







    def registrar_falar(self, fn: Callable) -> None:
        self.falar = fn







    async def iniciar(self) -> None:
        if self.rodando:
            return
        self.rodando = True
        self.task    = asyncio.create_task(self.consumidor())







    def limpar_fila(self) -> None:
        while not self.fila.empty():
            try:
                self.fila.get_nowait()
                self.fila.task_done()
            except asyncio.QueueEmpty:
                break







    async def parar(self, forcar_parada: bool = False) -> None:
        self.rodando = False
        if forcar_parada:
            self.limpar_fila()
        await self.fila.put(None)
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=1.5)
            except asyncio.TimeoutError:
                self.task.cancel()
            except Exception:
                pass







    async def enfileirar(self, texto: str) -> None:
        segmentos = segmentar(texto)
        for seg in segmentos:
            if not self.rodando:
                break
            await self.fila.put(seg)







    async def consumidor(self) -> None:
        while self.rodando:
            try:
                item = await asyncio.wait_for(self.fila.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if item is None:
                break
            if self.falar:
                try:
                    await self.falar(item)
                except Exception as exc:
                    log.error("TTS fila erro: %s", exc)
            self.fila.task_done()







def segmentar(texto: str) -> list[str]:
    partes = SEPARADORES.split(texto.strip())
    resultado: list[str] = []
    acumulado = ""
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        acumulado = (acumulado + " " + parte).strip() if acumulado else parte
        if len(acumulado) >= MIN_CHUNK:
            resultado.append(acumulado)
            acumulado = ""
    if acumulado:
        resultado.append(acumulado)
    return resultado or [texto]







async def falar_streaming(gerador: AsyncIterator[str], falar_fn: Callable) -> str:
    fila_tts.registrar_falar(falar_fn)
    if not fila_tts.rodando:
        await fila_tts.iniciar()
    buffer     = ""
    texto_full = ""
    async for token in gerador:
        buffer     += token
        texto_full += token
        if any(buffer.endswith(s) for s in (".", "!", "?", ";", ":")):
            segmento = buffer.strip()
            if len(segmento) >= MIN_CHUNK:
                await fila_tts.enfileirar(segmento)
                buffer = ""
    if buffer.strip():
        await fila_tts.enfileirar(buffer.strip())
    return texto_full







watchdog = Watchdog()
fila_tts = FilaTTS()