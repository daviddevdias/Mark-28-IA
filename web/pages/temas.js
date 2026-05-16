'use strict';

function pgTemas(wrap) {
    const ids = Object.keys(state.themes);

    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title" style="font-weight:700;">PROTOCOLO VISUAL</div>
                <div class="page-sub"   style="font-weight:700;">Selecione o esquema de cores da interface</div>
            </div>
        </div>

        ${ids.length === 0
            ? `<div style="text-align:center;padding:80px;color:var(--text3);
                    font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:2px;">
                    Conecte o sistema para carregar os temas disponíveis.
               </div>`
            : `<div class="themes-grid">
                ${ids.map(id => {
                    const t      = state.themes[id];
                    const a1     = t.accent    || '#00c8ff';
                    const a2     = t.secondary || '#00ff9d';
                    const a3     = t.danger    || '#ff2255';
                    const bgGrad = t.bg_grad || `linear-gradient(135deg, ${a1}33 0%, ${a2}1f 55%, ${a3}24 100%)`;
                    const active = state.theme === id;
                    return `
                        <div class="theme-card ${active ? 'active-theme' : ''}"
                             style="border-color:${active ? a1 : 'var(--border)'};"
                             onclick="aplicarTema('${id}')">
                            <div class="theme-preview">
                                <div class="theme-swatch" style="background:${bgGrad};flex:3;"></div>
                                <div class="theme-swatch" style="background:${a1};"></div>
                                <div class="theme-swatch" style="background:${a2};"></div>
                                <div class="theme-swatch" style="background:${a3};"></div>
                            </div>
                            <div class="theme-name" style="color:${a1};font-weight:700;">${id}</div>
                            <button class="theme-apply-btn" style="font-weight:700;border-color:${a1};color:${a1};
                                    background:${active ? a1 + '1a' : 'transparent'};">
                                ${active ? '✓ ATIVO' : 'APLICAR'}
                            </button>
                        </div>`;
                }).join('')}
               </div>`}

        <div style="margin-top:18px;padding:15px 18px;background:var(--card);
             border:1px solid var(--border);border-radius:10px;
             font-family:var(--mono);font-size:11px;font-weight:700;
             color:var(--text3);letter-spacing:1.5px;">
            Tema ativo persistido em
            <span style="color:var(--accent);">api/config_core.json</span>
            · restaurado automaticamente no próximo boot.
        </div>`;
}

function aplicarTema(id) {
    if (!state.themes[id]) return;
    state.theme = id;
    applyTheme(id);
    if (window.jarvis) window.jarvis.salvar_configuracao('tema_ativo', id);
    if (state.page === PG.TEMAS) renderPage();
    toast(`Tema ${id} ativado.`);
}

function applyTheme(id) {
    const t = state.themes[id];
    if (!t) return;
    const r = document.documentElement;
    r.style.setProperty('--accent',  t.accent    || '#ffb400');
    r.style.setProperty('--accent2', t.secondary || '#ff6a00');
    r.style.setProperty('--bg',      t.bg);
    if (t.bg_grad) r.style.setProperty('--bg-grad', t.bg_grad);
    else r.style.removeProperty('--bg-grad');
    r.style.setProperty('--card',    t.card);
    r.style.setProperty('--border',  t.border);
    r.style.setProperty('--border2', t.border);
    r.style.setProperty('--text',    t.text_pri);
    r.style.setProperty('--text2',   t.text_sec);
    r.style.setProperty('--red',     t.danger);
    r.style.setProperty('--surface', t.surface || t.card);
}