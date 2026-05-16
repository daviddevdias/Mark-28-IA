'use strict';

function pgIA(wrap) {
    const { ia } = state;
    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" style="font-weight:700;">MODELO DE IA</div>
                <div class="page-sub"   style="font-weight:700;">Selecione e gerencie o motor de inteligência</div>
            </div>
        </div>

        <div class="ia-grid">
            <div class="ia-option ${ia.modo === 'ollama' ? 'ia-active' : ''}"
                 onclick="trocarIA('ollama')">
                <div class="ia-option-header">
                    <div class="ia-name" style="color:var(--accent);font-weight:700;">OLLAMA</div>
                    <div class="ia-badge-dot ${ia.ollama ? 'online' : ''} ${ia.modo === 'ollama' ? 'active-dot' : ''}"></div>
                </div>
                <div class="ia-desc" style="font-weight:700;">LLM local via Ollama. Privacidade total, sem API key. Requer ollama serve.</div>
                <div class="ia-model-tag" style="font-weight:700;">${ia.modo === 'ollama' && ia.modelo ? ia.modelo : 'nenhum detectado'}</div>
            </div>

            <div class="ia-option ${ia.modo === 'gemini' ? 'ia-active' : ''}"
                 onclick="trocarIA('gemini')">
                <div class="ia-option-header">
                    <div class="ia-name" style="color:var(--yellow);font-weight:700;">GEMINI</div>
                    <div class="ia-badge-dot ${ia.modo === 'gemini' ? 'active-dot' : ''}"></div>
                </div>
                <div class="ia-desc" style="font-weight:700;">Google Gemini via API. Maior capacidade, requer chave configurada.</div>
                <div class="ia-model-tag" style="font-weight:700;">${ia.modo === 'gemini' ? 'gemini-pro' : '—'}</div>
            </div>
        </div>

        <div class="card" style="padding:22px;margin-top:0;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:3px;margin-bottom:18px;margin-top:6px;">
                 STATUS DO MOTOR
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                ${iaStatus('MODO ATIVO', ia.modo.toUpperCase(), ia.modo === 'ollama' ? 'var(--accent)' : 'var(--yellow)')}
                ${iaStatus('OLLAMA', ia.ollama ? 'ONLINE' : 'OFFLINE', ia.ollama ? 'var(--accent2)' : 'var(--red)')}
                ${iaStatus('MODELO', ia.modelo || 'N/A', 'var(--text)')}
            </div>
        </div>

        <div style="display:flex;gap:12px;">
            <button class="btn btn-accent" style="font-weight:700;" onclick="atualizarStatusIA()">↺ ATUALIZAR STATUS</button>
            <button class="btn btn-ghost"  style="font-weight:700;" onclick="testarIA()">▶ TESTAR IA</button>
        </div>`;
}

function iaStatus(lbl, val, col) {
    return `
        <div style="padding:14px;background:var(--surface);border:1px solid var(--border);border-radius:10px;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:2.5px;margin-bottom:9px;">${lbl}</div>
            <div style="font-family:var(--orb);font-size:16px;font-weight:700;color:${col};">${val}</div>
        </div>`;
}

async function trocarIA(modo) {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    const res = await bridgeCall('alternar_ia', modo);
    if (res) {
        try { const r = JSON.parse(res); toast(r.msg || 'Modo alterado.'); } catch(e) {}
    }
    state.ia.modo = modo;
    if (state.page === PG.IA) renderPage();
}

async function atualizarStatusIA() {
    const raw = await bridge('obter_ia_status');
    if (raw) {
        try {
            const ia = JSON.parse(raw);
            state.ia = { modo: ia.modo || 'ollama', modelo: ia.modelo || '', ollama: !!ia.ollama };
            updateIABadge();
            if (state.page === PG.IA) renderPage();
            toast('✓ Status IA atualizado.');
        } catch(e) {}
    } else {
        toast('Status IA indisponível.', 'warn');
    }
}

function testarIA() {
    enviarComando('olá jarvis');
    navegarPara(PG.CHAT);
}