'use strict';

function pgDash(wrap) {
    const m = state.metricas;

    

    wrap.innerHTML = `
        <div class="dash-grid">
            ${metricCard('CPU',        'v-cpu','p-cpu', Math.round(m.cpu)+'%', m.cpu, 'var(--accent)')}
            ${metricCard('MEMÓRIA RAM','v-ram','p-ram', Math.round(m.ram)+'%', m.ram, 'var(--accent)')}
            ${metricCard('GPU',        'v-gpu','p-gpu', Math.round(m.gpu)+'%', m.gpu, 'var(--orange)')}
        </div>

        <div class="dash-bottom">
            <div class="card" style="padding:24px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),var(--accent2));"></div>
                <div style="margin-top:8px;">
                    <div style="font-family:var(--mono);font-size:11px;font-weight:700;
                         color:var(--text3);letter-spacing:3px;margin-bottom:20px;">
                         ESPECIFICAÇÕES DO SISTEMA
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                        ${spec('DISCO USO',  Math.round(m.disco)+'%')}
                        ${spec('FREQ CPU',   m.freq+' MHz')}
                        ${spec('RAM EM USO', m.ram_usada+' / '+m.ram_total+' GB')}
                        ${spec('GPU TEMP',   m.gpu_temp+'°C')}
                        ${spec('LATÊNCIA',   m.ping+' ms')}
                        ${spec('UPTIME',     uptime())}
                        ${spec('DOWNLOAD',   m.net_in+' MB/s')}
                        ${spec('UPLOAD',     m.net_out+' MB/s')}
                    </div>
                </div>
            </div>

            <div class="card" style="padding:24px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="font-family:var(--mono);font-size:11px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;margin-bottom:16px;margin-top:8px;">
                     LOG DE ATIVIDADE
                </div>
                <div class="log-stream" id="logStream"></div>
            </div>
        </div>

        <div class="quick-grid">
            ${quickBtn('⛨','BLOQUEAR TELA', 'bloquear',       'var(--purple)', 'rgba(136,85,0,.07)')}
            ${quickBtn('⌾','CAPTURAR TELA', 'captura')}
            ${quickBtn('⌦','LIMPAR LIXEIRA','limpar lixeira', 'var(--red)',    'rgba(255,34,85,.06)')}
            ${quickBtn('▣','MINIMIZAR TUDO','minimizar',      'var(--accent2)','rgba(255,106,0,.07)')}
            ${quickBtn('⨯','FECHAR JANELA', 'fechar',         'var(--orange)', 'rgba(255,122,0,.06)')}
            ${quickBtn('⌁','MODO TRABALHO', 'trabalho',       'var(--yellow)', 'rgba(255,199,0,.06)')}
        </div>
    `;

    renderLog();
    updateMetrics();
}
diags



function metricCard(lbl, idV, idP, val, pct, cor) {
    const col = pct > 85 ? 'var(--red)' : pct > 65 ? 'var(--orange)' : cor;
    return `
        <div class="metric-card">
            <div class="card-accent" style="background:linear-gradient(90deg,${col},transparent);"></div>
            <div class="metric-label" style="margin-top:8px;">${lbl}</div>
            <div class="metric-val" id="${idV}" style="color:${col};">${val}</div>
            <div class="metric-bar">
                <div class="metric-fill" id="${idP}"
                     style="width:${pct}%;background:linear-gradient(90deg,${col},${col}88);box-shadow:0 0 12px ${col}66;"></div>
            </div>
        </div>`;
}



function spec(k, v) {
    return `
        <div class="spec-block">
            <div class="spec-label">${k}</div>
            <div class="spec-val">${v}</div>
        </div>`;
}



function quickBtn(icon, label, cmd, col, bg) {
    return `
        <div class="quick-btn" style="--hover-col:${bg};color:${col};border-color:var(--border);"
             onclick="${cmd === 'fechar' ? 'ocultarPainelQt()' : `enviarComando('${cmd}')`}"
             onmouseover="this.style.borderColor='${col}55'"
             onmouseout="this.style.borderColor='var(--border)'">
            <span class="quick-icon">${icon}</span>
            <span class="quick-label" style="color:${col};">${label}</span>
        </div>`;
}




function ocultarPainelQt() {
    try {
        if (window.jarvis?.ocultar_painel) { window.jarvis.ocultar_painel(); return; }
    } catch(e) {}
    toast('Bridge não conectada.', 'warn');
}




function uptime() {
    const s = Math.floor((Date.now() - state.metricas.uptime_start) / 1000);
    return `${zp(Math.floor(s/3600))}:${zp(Math.floor((s%3600)/60))}:${zp(s%60)}`;
}

function updateMetrics() {
    const m = state.metricas;
    const setV  = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    const setW  = (id, p) => { const e = document.getElementById(id); if (e) { e.style.width = p+'%'; e.style.boxShadow = `0 0 12px ${e.style.background.split(',')[0].replace('linear-gradient(90deg','').trim()}66`; } };
    const setC  = (id, c) => { const e = document.getElementById(id); if (e) e.style.color = c; };

    const cpuC = m.cpu > 85 ? 'var(--red)' : m.cpu > 65 ? 'var(--orange)' : 'var(--accent)';
    setV('v-cpu', Math.round(m.cpu)+'%'); setW('p-cpu', m.cpu); setC('v-cpu', cpuC);

    const ramC = m.ram > 85 ? 'var(--red)' : m.ram > 70 ? 'var(--orange)' : 'var(--accent)';
    setV('v-ram', Math.round(m.ram)+'%'); setW('p-ram', m.ram); setC('v-ram', ramC);

    const gpuC = m.gpu > 85 ? 'var(--red)' : m.gpu > 65 ? 'var(--orange)' : 'var(--orange)';
    setV('v-gpu', Math.round(m.gpu)+'%'); setW('p-gpu', m.gpu); setC('v-gpu', gpuC);
}