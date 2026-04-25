import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

log = logging.getLogger("jarvis.tool_cache")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "tool_cache.db")







@dataclass
class ConfigTool:
    timeout_s: float = 15.0
    ttl_s: float = 0.0
    cache: bool = False
    nome: str = ""







CONFIGS: dict[str, ConfigTool] = {
    "weather_report":   ConfigTool(10.0,  600.0, True,  "Clima"),
    "web_search":       ConfigTool(20.0,  120.0, True,  "Web"),
    "smart_home":       ConfigTool(8.0,   30.0,  True,  "Casa"),
    "spotify_control":  ConfigTool(8.0,   0.0,   False, "Spotify"),
    "open_app":         ConfigTool(12.0,  0.0,   False, "App"),
    "computer_control": ConfigTool(10.0,  0.0,   False, "PC"),
    "cmd_control":      ConfigTool(20.0,  0.0,   False, "CMD"),
    "youtube_video":    ConfigTool(30.0,  0.0,   False, "YouTube"),
    "screen_analysis":  ConfigTool(25.0,  0.0,   False, "Visão"),
    "file_controller":  ConfigTool(10.0,  0.0,   False, "Arquivos"),
    "set_reminder":     ConfigTool(5.0,   0.0,   False, "Alarme"),
    "save_memory":      ConfigTool(5.0,   0.0,   False, "Memória"),
    "agent_task":       ConfigTool(45.0,  0.0,   False, "Agente"),
    "code_helper":      ConfigTool(30.0,  0.0,   False, "Código"),
    "switch_ia_mode":   ConfigTool(5.0,   0.0,   False, "IA Mode"),
}







DEFAULT = ConfigTool()







class Cache:







    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.hits = 0
        self.miss = 0
        self.lock = asyncio.Lock() if False else None
        self.iniciar_banco()







    def conectar_banco(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn







    def iniciar_banco(self) -> None:
        try:
            with self.conectar_banco() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        chave      TEXT PRIMARY KEY,
                        tool       TEXT NOT NULL,
                        valor      TEXT NOT NULL,
                        criado_em  REAL NOT NULL,
                        ttl        REAL NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tool ON cache(tool)")
                conn.commit()
        except Exception:
            pass







    def gerar_chave(self, tool: str, args: dict) -> str:
        raw = json.dumps({"t": tool, "a": args}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]







    def get(self, tool: str, args: dict) -> Optional[Any]:
        k = self.gerar_chave(tool, args)
        try:
            with self.conectar_banco() as conn:
                row = conn.execute(
                    "SELECT valor, criado_em, ttl FROM cache WHERE chave = ?", (k,)
                ).fetchone()
                if row is None:
                    self.miss += 1
                    return None
                if (time.time() - row["criado_em"]) > row["ttl"]:
                    conn.execute("DELETE FROM cache WHERE chave = ?", (k,))
                    conn.commit()
                    self.miss += 1
                    return None
                self.hits += 1
                return json.loads(row["valor"])
        except Exception:
            self.miss += 1
            return None







    def set(self, tool: str, args: dict, valor: Any, ttl: float) -> None:
        k = self.gerar_chave(tool, args)
        try:
            with self.conectar_banco() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (chave, tool, valor, criado_em, ttl) VALUES (?,?,?,?,?)",
                    (k, tool, json.dumps(valor, default=str), time.time(), ttl),
                )
                conn.commit()
        except Exception:
            pass







    def invalidar(self, tool: str) -> int:
        try:
            with self.conectar_banco() as conn:
                cur = conn.execute("DELETE FROM cache WHERE tool = ?", (tool,))
                conn.commit()
                return cur.rowcount
        except Exception:
            return 0







    def limpar(self) -> None:
        try:
            with self.conectar_banco() as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()
        except Exception:
            pass







    def remover_expirados(self) -> None:
        try:
            with self.conectar_banco() as conn:
                conn.execute(
                    "DELETE FROM cache WHERE (? - criado_em) > ttl", (time.time(),)
                )
                conn.commit()
        except Exception:
            pass







    @property
    def stats(self) -> dict:
        total = self.hits + self.miss
        try:
            with self.conectar_banco() as conn:
                vivos = conn.execute(
                    "SELECT COUNT(*) FROM cache WHERE (? - criado_em) <= ttl", (time.time(),)
                ).fetchone()[0]
        except Exception:
            vivos = 0
        return {
            "hits": self.hits,
            "misses": self.miss,
            "taxa_hit": f"{(self.hits / total * 100) if total else 0:.1f}%",
            "entradas_vivas": vivos,
        }







cache = Cache()







def carregar_config(nome: str) -> ConfigTool:
    return CONFIGS.get(nome, DEFAULT)







async def despachar(nome: str, args: dict, func: Callable) -> Any:
    c = carregar_config(nome)

    if c.cache and c.ttl_s > 0:
        cached = cache.get(nome, args)
        if cached is not None:
            return cached

    try:
        resultado = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(None, func, args),
            timeout=c.timeout_s,
        )
    except asyncio.TimeoutError:
        return f"Timeout: '{nome}' excedeu {c.timeout_s:.0f}s."
    except Exception as e:
        return f"Erro na ferramenta '{nome}': {e}"

    if c.cache and c.ttl_s > 0:
        if isinstance(resultado, str) and not resultado.startswith(("Erro", "Timeout")):
            cache.set(nome, args, resultado, c.ttl_s)

    return resultado







def stats_cache() -> dict:
    return cache.stats







def invalidar_cache_tool(nome: str) -> str:
    n = cache.invalidar(nome)
    return f"{n} entrada(s) removida(s) de '{nome}'."







def limpar_cache() -> str:
    cache.limpar()
    return "Cache do banco limpo."