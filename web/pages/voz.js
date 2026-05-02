'use strict';







function atualizarMedidorVoz() {
    const wrap = document.getElementById('vozMeterBars');
    if (!wrap) return;

    const barras = wrap.querySelectorAll('.voz-bar');
    const estaFalando = state.voz.speaking;
    const volume = estaFalando ? state.voz.vol : 0;

    barras.forEach((bar, i) => {
        const tempo = Date.now() / 200;
        const seno = Math.sin(tempo + i * 0.5);
        
        let altura;
        if (estaFalando) {
            altura = 15 + (volume * 70) + (seno * 15);
        } else {
            altura = 8 + (seno * 4);
        }

        bar.style.height = `${Math.max(5, Math.min(100, altura))}%`;
        bar.style.opacity = estaFalando ? '1' : '0.4';
        bar.style.filter = estaFalando ? `drop-shadow(0 0 8px var(--accent))` : 'none';
    });
}







setInterval(() => {
    if (state.page === PG.VOZ) {
        atualizarMedidorVoz();
    }
}, 50);







function pgVoz(wrap) {
    const v = state.voz;
    const mics = v.microfones.length
        ? v.microfones.map(m => {
            const idx = parseInt(String(m).split(':')[0], 10);
            const safeIdx = Number.isFinite(idx) ? idx : 0;
            const sel = safeIdx === v.deviceIndex ? 'selected' : '';
            return `<option value="${safeIdx}" ${sel}>${esc(m)}</option>`;
        }).join('')
        : '<option value="0">Dispositivo padrão</option>';

    wrap.innerHTML = `

        <div class="page-header">
            <div>
                <div class="page-title">PROTOCOLO DE VOZ</div>
                <div class="page-sub">Entrada de áudio e processamento de síntese neural</div>
            </div>
        </div>

        <div class="voice-layout" style="display: flex; gap: 20px; margin-top: 20px;">
            <div class="card voice-meter-card" style="flex: 1;">
                <div class="card-accent" style="background: linear-gradient(90deg, var(--accent), transparent);"></div>
                <div style="font-family: var(--mono); font-size: 14px; letter-spacing: 2px; color: var(--text3);font-weight: 700;">SINAL DE ÁUDIO</div>
                
                <div class="voz-meter" id="vozMeterBars">
                    ${Array.from({ length: 16 }, () => '<div class="voz-bar"></div>').join('')}
                </div>
                
                <div style="font-family: var(--mono); font-size: 11px; font-weight: 700;">
                    ${v.speaking ? 
                        `<span style="color: var(--accent2); animation: pulse 1.5s infinite;">● PROCESSANDO VOZ</span>` : 
                        `<span style="color: var(--text3); font-weight: 700;">○ SISTEMA EM ESPERA</span>`}
                </div>
            </div>

            <div class="card" style="padding: 22px; flex: 1.5;">
                <div class="card-accent" style="background: linear-gradient(90deg, var(--accent2), transparent);"></div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-family: var(--mono); font-size: 10px; color: var(--text3); margin-bottom: 8px; font-size: 14px; font-weight: 700;">DISPOSITIVO DE ENTRADA</label>
                    <select class="input" id="selMicDev" style="width: 100%; font-weight: 700; font-size: 14px;">${mics}</select>
                </div>

                <div style="display: flex; gap: 12px;">
                    <button type="button" class="btn btn-accent" id="btnSaveVoz" style="flex: 1;">💾 SALVAR CONFIGURAÇÃO</button>
                    <button type="button" class="btn btn-ghost" onclick="enviarComando('teste de voz')" style="flex: 1;">▶ TESTAR SÍNTESE</button>
                </div>
            </div>
        </div>`;

    document.getElementById('btnSaveVoz')?.addEventListener('click', () => {
        if (!window.jarvis) { 
            toast('Bridge não conectada.', 'err'); 
            return; 
        }
        const idx = parseInt(document.getElementById('selMicDev')?.value || '0', 10) || 0;
        window.jarvis.salvar_configuracao('device_index', String(idx)); 
        state.voz.deviceIndex = idx;
        toast('Configurações de áudio salvas.');
    });

    atualizarMedidorVoz();
}