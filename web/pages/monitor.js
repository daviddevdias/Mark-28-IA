'use strict';







function processarEventoMonitor(ev) {
    const ts = new Date().toTimeString().slice(0, 8);
    const entrada = {
        ts,
        ok:             !!ev.ok,
        tipo:           ev.tipo   || 'normal',
        resumo:         ev.resumo || '',
        problema:       ev.problema || '',
        sugestao:       ev.sugestao_rapida || '',
    };

    state.monitor.ultimo_ok      = entrada.ok;
    state.monitor.ultimo_tipo    = entrada.tipo;
    state.monitor.ultimo_resumo  = entrada.resumo;
    state.monitor.total_capturas += 1;

    if (!entrada.ok) {
        state.monitor.total_alertas += 1;
        state.monitor.eventos.unshift(entrada);
        if (state.monitor.eventos.length > 50) state.monitor.eventos.pop();
        addLog('err', `[MONITOR] ${entrada.tipo.toUpperCase()}: ${entrada.resumo.slice(0,70)}`);
        mostrarAlertaFlutuante(entrada);
    }

    if (state.page === PG.MONITOR) {
        atualizarHeaderMonitor();
        renderEventosMonitor();
    }
}







function mostrarAlertaFlutuante(ev) {
    const cor   = TIPO_COR[ev.tipo]   || 'var(--red)';
    const icon  = TIPO_ICON[ev.tipo]  || '⚠️';

    let alerta = document.getElementById('monitorAlerta');
    if (!alerta) {
        alerta = document.createElement('div');
        alerta.id = 'monitorAlerta';
        alerta.style.cssText = `
            position:fixed; bottom:80px; right:24px; z-index:9999;
            background:var(--card); border:1px solid ${cor};
            border-radius:12px; padding:16px 20px; max-width:380px;
            box-shadow: 0 0 24px ${cor}44;
            font-family:var(--mono); animation: alertSlideIn .3s var(--ease);
            cursor:pointer;
        `;
        alerta.onclick = () => { navegarPara(PG.MONITOR); alerta.remove(); };
        document.body.appendChild(alerta);
    }






    

    alerta.style.borderColor = cor;
    alerta.style.boxShadow   = `0 0 24px ${cor}44`;
    alerta.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <span style="font-size:18px;">${icon}</span>
            <span style="font-size:10px;font-weight:700;letter-spacing:2px;color:${cor};">
                JARVIS DETECTOU · ${ev.tipo.toUpperCase()}
            </span>
            <span style="margin-left:auto;font-size:10px;color:var(--text3);">${ev.ts}</span>
        </div>
        <div style="font-size:13px;color:var(--text);line-height:1.5;margin-bottom:6px;">
            ${esc(ev.resumo.slice(0, 100))}
        </div>
        ${ev.sugestao ? `<div style="font-size:12px;color:${cor};font-weight:700;margin-top:4px;">
            → ${esc(ev.sugestao.slice(0, 80))}
        </div>` : ''}
        <div style="font-size:10px;color:var(--text3);margin-top:8px;letter-spacing:1px;">
            Clique para ver o painel de monitoramento
        </div>
    `;

    clearTimeout(alerta.timer);
    alerta.timer = setTimeout(() => {
        if (alerta.parentNode) {
            alerta.style.opacity = '0';
            alerta.style.transition = 'opacity .4s';
            setTimeout(() => alerta.remove(), 420);
        }
    }, 9000);
}







function exibirDicaMonitor(dica, tipo) {
    const cor  = TIPO_COR[tipo]  || 'var(--yellow)';
    const icon = TIPO_ICON[tipo] || '⚠️';

    let painel = document.getElementById('dicaFlutuante');
    if (!painel) {
        painel = document.createElement('div');
        painel.id = 'dicaFlutuante';
        painel.style.cssText = `
            position:fixed; bottom:80px; left:24px; z-index:9998;
            background:var(--card); border:1px solid ${cor};
            border-radius:12px; padding:18px 22px; max-width:420px;
            box-shadow: 0 0 30px ${cor}33;
            font-family:var(--mono); animation: alertSlideIn .3s var(--ease);
        `;
        document.body.appendChild(painel);
    }

    painel.style.borderColor = cor;
    painel.style.boxShadow   = `0 0 30px ${cor}33`;
    painel.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:20px;">${icon}</span>
            <span style="font-size:10px;font-weight:700;letter-spacing:2.5px;color:${cor};">
                DICA JARVIS — ${tipo.toUpperCase()}
            </span>
            <button onclick="document.getElementById('dicaFlutuante').remove()"
                    style="margin-left:auto;background:none;border:none;color:var(--text3);
                           cursor:pointer;font-size:16px;line-height:1;">✕</button>
        </div>
        <div style="font-size:13px;color:var(--text);line-height:1.6;">
            ${esc(dica).replace(/\n/g,'<br>')}
        </div>
        <div style="margin-top:12px;display:flex;gap:8px;">
            <button class="btn btn-accent" style="font-size:11px;padding:6px 14px;"
                    onclick="navegarPara(window.PG.MONITOR);document.getElementById('dicaFlutuante').remove();">
                VER MONITOR
            </button>
            <button class="btn btn-ghost" style="font-size:11px;padding:6px 14px;"
                    onclick="document.getElementById('dicaFlutuante').remove();">
                DISPENSAR
            </button>
        </div>
    `;

    clearTimeout(painel.timer);
    painel.timer = setTimeout(() => {
        if (painel.parentNode) {
            painel.style.opacity = '0';
            painel.style.transition = 'opacity .5s';
            setTimeout(() => painel.remove(), 520);
        }
    }, 20000);
}







