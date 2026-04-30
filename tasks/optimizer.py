import sqlite3
import os







def conectar_banco_auditoria() -> sqlite3.Connection:
    caminho_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "audit.db")
    conexao = sqlite3.connect(caminho_db, timeout=10)
    conexao.row_factory = sqlite3.Row
    return conexao







async def comprimir_banco_auditoria() -> str:
    conexao = conectar_banco_auditoria()
    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM audit_log")
    total_antes = cursor.fetchone()["total"]
    if total_antes < 50:
        conexao.close()
        return f"O banco já está otimizado. Registros atuais: {total_antes}."
    cursor.execute("SELECT comando, resultado, ts FROM audit_log ORDER BY id ASC LIMIT 100")
    registros = cursor.fetchall()
    texto_logs = " ".join([f"[{r['ts']}] Cmd: {r['comando']} | Res: {r['resultado'][:50]}" for r in registros])
    from engine.ia_router import router
    prompt = f"Analise este bloco de logs antigos e crie um resumo técnico de 2 linhas sobre o estado e comportamento do sistema. Logs: {texto_logs}"
    resumo = await router.responder(prompt)
    cursor.execute("DELETE FROM audit_log WHERE id IN (SELECT id FROM audit_log ORDER BY id ASC LIMIT 100)")
    conexao.commit()
    cursor.execute("SELECT COUNT(*) as total FROM audit_log")
    total_depois = cursor.fetchone()["total"]
    conexao.close()
    return f"Registos reduzidos de {total_antes} para {total_depois}. Resumo do período apagado: {resumo}"