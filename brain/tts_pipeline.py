from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import AsyncIterator, Callable

log = logging.getLogger("jarvis.tts_pipeline")

_SEPARADORES = re.compile(r"(?<=[.!?;:])\s+|(?<=,)\s{2,}")
_MIN_CHUNK   = 20


def segmentar(texto: str) -> list[str]:
    partes = _SEPARADORES.split(texto.strip())
    resultado: list[str] = []
    acumulado = ""
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        acumulado = (acumulado + " " + parte).strip() if acumulado else parte
        if len(acumulado) >= _MIN_CHUNK:
            resultado.append(acumulado)
            acumulado = ""
    if acumulado:
        resultado.append(acumulado)
    return resultado or [texto]


class FilaTTS:

    def __init__(self) -> None:
        self._fila:    asyncio.Queue[str | None] = asyncio.Queue(maxsize=20)
        self._rodando: bool                      = False
        self._task:    asyncio.Task | None       = None
        self._falar:   Callable | None           = None

    def registrar_falar(self, fn: Callable) -> None:
        self._falar = fn

    async def iniciar(self) -> None:
        if self._rodando:
            return
        self._rodando = True
        self._task    = asyncio.create_task(self._consumidor())

    async def parar(self) -> None:
        self._rodando = False
        await self._fila.put(None)
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=3.0)
            except Exception:
                pass

    async def enfileirar(self, texto: str) -> None:
        segmentos = segmentar(texto)
        for seg in segmentos:
            await self._fila.put(seg)

    async def _consumidor(self) -> None:
        while self._rodando:
            try:
                item = await asyncio.wait_for(self._fila.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            if self._falar:
                try:
                    await self._falar(item)
                except Exception as exc:
                    log.error("TTS fila erro: %s", exc)

            self._fila.task_done()


fila_tts = FilaTTS()


async def falar_streaming(gerador: AsyncIterator[str], falar_fn: Callable) -> str:
    fila_tts.registrar_falar(falar_fn)
    if not fila_tts._rodando:
        await fila_tts.iniciar()

    buffer     = ""
    texto_full = ""

    async for token in gerador:
        buffer     += token
        texto_full += token

        if any(buffer.endswith(s) for s in (".", "!", "?", ";", ":")):
            segmento = buffer.strip()
            if len(segmento) >= _MIN_CHUNK:
                await fila_tts.enfileirar(segmento)
                buffer = ""

    if buffer.strip():
        await fila_tts.enfileirar(buffer.strip())

    return texto_full


async def falar_com_segmentacao(texto: str, falar_fn: Callable) -> None:
    fila_tts.registrar_falar(falar_fn)
    if not fila_tts._rodando:
        await fila_tts.iniciar()
    await fila_tts.enfileirar(texto)