function pgMonitor(wrap) {
    const m = state.monitor;

    wrap.innerHTML = `
        <div class="page-header" style="margin-bottom:16px;">
            <div>
                <div class="page-title">MONITORAMENTO INTELIGENTE</div>
                <div class="page-sub">Visão computacional em tempo real via Qwen VL</div>
            </div>
            <div style="display:flex;gap:10px;align-items:center;">
                <div id="monitorBadge" style="
                    font-family:var(--mono);font-size:14px;font-weight:700;
                    letter-spacing:2px;padding:6px 14px;border-radius:20px;
                    border:1px solid var(--border);color:var(--text3);
                    background:var(--surface);">
                    ${m.ativo ? `<span style="color:var(--accent2);">● ATIVO</span>` : `<span style="color:var(--text3);">○ INATIVO</span>`}
                </div>
                <button class="btn btn-accent" id="btnToggleMonitor"
                        onclick="toggleMonitor()"
                        style="min-width:120px;">
                    ${m.ativo ? '⏹ PARAR' : '▶ INICIAR'}
                </button>
                <select id="monitorIntervalo" class="input" style="width:110px;padding:8px 10px;"
                        onchange="state.monitor.intervalo=parseInt(this.value)">
                    <option value="5"  ${m.intervalo===5?'selected':''}>5 s</option>
                    <option value="8"  ${m.intervalo===8?'selected':''}>8 s</option>
                    <option value="10" ${m.intervalo===10?'selected':''}>10 s</option>
                    <option value="15" ${m.intervalo===15?'selected':''}>15 s</option>
                    <option value="30" ${m.intervalo===30?'selected':''}>30 s</option>
                </select>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr; gap:12px; margin-bottom:16px; font-size: 12px; font-weight:700;">
            ${monStatCard('CAPTURAS',  m.total_capturas, 'var(--accent)',  '📸')}
            ${monStatCard('ALERTAS',   m.total_alertas,  m.total_alertas > 0 ? 'var(--red)' : 'var(--accent2)', '🔴')}
            ${monStatCard('INTERVALO', m.intervalo + 's', 'var(--yellow)', '⏱')}
            ${monStatCard('STATUS',    m.ativo ? 'ATIVO' : 'PARADO', m.ativo ? 'var(--accent2)' : 'var(--text3)', m.ativo ? '⬡' : '○')}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr; gap:14px;margin-bottom:14px;">
            <div class="card" style="padding:18px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>

                <div style="font-family:var(--mono); font-size:14px; font-weight:700;    

                     color:var(--text3);letter-spacing:3px; margin-bottom:14px; margin-top:4px;">
                     ÚLTIMA ANÁLISE
                </div>
                <div id="monitorUltima" style="font-size:13px;color:var(--text);line-height:1.6;min-height:60px;">


                    ${m.ultimo_resumo
                        ? `<span style="color:${m.ultimo_ok ? 'var(--accent2)' : 'var(--red)'};">
                               ${TIPO_ICON[m.ultimo_tipo]||'◈'} ${esc(m.ultimo_resumo)}
                           </span>`
                        : `<span style="color:var(--text3);">Aguardando primeira análise...</span>`}
                </div>
            </div>
            <div class="card" style="padding:18px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="font-family:var(--mono);font-size:14px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;margin-bottom:14px;margin-top:4px;">
                     ÚLTIMA DICA JARVIS
                </div>
                <div id="monitorUltimaDica" style="font-size:13px;color:var(--text);line-height:1.6;min-height:60px;">
                    ${m.ultima_dica
                        ? `<span style="color:var(--yellow);">${esc(m.ultima_dica).replace(/\n/g,'<br>')}</span>`
                        : `<span style="color:var(--text3);">Nenhuma dica gerada ainda.</span>`}
                </div>
            </div>
        </div>

        <div class="card" style="padding:18px;flex:1;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--red),transparent);"></div>
            <div style="display:flex;align-items:center;justify-content:space-between;
                 margin-bottom:14px;margin-top:4px;">
                <div style="font-family:var(--mono);font-size:14px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;">
                     HISTÓRICO DE ALERTAS
                </div>
                <button class="btn btn-ghost" style="font-size:11px;padding:5px 12px;"
                        onclick="limparEventosMonitor()">
                    🗑 LIMPAR
                </button>
            </div>
            <div id="monitorEventos" style="max-height:260px;overflow-y:auto;">
                ${renderEventosMonitorHTML()}
            </div>
        </div>
    `;
}







