'use strict';







function pgVisao(wrap) {
    wrap.innerHTML = `
        <style>
            .vision-wrap { animation: pageEnter 0.3s ease-out both; display: flex; flex-direction: column; gap: 8px; max-height: 800px; }
            .vision-main { display: grid; grid-template-columns: 1.4fr 1fr; gap: 8px; height: 540px; }
            .canvas-view {
                background: #000; border: 1px solid var(--border); border-radius: 8px;
                position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center;
            }
            .scan-line {
                position: absolute; top: 0; left: 0; width: 100%; height: 2px;
                background: var(--accent); box-shadow: 0 0 10px var(--accent);
                opacity: 0.7; display: none; z-index: 5;
            }
            @keyframes scanline { 0% { transform: translateY(0); } 100% { transform: translateY(340px); } }
            .vision-card {
                background: var(--card); border: 1px solid var(--border); border-radius: 8px;
                padding: 12px; display: flex; flex-direction: column; gap: 6px; overflow: hidden;
            }
            .vision-results {
                flex: 1; overflow-y: auto; font-family: var(--mono); font-size: 11px;
                color: var(--text2); line-height: 1.5; border-top: 1px solid rgba(255,255,255,0.05);
                padding-top: 8px; word-break: break-word;
            }
            .vision-corner { position: absolute; width: 10px; height: 10px; border: 1px solid var(--accent); opacity: 0.4; }
            .vision-status-bar {
                display: flex; align-items: center; gap: 8px;
                font-family: var(--mono); font-size: 8px; color: var(--text3);
                letter-spacing: 1px; padding: 0 2px;
            }
            .vision-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text3); }
            .vision-dot.ok { background: var(--accent2); box-shadow: 0 0 6px var(--accent2); }
            .vision-dot.err { background: var(--red); box-shadow: 0 0 6px var(--red); }
            .vision-dot.scanning { background: var(--accent); animation: pulse 0.8s infinite; }
        </style>

        <div class="vision-wrap">
            <div class="page-header" style="padding: 0 4px; margin-bottom: 4px;">
                <div style="flex: 1;">
                    <div class="page-title" style="font-size: 18px; letter-spacing: 2px;">◬ OPTICAL_SCANNER</div>
                    <div class="page-sub" style="font-size: 16px;">QWEN_VL MULTIMODAL SENSOR</div>
                </div>
                <button class="btn btn-ghost" onclick="renderPage()" style="padding: 3px 8px; font-size: 8px;">RESET</button>
            </div>

            <div class="vision-main">
                <div class="canvas-view" id="visaoCanvas">
                    <div class="vision-corner" style="top:6px; left:6px; border-width: 1px 0 0 1px;"></div>
                    <div class="vision-corner" style="top:6px; right:6px; border-width: 1px 1px 0 0;"></div>
                    <div class="vision-corner" style="bottom:6px; left:6px; border-width: 0 0 1px 1px;"></div>
                    <div class="vision-corner" style="bottom:6px; right:6px; border-width: 0 1px 1px 0;"></div>
                    <div class="scan-line" id="visaoScanner"></div>
                    <div id="visaoLoader" style="
                        font-family: var(--mono); color: var(--accent); font-size: 14px;
                        letter-spacing: 1.5px; text-align: center; z-index: 10; padding: 16px;
                    ">IDLE_STANDBY</div>
                    <img id="visaoFrame" src="" style="
                        display: none; max-width: 98%; max-height: 98%;
                        border-radius: 4px; filter: brightness(1.05) contrast(1.08);
                        object-fit: contain;
                    " />
                </div>

                <div class="vision-card">
                    <div style="font-family: var(--mono); font-size: 14px; color: var(--text3); letter-spacing: 2px; font-weight: 700;">
                        NEURAL_DIAGNOSTICS
                    </div>
                    <div id="visaoStatusBar" class="vision-status-bar">
                        <div class="vision-dot" id="visaoDot"></div>
                        <span id="visaoStatusLabel" style="font-size: 14px;font-weight: 700;" >AGUARDANDO</span>
                    </div>
                    <div id="visaoResultado" class="vision-results">
                        <span style="opacity: 0.3; font-size: 14px; font-weight: 700;">Aguardando varredura neural...</span>
                    </div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 4px 2px;">
                <button class="btn btn-accent"
                    onclick="iniciarAnaliseVisual('Analise detalhadamente a tela e identifique o que está sendo exibido.')"
                    style="font-size: 9px; padding: 7px;">
                    ◈ FULL_SCAN
                </button>
                <button class="btn btn-ghost"
                    onclick="iniciarAnaliseVisual('Extraia todo o texto visível na tela.')"
                    style="font-size: 9px; padding: 7px;">
                    ⬡ OCR_EXTRACT
                </button>
                <button class="btn btn-ghost"
                    onclick="iniciarAnaliseVisual('Identifique erros, exceções, crashes ou avisos visíveis na tela.')"
                    style="font-size: 9px; padding: 7px; border-color: var(--red); color: var(--red);">
                    ✕ BUG_CHECK
                </button>
            </div>
        </div>`;

    const frame = document.getElementById('visaoFrame');
    
    if (frame) frame.style.display = 'none';
}
window.pgVisao = pgVisao;







