'use strict';







async function pgComandos(wrap) {
    wrap.innerHTML =`
        <div class="page-header">
            <div>
                <div class="page-title">⌬ BIBLIOTECA DE COMANDOS</div>
                <div class="page-sub">Rotas de voz e atalhos reconhecidos pelo núcleo</div>
            </div>
            <input class="input" id="cmdFilterIn" placeholder="Filtrar…" style="max-width:280px;"
                   value="${esc(state.cmdFilter)}">
        </div>
        <div id="cmdListMount" style="margin-top:14px;">
            <div style="color:var(--text3);font-family:var(--mono);font-size:13px;">A carregar…</div>
        </div>`;

    const inp = document.getElementById('cmdFilterIn');
    inp?.addEventListener('input', e => {
        state.cmdFilter = e.target.value;
        renderCmdList();
    });

    if (window.jarvis?.obter_biblioteca_comandos) {
        try {
            const raw = await new Promise(res => {
                try { window.jarvis.obter_biblioteca_comandos(r => res(r)); }
                catch (err) { res(null); }
            });
            if (raw) state.cmdLibrary = JSON.parse(raw);
        } catch (e) { state.cmdLibrary = state.cmdLibrary || []; }
    }
    renderCmdList();
}







function renderCmdList() {
    const mount = document.getElementById('cmdListMount');

        
    if (!mount) return;
    const q = (state.cmdFilter || '').trim().toLowerCase();
    const items = (state.cmdLibrary || []).filter(it => {
        if (!q) return true;
        const blob = `${it.cmd} ${it.cat} ${it.desc} ${(it.passos || []).join(' ')}`.toLowerCase();
        return blob.includes(q);
    });


    if (!items.length) {
        mount.innerHTML =`<div class="card" style="padding:40px;text-align:center;color:var(--text3);">
            Nenhum comando corresponde ao filtro.</div>`;
        return;
    }


    mount.innerHTML =`<div class="cmd-grid">${items.map(it =>`
        <div class="cmd-card">
            <div class="cmd-card-top">
                <span class="cmd-icon">${it.icon || '◈'}</span>
                <span class="cmd-cat">${esc(it.cat || '')}</span>
            </div>
            <div class="cmd-name">${esc(it.cmd)}</div>
            <div class="cmd-desc">${esc(it.desc || '')}</div>
            ${(it.passos && it.passos.length) ?`
                <ul class="cmd-steps">${it.passos.map(p => `<li>${esc(p)}</li>`).join('')}</ul>` : ''}
        </div>`).join('')}</div>`;
    mount.querySelectorAll('.cmd-copy').forEach(btn => {
        btn.addEventListener('click', () => {
            const t = btn.getAttribute('data-cmd') || '';
            if (t) {
                navigator.clipboard?.writeText(t).then(() => toast('Copiado.')).catch(() => toast(t.slice(0, 80)));
            }
        });
    });
}