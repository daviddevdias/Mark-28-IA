'use strict';

function pgNotas(wrap) {
    wrap.innerHTML = `
        <style>
            .notes-item { animation: msgEnter 0.3s ease-out both; }
            .notes-history { scroll-behavior: smooth; }
        </style>
        <div class="chat-wrap" style="max-height:500px;display:flex;flex-direction:column;">
            <div class="chat-history notes-history" id="notasHistory" style="padding:10px;flex:1;">
                <div class="notes-item">
                    <textarea class="notes-textarea" id="notasTxt"
                              spellcheck="false"
                              style="width:100%;height:380px;background:rgba(0,0,0,0.08);
                                     border:1px solid rgba(255,255,255,0.05);border-radius:8px;
                                     padding:12px;font-size:13px;color:var(--text2);font-weight:700;
                                     line-height:1.5;resize:none;outline:none;font-family:var(--mono);"
                              placeholder="ENTRADA DE DADOS TÁTICOS...">${esc(state.notas)}</textarea>
                </div>
            </div>
            <div class="chat-input-row" style="gap:8px;padding:10px;border-top:1px solid var(--border);">
                <div style="flex:1;display:flex;align-items:center;gap:10px;">
                    <div class="status-glitch" id="notasStatus"
                         style="font-family:var(--mono);font-size:14px;font-weight:700;color:var(--accent);letter-spacing:1px;">
                        0 CHR
                    </div>
                </div>
                <button class="btn btn-ghost"   onclick="limparNotas()" style="padding:6px 15px;font-size:11px;font-weight:700;">LIMPAR</button>
                <button class="btn btn-accent"  onclick="salvarNotas()" style="padding:6px 15px;font-size:11px;font-weight:700;">SALVAR</button>
            </div>
        </div>`;

    const ta = document.getElementById('notasTxt');
    if (ta) {
        const atualizarMeta = val => {
            document.getElementById('notasStatus').textContent = `${val.length} CHR`;
        };
        atualizarMeta(ta.value);
        ta.addEventListener('input', e => {
            state.notas = e.target.value;
            atualizarMeta(e.target.value);
        });
    }
}
window.pgNotas = pgNotas;

function salvarNotas() {
    if (window.jarvis) window.jarvis.salvar_configuracao('notas', state.notas);
    toast('✓ DATA SYNC');
}
window.salvarNotas = salvarNotas;

function limparNotas() {
    state.notas = '';
    const t = document.getElementById('notasTxt');
    if (t) {
        t.value = '';
        document.getElementById('notasStatus').textContent = '0 CHR';
    }
    toast('MEM_CLEAR', 'warn');
}
window.limparNotas = limparNotas;