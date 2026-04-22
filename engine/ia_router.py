from __future__ import annotations

import json
import logging
import time
from collections import deque
from typing import Any, Optional

import aiohttp

from engine.tools import TOOL_DECLARATIONS, DISPATCHER
import config
from vision.capture import iniciar_monitor as ligar_monitor
from vision.capture import parar_monitor as desligar_monitor
from vision.capture import status_monitor as info_monitor

log = logging.getLogger("engine.ia_router")

URL_OLLAMA    = "http://127.0.0.1:11434/api/chat"
MODELO_OLLAMA = "qwen2.5"
TIMEOUT_S     = 30.0
MAX_HISTORICO = 20
MAX_TOOL_ITER = 5

BASE_SISTEMA = (
    "Você é Jarvis, assistente pessoal do sistema. "
    "Responda SEMPRE em português, de forma técnica e concisa. "
    "Contexto do mestre: {memoria}. "
    "REGRAS OBRIGATÓRIAS:\n"
    "1. Para QUALQUER ação real (abrir app, pesquisar, clima, spotify, etc) "
    "você DEVE chamar a ferramenta correspondente via tool_call.\n"
    "2. NUNCA simule, invente ou afirme que executou algo sem chamar a ferramenta.\n"
    "3. NUNCA retorne JSON bruto como resposta ao usuário.\n"
    "4. Após receber o resultado da ferramenta, responda de forma direta e curta.\n"
    "5. Se não souber qual ferramenta usar, responda em texto normalmente."
)


def _build_system(memoria: str) -> str:
    mem_limpa = memoria[:300] if memoria else "Nenhuma"
    return BASE_SISTEMA.format(memoria=mem_limpa)


def _tool_declarations_ollama() -> list[dict]:
    return TOOL_DECLARATIONS


class Historico:
    def __init__(self, max_turns: int = MAX_HISTORICO):
        self._turns: deque[dict] = deque(maxlen=max_turns)

    def adicionar(self, role: str, content: Any) -> None:
        self._turns.append({"role": role, "content": content})

    def adicionar_tool_result(self, tool_call_id: str, nome: str, resultado: str) -> None:
        self._turns.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": nome,
            "content": resultado,
        })

    def para_ollama(self) -> list[dict]:
        return list(self._turns)

    def limpar(self) -> None:
        self._turns.clear()

    def __len__(self) -> int:
        return len(self._turns)


