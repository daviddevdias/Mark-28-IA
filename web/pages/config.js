'use strict';

function toggleEditConfig() {
    state.configEdit = !state.configEdit;
    if (state.page === PG.CONFIG) renderPage();
    toast(state.configEdit ? '🔓 Edição liberada.' : '🔒 Configurações bloqueadas.');
}

function pgConfig(wrap) {
    const locked    = !state.configEdit;
    const lockStyle = locked ? 'opacity:.45;cursor:not-allowed;border-color:transparent;' : '';

    const apiFields = [
        { key: 'gemini',              label: 'GEMINI API KEY',            tip: 'Google AI Studio'                   },
        { key: 'qwen',                label: 'QWEN / OPENROUTER KEY',     tip: 'OpenRouter — qwen-vl-max etc.'      },
        { key: 'openweather_api_key', label: 'OPENWEATHER API KEY',       tip: 'openweathermap.org'                 },
        { key: 'telegram_token',      label: 'TELEGRAM BOT TOKEN',        tip: '@BotFather'                         },
        { key: 'telegram_auth_token', label: 'TELEGRAM AUTH TOKEN',       tip: 'Token de autorização personalizado' },
        { key: 'smartthings',         label: 'SMARTTHINGS TOKEN',         tip: 'SmartThings API'                    },
        { key: 'spotify_id',          label: 'SPOTIFY CLIENT ID',         tip: 'Spotify Developer Dashboard'        },
        { key: 'spotify_sec',         label: 'SPOTIFY CLIENT SECRET',     tip: 'Spotify Developer Dashboard'        },
    ];

    const sttFields = [
        { key: 'deepgram_api_key', label: 'DEEPGRAM API KEY',      tip: 'Nova-3 · STT primário (~300ms)'         },
        { key: 'whisper_model',    label: 'WHISPER MODEL (LOCAL)', tip: 'tiny / base / small / medium / large', pw: false },
    ];

    function renderFields(fields) {
        return fields.map(f => `
            <div class="api-field">
                <div class="api-field-top">
                    <div class="api-label">${f.label}</div>
                    <div class="api-status ${state.apis[f.key] ? 'ok' : ''}" id="dot_${f.key}"></div>
                </div>
                <input class="api-input" id="api_${f.key}"
                       type="${f.pw === false ? 'text' : 'password'}"
                       placeholder="${f.tip}"
                       value="${esc(state.apis[f.key] || '')}"
                       ${locked ? 'readonly' : ''}
                       style="transition:all .3s;${lockStyle}"
                       oninput="onApiInput('${f.key}', this.value)">
            </div>`).join('');
    }

    function inputPref(id, key, placeholder, type = 'text') {
        return `<input class="input" id="${id}"
                       type="${type}"
                       value="${esc(String(state.apis[key] ?? ''))}"
                       placeholder="${placeholder}"
                       ${locked ? 'readonly' : ''}
                       style="width:100%;transition:all .3s;font-weight:700;${lockStyle}"
                       oninput="state.apis['${key}']=this.value">`;
    }

    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">CONFIGURAÇÃO</div>
                <div class="page-sub">APIs e preferências do sistema</div>
            </div>
            <div style="display:flex;gap:12px;">
                <button class="btn ${state.configEdit ? 'btn-accent2' : 'btn-ghost'}" onclick="toggleEditConfig()">
                    ${state.configEdit ? '🔓 BLOQUEAR' : '🔒 EDITAR CHAVES'}
                </button>
                <button class="btn btn-accent" onclick="salvarConfig()">💾 SALVAR TUDO</button>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-heading">
                <h3>CHAVES DE API — SISTEMA</h3>
                <div class="section-line"></div>
            </div>
            <div class="api-row">${renderFields(apiFields)}</div>
        </div>

        <div class="settings-section">
            <div class="section-heading">
                <h3>VOZ — STT (SPEECH-TO-TEXT)</h3>
                <div class="section-line"></div>
            </div>
            <div class="badge-row">
                <span class="badge">1º Deepgram Nova-3</span>
                <span class="badge-sep">→</span>
                <span class="badge">2º Google STT</span>
                <span class="badge-sep">→</span>
                <span class="badge">3º Whisper Local</span>
            </div>
            <div class="api-row">${renderFields(sttFields)}</div>
        </div>

        <div class="settings-section">
            <div class="section-heading">
                <h3>VOZ — TTS (TEXT-TO-SPEECH)</h3>
                <div class="section-line"></div>
            </div>
            <div class="badge-row">
                <span class="badge accent">1º Local Clone (XTTSv2)</span>
                <span class="badge-sep">→</span>
                <span class="badge accent">2º Edge TTS</span>
            </div>
        </div>

        <div class="settings-section">
            <div class="section-heading">
                <h3>PREFERÊNCIAS GERAIS</h3>
                <div class="section-line"></div>
            </div>
            <div class="card" style="padding:22px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="margin-top:6px;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px;">
                    <div>
                        <div class="pref-label">NOME DO MESTRE</div>
                        ${inputPref('masterName', 'nome_mestre', 'David')}
                    </div>
                    <div>
                        <div class="pref-label">CIDADE PADRÃO (CLIMA)</div>
                        ${inputPref('defaultCity', 'cidade_padrao', 'Ex: São Paulo')}
                    </div>
                </div>
            </div>
        </div>

        <div class="cfg-footer">
            <span>◈ Persistido em <span style="color:var(--accent);">api/config_core.json</span></span>
            <span>◎ STT: <span style="color:var(--accent2);">Deepgram Nova-3</span></span>
            <span>◎ TTS: <span style="color:var(--accent2);">Local Clone + Edge</span></span>
        </div>

        <style>
            .pref-label {
                font-family: var(--mono);
                font-size: 10px;
                font-weight: 700;
                color: var(--text3);
                letter-spacing: 3px;
                margin-bottom: 8px;
            }
            .badge-row {
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
                margin-bottom: 12px;
            }
            .badge {
                font-family: var(--mono);
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                padding: 4px 10px;
                border-radius: 4px;
                background: var(--card);
                border: 1px solid var(--border);
                color: var(--text3);
            }
            .badge.accent { border-color: var(--accent); color: var(--accent); }
            .badge-sep { color: var(--text3); font-size: 12px; font-weight: 700; }
            .cfg-footer {
                font-family: var(--mono);
                font-size: 11px;
                font-weight: 700;
                color: var(--text3);
                letter-spacing: 1.5px;
                margin-top: 10px;
                padding: 14px 18px;
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 10px;
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 16px;
            }
        </style>
    `;
}

function onApiInput(key, val) {
    state.apis[key] = val;
    const dot = document.getElementById('dot_' + key);
    if (dot) dot.className = 'api-status ' + (val ? 'ok' : '');
}

function salvarConfig() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }

    const keys = [
        'gemini', 'qwen',
        'openweather_api_key',
        'telegram_token', 'telegram_auth_token',
        'smartthings', 'smartthings_tv_id',
        'spotify_id', 'spotify_sec',
        'deepgram_api_key', 'whisper_model',
        'nome_mestre', 'cidade_padrao',
    ];

    let saved = 0;
    for (const k of keys) {
        const v = state.apis[k];
        if (v !== undefined && v !== null) {
            window.jarvis.salvar_configuracao(k, String(v));
            saved++;
        }
    }

    toast(`✓ ${saved} configurações salvas.`);
    if (state.configEdit) toggleEditConfig();
}