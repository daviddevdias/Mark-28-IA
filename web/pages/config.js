'use strict';







function toggleEditConfig() {
    state.configEdit = !state.configEdit;
    if (state.page === PG.CONFIG) renderPage();
    toast(state.configEdit ? '🔓 Edição liberada.' : '🔒 Configurações bloqueadas.');
}







function pgConfig(wrap) {
    const apiFields = [
        { key:'gemini',      label:'GEMINI API KEY',    tip:'Google AI Studio'  },
        { key:'qwen',        label:'QWEN API KEY',      tip:'Alibaba Cloud'     },
        { key:'smartthings', label:'SMARTTHINGS TOKEN', tip:'SmartThings API'   },
        { key:'smartthings_tv_id', label:'SMARTTHINGS — ID DA TV (opcional)', tip:'Cole o deviceId (app SmartThings → TV → três pontos → Informação)' },
        { key:'spotify_id',  label:'SPOTIFY CLIENT ID', tip:'Spotify Dashboard' },
        { key:'spotify_sec', label:'SPOTIFY SECRET',    tip:'Spotify Dashboard' },
    ];

    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">CONFIGURAÇÃO</div>
                <div class="page-sub">Chaves de API e preferências do sistema</div>
            </div>
            <div style="display:flex;gap:12px;">
                <button class="btn ${state.configEdit ? 'btn-accent2' : 'btn-ghost'}"
                        onclick="toggleEditConfig()">
                    ${state.configEdit ? '🔓 BLOQUEAR' : '🔒 EDITAR CHAVES'}
                </button>
                <button class="btn btn-accent" onclick="salvarConfig()">💾 SALVAR TUDO</button>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-heading"><h3>CHAVES DE API</h3><div class="section-line"></div></div>
            <div class="api-row">
                ${apiFields.map(f => `
                    <div class="api-field">
                        <div class="api-field-top">
                            <div class="api-label">${f.label}</div>
                            <div class="api-status ${state.apis[f.key] ? 'ok' : ''}" id="dot_${f.key}"></div>
                        </div>
                        <input class="api-input" id="api_${f.key}" type="${f.key === 'smartthings_tv_id' ? 'text' : 'password'}"
                               placeholder="${f.tip}"
                               value="${esc(state.apis[f.key] || '')}"
                               ${state.configEdit ? '' : 'readonly'}
                               style="transition:all .3s;${state.configEdit ? '' : 'opacity:.5;cursor:not-allowed;border-color:transparent;'}"
                               oninput="onApiInput('${f.key}', this.value)">
                    </div>`).join('')}
            </div>
        </div>

        <div class="settings-section">
            <div class="section-heading"><h3>PREFERÊNCIAS</h3><div class="section-line"></div></div>
            <div class="card" style="padding:22px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="margin-top:6px;display:flex;flex-direction:column;gap:14px;">
                    <div>
                        <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                             color:var(--text3);letter-spacing:3px;margin-bottom:8px;">NOME DO MESTRE</div>
                        <input class="input" id="masterName"
                               value="${esc(state.apis.nome_mestre || '')}"
                               placeholder="David"
                               ${state.configEdit ? '' : 'readonly'}
                               style="max-width:320px;width:100%;transition:all .3s;${state.configEdit ? '' : 'opacity:.5;cursor:not-allowed;border-color:transparent;'}"
                               oninput="state.apis.nome_mestre=this.value">
                    </div>
                    <div>
                        <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                             color:var(--text3);letter-spacing:3px;margin-bottom:8px;margin-top:8px;">
                             CIDADE PADRÃO (CLIMA)
                        </div>
                        <input class="input" id="defaultCity"
                               value="${esc(state.apis.cidade_padrao || '')}"
                               placeholder="Ex: São Paulo"
                               ${state.configEdit ? '' : 'readonly'}
                               style="max-width:320px;width:100%;transition:all .3s;${state.configEdit ? '' : 'opacity:.5;cursor:not-allowed;border-color:transparent;'}"
                               oninput="state.apis.cidade_padrao=this.value;state.weather.city=this.value;">
                    </div>
                </div>
            </div>
        </div>

        <div style="font-family:var(--mono);font-size:11px;font-weight:700;
             color:var(--text3);letter-spacing:1.5px;margin-top:10px;padding:14px 18px;
             background:var(--card);border:1px solid var(--border);border-radius:10px;">
            Configurações persistidas em
            <span style="color:var(--accent);">api/config_core.json</span>
        </div>
    `;
}







function onApiInput(key, val) {
    state.apis[key] = val;
    const dot = document.getElementById(`dot_${key}`);
    if (dot) dot.className = 'api-status ' + (val ? 'ok' : '');
}







function salvarConfig() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    const keys = ['gemini','qwen','smartthings','smartthings_tv_id','spotify_id','spotify_sec','nome_mestre','cidade_padrao'];
    let saved = 0;
    keys.forEach(k => {
        if (state.apis[k] !== undefined) { window.jarvis.salvar_configuracao(k, state.apis[k]); saved++; }
    });
    toast(`✓ ${saved} configurações salvas.`);
    if (state.configEdit) toggleEditConfig();
}