class IARRouter:

    def __init__(self):
        self.ollama_disponivel: Optional[bool] = None
        self.ultimo_check: float = 0.0
        self.intervalo_check: float = 15.0
        self.historico = Historico()

    # ── status ──────────────────────────────────────────────────────────────

    @property
    def modo_atual(self) -> str:
        return "ollama"

    @property
    def status(self) -> dict:
        return {
            "modo": "ollama",
            "modelo": MODELO_OLLAMA,
            "ollama": self.ollama_disponivel,
        }

    # ── compatibilidade com painel.py ────────────────────────────────────────

    def definir_modo(self, modo: str) -> str:
        """Painel.py chama isso ao clicar em trocar IA. Só Ollama disponível."""
        if modo.lower() == "ollama":
            return f"Modo Ollama ativo. Modelo: {MODELO_OLLAMA}."
        # FIX: antes retornava mensagem confusa quando Gemini era pedido
        return (
            f"Modo '{modo}' não disponível nesta build. "
            f"Usando Ollama ({MODELO_OLLAMA}). "
            "Para ativar Gemini, configure a GEMINI_API_KEY e adicione o módulo."
        )

    def carregar_modo_salvo(self) -> None:
        pass

    def resetar_conversa(self) -> str:
        self.historico.limpar()
        return "Conversa resetada."

    # ── verificação de saúde ─────────────────────────────────────────────────

    async def _check_ollama(self) -> bool:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    "http://127.0.0.1:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as r:
                    return r.status == 200
        except Exception:
            return False

    async def _update_status(self) -> None:
        now = time.time()
        if now - self.ultimo_check < self.intervalo_check:
            return
        self.ultimo_check = now
        self.ollama_disponivel = await self._check_ollama()

    # ── despacho de ferramenta ───────────────────────────────────────────────

    async def _despachar_tool(self, nome: str, args: dict) -> str:
        try:
            from engine.tools_mapper import despachar
            resultado = await despachar(nome, args)
            return str(resultado)
        except Exception as e:
            log.error("Erro ao despachar tool '%s': %s", nome, e)
            return f"Erro na ferramenta '{nome}': {e}"

    # ── envio ao Ollama ──────────────────────────────────────────────────────

    async def _chat(self, mensagens: list[dict]) -> dict | None:
        payload = {
            "model": MODELO_OLLAMA,
            "messages": mensagens,
            "tools": _tool_declarations_ollama(),
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    URL_OLLAMA,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
                ) as r:
                    if r.status != 200:
                        texto = await r.text()
                        log.error("Ollama HTTP %d: %s", r.status, texto[:200])
                        return None
                    data = await r.json()
                    return data.get("message")
        except aiohttp.ClientConnectorError:
            log.error("Ollama não está rodando em %s", URL_OLLAMA)
            self.ollama_disponivel = False
            self.ultimo_check = 0.0
            return None
        except Exception as e:
            log.error("Exceção ao chamar Ollama: %s", e)
            self.ollama_disponivel = False
            self.ultimo_check = 0.0
            return None

    # ── loop principal com tool-use ──────────────────────────────────────────

    async def responder(
        self,
        pergunta: str,
        nome: str = "David",
        memoria: str = "",
        imagem: Any = None,
    ) -> str:
        await self._update_status()

        if not self.ollama_disponivel:
            return "Ollama offline. Inicie com 'ollama serve'."

        system = _build_system(memoria)

        # FIX: imagem era recebida mas nunca incluída no payload
        # Se vier imagem (base64 ou caminho), adiciona como conteúdo multimodal
        if imagem is not None:
            user_content = self._montar_conteudo_com_imagem(pergunta, imagem)
        else:
            user_content = pergunta

        self.historico.adicionar("user", user_content)
        mensagens = [{"role": "system", "content": system}] + self.historico.para_ollama()

        for iteracao in range(MAX_TOOL_ITER):
            msg = await self._chat(mensagens)

            if msg is None:
                self.historico._turns.pop()
                return "Ollama não respondeu. Verifique se o serviço está ativo."

            tool_calls: list = msg.get("tool_calls") or []

            if not tool_calls:
                resposta = (msg.get("content") or "").strip()
                if not resposta:
                    resposta = "Concluído."
                self.historico.adicionar("assistant", resposta)
                return resposta

            mensagens.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })
            self.historico.adicionar("assistant", msg.get("content") or "")

            for tc in tool_calls:
                tc_id    = tc.get("id", f"call_{iteracao}")
                fn       = tc.get("function", {})
                nome_fn  = fn.get("name", "")
                args_raw = fn.get("arguments", {})

                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except Exception:
                        args = {}
                else:
                    args = args_raw or {}

                log.info("Tool call [%d]: %s(%s)", iteracao, nome_fn, args)
                resultado = await self._despachar_tool(nome_fn, args)
                log.info("Tool result: %.120s", resultado)

                tool_result_msg = {
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": nome_fn,
                    "content": resultado,
                }
                mensagens.append(tool_result_msg)
                self.historico.adicionar_tool_result(tc_id, nome_fn, resultado)

        log.warning("Limite de iterações de tool-use atingido.")
        return "Operação concluída (limite de chamadas de ferramenta atingido)."

    # ── suporte a imagem ─────────────────────────────────────────────────────

    def _montar_conteudo_com_imagem(self, pergunta: str, imagem: Any) -> Any:
        """
        Monta conteúdo multimodal para o Ollama.
        imagem pode ser: caminho de arquivo (str), bytes ou base64 (str com prefixo data:).
        """
        import base64, os

        # Se for caminho de arquivo
        if isinstance(imagem, str) and os.path.isfile(imagem):
            try:
                with open(imagem, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                return [
                    {"type": "text", "text": pergunta},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                ]
            except Exception as e:
                log.warning("Falha ao carregar imagem '%s': %s", imagem, e)
                return pergunta

        # Se vier como bytes
        if isinstance(imagem, bytes):
            img_b64 = base64.b64encode(imagem).decode()
            return [
                {"type": "text", "text": pergunta},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            ]

        # Se já vier como base64 string (data:image/...)
        if isinstance(imagem, str) and imagem.startswith("data:"):
            return [
                {"type": "text", "text": pergunta},
                {"type": "image_url", "image_url": {"url": imagem}},
            ]

        # Fallback: ignora imagem inválida
        log.warning("Imagem em formato não reconhecido: %s", type(imagem))
        return pergunta


# instância global
router = IARRouter()
router.carregar_modo_salvo()