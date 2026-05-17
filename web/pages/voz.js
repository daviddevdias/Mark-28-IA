'use strict';

//  MEDIDOR DE VOZ (LOOP A 50ms) ──
function atualizarMedidorVoz() {
    const wrap = document.getElementById('vozMeterBars');
    if (!wrap) return;

    const barras      = wrap.querySelectorAll('.voz-bar');
    const estaFalando = state.voz.speaking;
    const volume      = estaFalando ? state.voz.vol : 0;
    const agora       = Date.now() / 200;

    barras.forEach((bar, i) => {
        const seno = Math.sin(agora + i * 0.5);
        const alt  = estaFalando
            ? 15 + volume * 70 + seno * 15
            : 8  + seno * 4;

        bar.style.height  = `${Math.max(5, Math.min(100, alt))}%`;
        bar.style.opacity = estaFalando ? '1' : '0.35';
        bar.style.filter  = estaFalando
            ? 'drop-shadow(0 0 8px var(--accent))'
            : 'none';
    });
}

setInterval(() => {
    if (state.page === PG.VOZ) atualizarMedidorVoz();
}, 50);

//  PÁGINA DE VOZ ──
function pgVoz(wrap) {
    const v    = state.voz;
    const apis = state.apis;

    /* Lista de microfones */
    const micsOpts = v.microfones.length
        ? v.microfones.map(m => {
            const idx = parseInt(String(m).split(':')[0], 10);
            const i   = Number.isFinite(idx) ? idx : 0;
            return `<option value="${i}" ${i === v.deviceIndex ? 'selected' : ''}>${esc(m)}</option>`;
        }).join('')
        : '<option value="0">Dispositivo padrão</option>';

    /* Voz Edge TTS selecionada */
    const vozAtual = apis.voz || 'pt-BR-AntonioNeural';

    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">PROTOCOLO DE VOZ</div>
                <div class="page-sub">Entrada, síntese e configuração de áudio</div>
            </div>
        </div>

        <!-- LINHA 1: Medidor + Status -->
        <div class="voice-layout">

            <!-- MEDIDOR -->
            <div class="card voice-meter-card">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
                <div class="voz-section-label">SINAL DE ÁUDIO</div>
                <div class="voz-meter" id="vozMeterBars">
                    ${Array.from({ length: 16 }, () => '<div class="voz-bar"></div>').join('')}
                </div>
                <div class="voz-status-line">
                    ${v.speaking
                        ? `<span class="voz-status-on">● PROCESSANDO VOZ</span>`
                        : `<span class="voz-status-off">○ SISTEMA EM ESPERA</span>`}
                </div>
            </div>

            <!-- CASCATA TTS -->
            <div class="card voz-cascade-card">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div class="voz-section-label">CASCATA DE SÍNTESE (TTS)</div>
                <div class="voz-cascade">
                    <div class="voz-cascade-step ${apis.fish_audio_api_key ? 'active' : ''}">
                        <div class="voz-cascade-rank">1</div>
                        <div>
                            <div class="voz-cascade-name">Fish Audio</div>
                            <div class="voz-cascade-desc">Clone de voz personalizado</div>
                        </div>
                        <div class="voz-cascade-dot ${apis.fish_audio_api_key ? 'ok' : ''}"></div>
                    </div>
                    <div class="voz-cascade-arrow">↓</div>
                    <div class="voz-cascade-step ${apis.openai_api_key ? 'active' : ''}">
                        <div class="voz-cascade-rank">2</div>
                        <div>
                            <div class="voz-cascade-name">OpenAI TTS</div>
                            <div class="voz-cascade-desc">${esc(apis.openai_tts_voice || 'nova')}</div>
                        </div>
                        <div class="voz-cascade-dot ${apis.openai_api_key ? 'ok' : ''}"></div>
                    </div>
                    <div class="voz-cascade-arrow">↓</div>
                    <div class="voz-cascade-step active always">
                        <div class="voz-cascade-rank">3</div>
                        <div>
                            <div class="voz-cascade-name">Edge TTS</div>
                            <div class="voz-cascade-desc">Fallback garantido</div>
                        </div>
                        <div class="voz-cascade-dot ok"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- LINHA 2: Dispositivo + Configurações -->
        <div class="voice-layout" style="margin-top:16px;">

            <!-- MICROFONE -->
            <div class="card" style="padding:22px;flex:1;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
                <div class="voz-section-label">DISPOSITIVO DE ENTRADA</div>
                <select class="input" id="selMicDev" style="width:100%;font-size:14px;margin-bottom:16px;">
                    ${micsOpts}
                </select>
                <button class="btn btn-accent" id="btnSaveVoz" style="width:100%;">💾 SALVAR DISPOSITIVO</button>
            </div>

            <!-- VOZ EDGE TTS -->
            <div class="card" style="padding:22px;flex:1;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div class="voz-section-label">VOZ EDGE TTS (FALLBACK)</div>
                <input class="input" id="edgeVoiceInput"
                       type="text"
                       value="${esc(vozAtual)}"
                       placeholder="pt-BR-AntonioNeural"
                       style="width:100%;margin-bottom:16px;"
                       oninput="state.apis.voz = this.value">
                <button class="btn btn-ghost" id="btnSaveEdge" style="width:100%;">💾 SALVAR VOZ</button>
            </div>

            <!-- TESTE -->
            <div class="card" style="padding:22px;flex:1;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
                <div class="voz-section-label">TESTE DE SÍNTESE</div>
                <div style="font-family:var(--mono);font-size:10px;color:var(--text3);letter-spacing:1.5px;margin-bottom:16px;line-height:1.7;">
                    Fish Audio → OpenAI nova → Edge TTS
                </div>
                <button class="btn btn-ghost" onclick="testarVoz()" style="width:100%;">
                    🎙 TESTAR SÍNTESE DE VOZ
                </button>
            </div>
        </div>

        <!-- CASCATA STT -->
        <div class="card" style="padding:22px;margin-top:16px;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
            <div class="voz-section-label" style="margin-bottom:14px;">CASCATA DE RECONHECIMENTO (STT)</div>
            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <div class="stt-step ${apis.deepgram_api_key ? 'ok' : ''}">
                    <div class="stt-rank">1</div>
                    <div>
                        <div class="stt-name">Deepgram Nova-3</div>
                        <div class="stt-lat">~300ms latência</div>
                    </div>
                </div>
                <div class="stt-arrow">→</div>
                <div class="stt-step ok always">
                    <div class="stt-rank">2</div>
                    <div>
                        <div class="stt-name">Google STT</div>
                        <div class="stt-lat">pt-BR</div>
                    </div>
                </div>
                <div class="stt-arrow">→</div>
                <div class="stt-step ok always">
                    <div class="stt-rank">3</div>
                    <div>
                        <div class="stt-name">Whisper Local</div>
                        <div class="stt-lat">${esc(apis.whisper_model || 'small')}</div>
                    </div>
                </div>
            </div>
        </div>

        <style>
            .voice-layout {
                display: flex;
                gap: 16px;
            }
            .voice-layout > .card { flex: 1; }
            .voice-meter-card { padding: 22px; }
            .voz-cascade-card { padding: 22px; flex: 1.2 !important; }

            .voz-section-label {
                font-family: var(--mono);
                font-size: 10px;
                font-weight: 700;
                color: var(--text3);
                letter-spacing: 3px;
                margin-bottom: 14px;
            }
            .voz-status-line { font-family: var(--mono); font-size: 11px; font-weight: 700; margin-top: 8px; }
            .voz-status-on  { color: var(--accent2); animation: pulse 1.5s infinite; }
            .voz-status-off { color: var(--text3); }

            /* Cascata TTS */
            .voz-cascade { display: flex; flex-direction: column; gap: 4px; }
            .voz-cascade-step {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 14px;
                border-radius: 8px;
                border: 1px solid var(--border);
                background: transparent;
                opacity: .45;
                transition: all .3s;
            }
            .voz-cascade-step.active { opacity: 1; border-color: var(--accent2)55; background: var(--accent2)08; }
            .voz-cascade-step.always { opacity: 1; border-color: var(--border); }
            .voz-cascade-rank {
                font-family: var(--mono);
                font-size: 11px;
                font-weight: 700;
                color: var(--text3);
                min-width: 18px;
            }
            .voz-cascade-name { font-size: 13px; font-weight: 700; }
            .voz-cascade-desc { font-family: var(--mono); font-size: 10px; color: var(--text3); letter-spacing: 1px; margin-top: 2px; }
            .voz-cascade-dot  { width: 8px; height: 8px; border-radius: 50%; background: var(--border); margin-left: auto; flex-shrink: 0; }
            .voz-cascade-dot.ok { background: var(--accent2); box-shadow: 0 0 6px var(--accent2); }
            .voz-cascade-arrow { font-family: var(--mono); font-size: 11px; color: var(--text3); padding-left: 24px; }

            /* Cascata STT */
            .stt-step {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 16px;
                border-radius: 8px;
                border: 1px solid var(--border);
                opacity: .45;
                transition: all .3s;
            }
            .stt-step.ok { opacity: 1; border-color: var(--accent)55; background: var(--accent)08; }
            .stt-rank { font-family: var(--mono); font-size: 11px; font-weight: 700; color: var(--text3); }
            .stt-name { font-size: 13px; font-weight: 700; }
            .stt-lat  { font-family: var(--mono); font-size: 10px; color: var(--text3); margin-top: 2px; letter-spacing: 1px; }
            .stt-arrow { font-family: var(--mono); font-size: 14px; color: var(--text3); }
        </style>
    `;

    /* Salvar device index */
    document.getElementById('btnSaveVoz')?.addEventListener('click', () => {
        if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
        const idx = parseInt(document.getElementById('selMicDev')?.value || '0', 10) || 0;
        window.jarvis.salvar_configuracao('device_index', String(idx));
        state.voz.deviceIndex = idx;
        toast('✓ Dispositivo de áudio salvo.');
    });

    /* Salvar voz Edge */
    document.getElementById('btnSaveEdge')?.addEventListener('click', () => {
        if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
        const voz = (document.getElementById('edgeVoiceInput')?.value || '').trim();
        if (!voz) return;
        window.jarvis.salvar_configuracao('voz', voz);
        toast('✓ Voz Edge TTS salva.');
    });

    atualizarMedidorVoz();
}

//  TESTE DE VOZ 
function testarVoz() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    window.jarvis.testar_voz_painel();
    toast('🎙 Testando síntese de voz...');
}