function iniciarAnaliseVisual(promptCustomizado) {
    if (!window.jarvis) { toast('ERR: NO_BRIDGE', 'err'); return; }


    const loader  = document.getElementById('visaoLoader');
    const scanner = document.getElementById('visaoScanner');
    const res     = document.getElementById('visaoResultado');
    const frame   = document.getElementById('visaoFrame');
    const dot     = document.getElementById('visaoDot');
    const label   = document.getElementById('visaoStatusLabel');

    if (frame)   { frame.style.display = 'none'; }


    if (scanner) { scanner.style.display = 'block'; scanner.style.animation = 'scanline 1.8s linear infinite'; }


    if (loader)  { loader.style.display = 'block'; loader.textContent = 'LINKING_NEURAL_CORE...'; }


    if (dot)     { dot.className = 'vision-dot scanning'; }


    if (label)   { label.textContent = 'SCANNING...'; }


    if (res)     { res.innerHTML = '<div style="color:var(--accent); animation: pulse 1s infinite; font-size:14px;">● ANALYZING_STREAM...</div>'; }


    const promptFinal = promptCustomizado || 'Descreva a tela.';

    setTimeout(() => {
        if (window.jarvis.solicitar_analise_visual_com_prompt) {
            window.jarvis.solicitar_analise_visual_com_prompt(promptFinal);
        } else {
            window.jarvis.solicitar_analise_visual();
        }
    }, 100);
}
window.iniciarAnaliseVisual = iniciarAnaliseVisual;







