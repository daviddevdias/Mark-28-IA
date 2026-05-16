'use strict';

async function pgComandos(wrap) {
    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" style="font-weight:700;">⌬ BIBLIOTECA DE COMANDOS</div>
                <div class="page-sub" style="font-weight:700;">Rotas de voz e atalhos reconhecidos pelo núcleo</div>
            </div>
            <div style="display:flex;gap:10px;align-items:center;">
                <button class="btn" id="btnCmdRefresh" style="font-weight:700;">ATUALIZAR</button>
                <input class="input" id="cmdFilterIn" placeholder="Filtrar…"
                       style="max-width:280px;font-weight:700;"
                       value="${esc(state.cmdFilter)}">
            </div>
        </div>
        <div id="cmdListMount" style="margin-top:14px;">
            <div style="color:var(--text3);font-family:var(--mono);font-size:13px;font-weight:700;">A carregar…</div>
        </div>`;

    const inp = document.getElementById('cmdFilterIn');
    inp?.addEventListener('input', e => {
        state.cmdFilter = e.target.value;
        renderCmdList();
    });

    document.getElementById('btnCmdRefresh')?.addEventListener('click', async () => {
        await carregarBibliotecaComandos();
        renderCmdList();
        toast('Biblioteca atualizada.');
    });

    await carregarBibliotecaComandos();
    renderCmdList();
}

async function carregarBibliotecaComandos() {
    if (window.jarvis?.obter_biblioteca_comandos) {
        try {
            const raw = await new Promise(res => {
                try {
                    window.jarvis.obter_biblioteca_comandos(r => res(r));
                } catch {
                    res(null);
                }
            });
            if (raw) state.cmdLibrary = JSON.parse(raw);
        } catch {
            state.cmdLibrary = state.cmdLibrary || [];
        }
    }
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
        mount.innerHTML = `<div class="card" style="padding:40px;text-align:center;color:var(--text3);font-weight:700;">
            Nenhum comando corresponde ao filtro.</div>`;
        return;
    }

    mount.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin:6px 2px 14px;">
        <div style="color:var(--text3);font-family:var(--mono);font-size:12px;letter-spacing:2px;font-weight:700;">
          ${items.length} comando(s)
        </div>
        <div style="color:var(--text3);font-family:var(--mono);font-size:12px;font-weight:700;">
          Fonte: núcleo + ferramentas
        </div>
      </div>
      <div class="cmd-grid">${items.map(it => `
        <div class="cmd-card">
            <div class="cmd-card-top">
                <span class="cmd-icon">${it.icon || '◈'}</span>
                <span class="cmd-cat" style="font-weight:700;">${esc(it.cat || '')}</span>
            </div>
            <div class="cmd-name" style="font-weight:700;">${esc(it.cmd)}</div>
            <div class="cmd-desc" style="font-weight:700;">${esc(it.desc || '')}</div>
            ${(it.passos && it.passos.length) ? `
                <ul class="cmd-steps">${it.passos.map(p => `<li style="font-weight:700;">${esc(p)}</li>`).join('')}</ul>` : ''}
        </div>`).join('')}</div>`;
}