function monStatCard(label, val, cor, icon) {
    return `
        <div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:8px;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:2.5px;">${icon} ${label}</div>
            <div style="font-family:var(--orb,var(--mono));font-size:22px;
                 font-weight:700;color:${cor};">${val}</div>
        </div>`;
}







function renderEventosMonitorHTML() {
    if (!state.monitor.eventos.length) {
        return `<div style="text-align:center;padding:40px;color:var(--text3);
                     font-family:var(--mono);font-size:14px;letter-spacing:2px; font-weight:700;">
                    Nenhum alerta detectado nesta sessão.
                </div>`;
    }

    return state.monitor.eventos.map(ev => {
        const cor  = TIPO_COR[ev.tipo]  || 'var(--text3)';
        const icon = TIPO_ICON[ev.tipo] || '◈';

        return `
            <div style="
                padding:12px 14px;margin-bottom:8px;border-radius:8px;
                border:1px solid ${cor}33;background:${cor}08;
                border-left:3px solid ${cor};
            ">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="font-size:14px;">${icon}</span>
                    <span style="font-family:var(--mono);font-size:10px;font-weight:700;
                          color:${cor};letter-spacing:1.5px;">${ev.tipo.toUpperCase()}</span>
                    <span style="margin-left:auto;font-family:var(--mono);font-size:10px;
                          color:var(--text3);">${ev.ts}</span>
                </div>
                <div style="font-size:13px;color:var(--text);margin-bottom:4px;">
                    ${esc(ev.resumo)}
                </div>
                ${ev.sugestao ? `
                <div style="font-size:12px;color:${cor};font-weight:600;margin-top:4px;">
                    → ${esc(ev.sugestao)}
                </div>` : ''}
            </div>`;
    }).join('');
}







function renderEventosMonitor() {
    const el = document.getElementById('monitorEventos');
    if (el) el.innerHTML = renderEventosMonitorHTML();
}







function atualizarHeaderMonitor() {
    const badge = document.getElementById('monitorBadge');
    const btn   = document.getElementById('btnToggleMonitor');
    const m     = state.monitor;

    if (badge) {
        badge.innerHTML = m.ativo
            ? `<span style="color:var(--accent2);">● ATIVO</span>`
            : `<span style="color:var(--text3);">○ INATIVO</span>`;
    }

    if (btn) {
        btn.textContent = m.ativo ? '⏹ PARAR' : '▶ INICIAR';
    }

    const ultima = document.getElementById('monitorUltima');
    if (ultima && m.ultimo_resumo) {
        const cor = m.ultimo_ok ? 'var(--accent2)' : 'var(--red)';
        ultima.innerHTML = `<span style="color:${cor};">
            ${TIPO_ICON[m.ultimo_tipo]||'◈'} ${esc(m.ultimo_resumo)}
        </span>`;
    }

    const dica = document.getElementById('monitorUltimaDica');
    if (dica && m.ultima_dica) {
        dica.innerHTML = `<span style="color:var(--yellow);">
            ${esc(m.ultima_dica).replace(/\n/g,'<br>')}
        </span>`;
    }

    const s1 = document.querySelector('[data-stat="capturas"]');
    const s2 = document.querySelector('[data-stat="alertas"]');
    if (s1) s1.textContent = m.total_capturas;
    if (s2) s2.textContent = m.total_alertas;
}







function toggleMonitor() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }

    if (state.monitor.ativo) {
        enviarComando('desligar monitoramento');
        state.monitor.ativo = false;
    } else {
        const intervalo = state.monitor.intervalo || 8;
        enviarComando(`monitorar tela ${intervalo}`);
        state.monitor.ativo = true;
    }

    if (state.page === PG.MONITOR) {
        setTimeout(() => {
            if (state.page === PG.MONITOR) renderPage();
        }, 300);
    }
}







function limparEventosMonitor() {
    state.monitor.eventos       = [];
    state.monitor.total_alertas = 0;
    renderEventosMonitor();
    toast('Histórico de alertas limpo.');
}