function finalizarAnaliseVisual(imgBase64, textoResultado) {
    const frame   = document.getElementById('visaoFrame');
    const loader  = document.getElementById('visaoLoader');
    const scanner = document.getElementById('visaoScanner');
    const res     = document.getElementById('visaoResultado');
    const dot     = document.getElementById('visaoDot');
    const label   = document.getElementById('visaoStatusLabel');

    if (loader)  { loader.style.display = 'none'; }


    if (scanner) { scanner.style.display = 'none'; scanner.style.animation = 'none'; }


    if (frame && imgBase64) {
        const cleanB64 = imgBase64.trim();
        frame.src = cleanB64.startsWith('data:') ? cleanB64 : 'data:image/jpeg;base64,' + cleanB64;
        frame.style.display = 'block';
        const ldr = document.getElementById('visaoLoader');
        
        if (ldr) ldr.style.display = 'none';
    }


    if (!res) return;


    let dados = null;

    if (typeof textoResultado === 'object' && textoResultado !== null) {
        dados = textoResultado;
    } else {
        try {
            let limpo = String(textoResultado).trim();
            limpo = limpo.replace(/^```(?:json)?|```$/gm, '').trim();
            const inicio = limpo.indexOf('{');
            const fim    = limpo.lastIndexOf('}') + 1;
            
            if (inicio >= 0 && fim > inicio) limpo = limpo.slice(inicio, fim);


            dados = JSON.parse(limpo);
        } catch (e) {
            dados = null;
        }
    }


    if (dados) {
        if (dados.ok) {
            if (dot)   { dot.className = 'vision-dot ok'; }


            if (label) { label.textContent = 'SYSTEM_NOMINAL'; }


            res.innerHTML = `
                <div style="color:var(--accent2);font-weight:700;font-size:14px;letter-spacing:1.5px;margin-bottom:8px;">
                    ● SYSTEM_NOMINAL
                </div>
                <div style="color:var(--text);font-size:14px;line-height:1.6;margin-bottom:8px;font-weight:700;">
                    ${esc(dados.resumo || 'Sem anomalias detectadas.')}
                </div>
                <div style="font-size:14px;color:var(--text3);font-family:var(--mono);letter-spacing:1px;
                     padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);">
                    TYPE › ${(dados.tipo || 'normal').toUpperCase()}
                </div>
            `;
        } else {
            if (dot)   { dot.className = 'vision-dot err'; }


            if (label) { label.textContent = 'ANOMALY_DETECTED'; }


            res.innerHTML = `
                <div style="color:var(--red);font-weight:700;font-size:14px;letter-spacing:1.5px;margin-bottom:8px;">
                    ✕ ANOMALY_DETECTED › ${(dados.tipo || 'erro').toUpperCase()}
                </div>
                <div style="color:var(--text);font-size:14px;line-height:1.6;margin-bottom:10px;">
                    ${esc(dados.problema || dados.resumo || 'Anomalia detectada.')}
                </div>
                ${dados.sugestao_rapida ? `
                <div style="
                    font-size:14px;color:var(--red);font-weight:600;
                    padding:8px 10px;background:rgba(255,50,50,0.08);
                    border-left:2px solid var(--red);border-radius:4px;
                    line-height:1.5;
                ">
                    → ${esc(dados.sugestao_rapida)}
                </div>` : ''}
                <div style="font-size:12px;color:var(--text3);font-family:var(--mono);letter-spacing:1px;
                font-weight:600; padding-top:8px;margin-top:8px;border-top:1px solid rgba(255,255,255,0.05);">
                    TYPE › ${(dados.tipo || 'erro').toUpperCase()}
                </div>
            `;
        }
    } else {
        if (dot)   { dot.className = 'vision-dot ok'; }


        if (label) { label.textContent = 'SCAN_COMPLETE'; }


        res.innerHTML = `<div style="font-size:14px;color:var(--text);line-height:1.6;">${esc(String(textoResultado || '')).replace(/\n/g,'<br>')}</div>`;
    }

    toast('SCAN_COMPLETE');
}
window.finalizarAnaliseVisual = finalizarAnaliseVisual;







function receberVisaoDoBackend(payload) {
    if (!payload) return;


    if (payload.visao_status) {
        const loader = document.getElementById('visaoLoader');
        
        if (loader) { loader.style.display = 'block'; loader.textContent = payload.visao_status; }
    }


    if (payload.visao_erro) {
        const res = document.getElementById('visaoResultado');
        const dot = document.getElementById('visaoDot');
        const label = document.getElementById('visaoStatusLabel');
        
        if (dot)   dot.className = 'vision-dot err';


        if (label) label.textContent = 'ERROR';


        if (res)   res.innerHTML = `<div style="color:var(--red);font-size:14px;">✕ ${esc(payload.visao_erro)}</div>`;


        const scanner = document.getElementById('visaoScanner');
        const loader  = document.getElementById('visaoLoader');
        
        if (scanner) { scanner.style.display = 'none'; scanner.style.animation = 'none'; }


        if (loader)  { loader.style.display = 'none'; }


        toast('VISION_ERROR', 'err');
        return;
    }

    const temImg      = !!payload.visao_img;
    const temResultado = payload.visao_resultado !== undefined && payload.visao_resultado !== null;

    if (temImg || temResultado) {
        finalizarAnaliseVisual(
            temImg ? payload.visao_img : '',
            temResultado ? payload.visao_resultado : ''
        );
    }
}
window.receberVisaoDoBackend = receberVisaoDoBackend;