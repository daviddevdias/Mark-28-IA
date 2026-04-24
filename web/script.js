'use strict';

const PAGES = [
    { id: 'weather',  label: 'CLIMA',        icon: '◎'  },
    { id: 'dash',     label: 'DIAGNÓSTICO',  icon: '◉'  },
    { id: 'visao',    label: 'VISÃO IA',     icon: '👁️' },
    { id: 'monitor',  label: 'MONITOR',      icon: '⬡'  },
    { id: 'chat',     label: 'CHAT IA',      icon: '◈'  },
    { id: 'notas',    label: 'NOTAS',        icon: '◑'  },
    { id: 'ia',       label: 'MODELO',       icon: '◒'  },
    { id: 'config',   label: 'CONFIG',       icon: '⊙'  },
    { id: 'temas',    label: 'VISUAL',       icon: '◓'  },
];

const state = {
    page: 0,
    theme: '',
    themes: {},
    notas: '',
    apis: { gemini: '', qwen: '', smartthings: '', spotify_id: '', spotify_sec: '', nome_mestre: '', cidade_padrao: '' },
    ia: { modo: 'ollama', modelo: '', ollama: false },
    configEdit: false,

    metricas: {
        cpu: 28, ram: 42, gpu: 15, disco: 55,
        net_in: 0.4, net_out: 0.1, ping: 24,
        freq: 3400, gpu_temp: 48, ram_usada: 6.7, ram_total: 16, disco_livre: 225,
        uptime_start: Date.now(),
        _cpu_raw: 28, _ram_raw: 42, _gpu_raw: 15,
    },

    logs: [],
    chatHist: [],

    weather: {
        city: 'São Paulo',
        temp: null, desc: null, icon: '🌤',
        feels: null, humidity: null, wind: null,
        uv: null, pressure: null, vis: null,
        loading: true, error: null, forecast: [],
    },

    monitor: {
        ativo: false,
        intervalo: 8,
        eventos: [],
        ultimo_ok: true,
        ultimo_tipo: 'normal',
        ultimo_resumo: '',
        ultima_dica: '',
        total_alertas: 0,
        total_capturas: 0,
    },

    konami: [],
    _bridgeReady: false,
};

const WX_ICONS = {
    'Clear':'☀️','Sunny':'☀️','Clouds':'☁️','Overcast':'⛅',
    'Rain':'🌧️','Drizzle':'🌦️','Thunderstorm':'⛈️',
    'Snow':'❄️','Sleet':'🌨️','Mist':'🌫️','Fog':'🌫️',
    'Haze':'🌫️','Tornado':'🌪️','Partly cloudy':'⛅',
    'Blizzard':'🌨️','default':'🌡️',
};

const TIPO_COR = {
    normal:      'var(--accent2)',
    erro:        'var(--red)',
    crash:       'var(--red)',
    travado:     'var(--orange)',
    aviso:       'var(--yellow)',
    instalacao:  'var(--accent)',
    compilacao:  'var(--accent)',
    terminal:    'var(--purple)',
    codigo:      'var(--accent2)',
    navegador:   'var(--accent)',
    outro:       'var(--text3)',
};

const TIPO_ICON = {
    normal:      '✅',
    erro:        '🔴',
    crash:       '💥',
    travado:     '🟠',
    aviso:       '⚠️',
    instalacao:  '📦',
    compilacao:  '⚙️',
    terminal:    '💻',
    codigo:      '🔧',
    navegador:   '🌐',
    outro:       '◈',
};


function receberDoJarvis(data) {
    if (data.cpu !== undefined) {
        state.metricas._cpu_raw = data.cpu;
        state.metricas._ram_raw = data.ram;
        if (state.page === 1) _updateMetrics();
    }

    if (data.resposta) {
        const s = String(data.resposta).slice(0, 120);
        addLog('ok', s);
        toast(s.slice(0, 90));
        if (state.chatHist.length && state.chatHist[state.chatHist.length - 1]?.role === 'user') {
            document.getElementById('typingIndicator')?.remove();
            state.chatHist.push({ role: 'jarvis', text: s });
            if (state.page === 4) _renderChat();
        }
    }

    if (data.erro) {
        addLog('err', String(data.erro).slice(0, 120));
        toast(String(data.erro).slice(0, 90), 'err');
    }

    if (data.ia_status) {
        state.ia = {
            modo:   data.ia_status.modo   || state.ia.modo,
            modelo: data.ia_status.modelo || '',
            ollama: !!data.ia_status.ollama,
        };
        _updateIABadge();
        if (state.page === 6) renderPage();
    }

    if (data.visao_status) {
        const el = document.getElementById('visaoLoader');
        if (el) el.textContent = data.visao_status;
        toast(data.visao_status);
    }

    if (data.visao_img) {
        const frame  = document.getElementById('visaoFrame');
        const loader = document.getElementById('visaoLoader');
        if (frame && loader) {
            loader.style.display = 'none';
            frame.src = 'data:image/jpeg;base64,' + data.visao_img;
            frame.style.display = 'block';
        }
    }

    if (data.visao_resultado) {
        const el = document.getElementById('visaoResultado');
        if (el) el.innerHTML = esc(data.visao_resultado).replace(/\n/g, '<br>');
        addLog('ok', 'Análise visual concluída.');
    }

    if (data.visao_erro) {
        toast(data.visao_erro, 'err');
        const el = document.getElementById('visaoResultado');
        if (el) el.innerHTML = `<span style="color:var(--red);">ERRO: ${esc(data.visao_erro)}</span>`;
    }

    if (data.monitor_status) {
        state.monitor.ativo = data.monitor_status === 'ativo';
        if (data.monitor_intervalo) state.monitor.intervalo = data.monitor_intervalo;
        if (state.page === 3) _atualizarHeaderMonitor();
        addLog(state.monitor.ativo ? 'ok' : 'warn',
               state.monitor.ativo ? `Monitor ativo (${state.monitor.intervalo}s)` : 'Monitor desativado.');
    }

    if (data.monitor_evento) {
        _processarEventoMonitor(data.monitor_evento);
    }

    if (data.monitor_dica) {
        state.monitor.ultima_dica = data.monitor_dica;
        _exibirDicaMonitor(data.monitor_dica, data.monitor_tipo || state.monitor.ultimo_tipo);
        addLog('warn', 'Dica Jarvis: ' + data.monitor_dica.slice(0, 80));
    }

    if (data.clima_dados) {
        state.weather.loading = false;
        if (data.clima_dados.error) {
            state.weather.error = data.clima_dados.error;
            _renderWeatherError();
        } else {
            _parseWeatherData(data.clima_dados, data.cidade_buscada);
        }
    }
}


function _processarEventoMonitor(ev) {
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
        _mostrarAlertaFlutuante(entrada);
    }

    if (state.page === 3) {
        _atualizarHeaderMonitor();
        _renderEventosMonitor();
    }
}


function _mostrarAlertaFlutuante(ev) {
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
        alerta.onclick = () => { navegarPara(3); alerta.remove(); };
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

    clearTimeout(alerta._t);
    alerta._t = setTimeout(() => {
        if (alerta.parentNode) {
            alerta.style.opacity = '0';
            alerta.style.transition = 'opacity .4s';
            setTimeout(() => alerta.remove(), 420);
        }
    }, 9000);
}


function _exibirDicaMonitor(dica, tipo) {
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
                    onclick="navegarPara(3);document.getElementById('dicaFlutuante').remove();">
                VER MONITOR
            </button>
            <button class="btn btn-ghost" style="font-size:11px;padding:6px 14px;"
                    onclick="document.getElementById('dicaFlutuante').remove();">
                DISPENSAR
            </button>
        </div>
    `;

    clearTimeout(painel._t);
    painel._t = setTimeout(() => {
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
                    font-family:var(--mono);font-size:10px;font-weight:700;
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

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px;">
            ${_monStatCard('CAPTURAS',  m.total_capturas, 'var(--accent)',  '📸')}
            ${_monStatCard('ALERTAS',   m.total_alertas,  m.total_alertas > 0 ? 'var(--red)' : 'var(--accent2)', '🔴')}
            ${_monStatCard('INTERVALO', m.intervalo + 's', 'var(--yellow)', '⏱')}
            ${_monStatCard('STATUS',    m.ativo ? 'ATIVO' : 'PARADO', m.ativo ? 'var(--accent2)' : 'var(--text3)', m.ativo ? '⬡' : '○')}
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">

            <div class="card" style="padding:18px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;margin-bottom:14px;margin-top:4px;">
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
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;
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
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;">
                     HISTÓRICO DE ALERTAS
                </div>
                <button class="btn btn-ghost" style="font-size:11px;padding:5px 12px;"
                        onclick="limparEventosMonitor()">
                    🗑 LIMPAR
                </button>
            </div>
            <div id="monitorEventos" style="max-height:260px;overflow-y:auto;">
                ${_renderEventosMonitorHTML()}
            </div>
        </div>
    `;
}


function _monStatCard(label, val, cor, icon) {
    return `
        <div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:8px;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:2.5px;">${icon} ${label}</div>
            <div style="font-family:var(--orb,var(--mono));font-size:22px;
                 font-weight:700;color:${cor};">${val}</div>
        </div>`;
}


function _renderEventosMonitorHTML() {
    if (!state.monitor.eventos.length) {
        return `<div style="text-align:center;padding:40px;color:var(--text3);
                     font-family:var(--mono);font-size:12px;letter-spacing:2px;">
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


function _renderEventosMonitor() {
    const el = document.getElementById('monitorEventos');
    if (el) el.innerHTML = _renderEventosMonitorHTML();
}


function _atualizarHeaderMonitor() {
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

    if (state.page === 3) {
        setTimeout(() => {
            if (state.page === 3) renderPage();
        }, 300);
    }
}


function limparEventosMonitor() {
    state.monitor.eventos       = [];
    state.monitor.total_alertas = 0;
    _renderEventosMonitor();
    toast('Histórico de alertas limpo.');
}


function pgVisao(wrap) {
    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">MÓDULO DE VISÃO COMPUTACIONAL</div>
                <div class="page-sub">Monitorização óptica via Qwen VL Multimodal</div>
            </div>
            <button class="btn btn-accent" onclick="iniciarAnaliseVisual()">📸 INICIAR VARREDURA</button>
        </div>

        <div style="display:flex;gap:20px;margin-top:20px;height:calc(100vh - 250px);">
            <div class="card" style="flex:2;padding:20px;display:flex;flex-direction:column;
                 align-items:center;justify-content:center;background:#000;
                 border:1px solid var(--border);border-radius:10px;position:relative;">
                <div id="visaoLoader"
                     style="font-family:var(--mono);color:var(--accent);
                            letter-spacing:2px;font-weight:700;">
                    AGUARDANDO COMANDO VISUAL...
                </div>
                <img id="visaoFrame" src=""
                     style="display:none;max-width:100%;max-height:100%;
                            border-radius:6px;box-shadow:0 0 20px rgba(0,200,255,.1);" />
            </div>

            <div class="card" style="flex:1;padding:22px;display:flex;flex-direction:column;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;margin-bottom:14px;margin-top:6px;">
                     DIAGNÓSTICO NEURAL
                </div>
                <div id="visaoResultado"
                     style="flex:1;overflow-y:auto;font-size:14px;color:var(--text);
                            line-height:1.6;border-top:1px solid var(--border);padding-top:15px;">
                    A análise do sistema aparecerá aqui.
                </div>
            </div>
        </div>
    `;
}


function iniciarAnaliseVisual() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }

    document.getElementById('visaoFrame')?.setAttribute('style', 'display:none');
    const loader = document.getElementById('visaoLoader');
    if (loader) {
        loader.style.display = 'block';
        loader.textContent   = 'A INICIAR PROTOCOLO ÓPTICO...';
    }
    const res = document.getElementById('visaoResultado');
    if (res) res.innerHTML = '<span style="color:var(--text3);">A processar dados visuais...</span>';

    window.jarvis.solicitar_analise_visual();
}


function wxIcon(desc) {
    if (!desc) return '🌡️';
    const d = desc.toLowerCase();
    for (const [k, v] of Object.entries(WX_ICONS)) {
        if (d.includes(k.toLowerCase())) return v;
    }
    return WX_ICONS.default;
}


const _qwcScript = document.createElement('script');
_qwcScript.src = 'qrc:///qtwebchannel/qwebchannel.js';
document.head.appendChild(_qwcScript);

_qwcScript.onload = () => {
    try {
        new QWebChannel(qt.webChannelTransport, ch => {
            window.jarvis = ch.objects.jarvis;
            state._bridgeReady = true;
            window.jarvis.dados_para_ui.connect(raw => {
                try { receberDoJarvis(JSON.parse(raw)); }
                catch(e) { console.error('[BRIDGE] Parse error:', e); }
            });
            _loadData();
        });
    } catch(e) {
        addLog('warn', 'Modo demonstração ativo — bridge Qt não detectada');
    }
};


async function _loadData() {
    try {
        const [temas, cfg, iaRaw] = await Promise.all([
            _bridge('obter_temas_sistema'),
            _bridge('obter_configuracoes_atuais'),
            _bridge('obter_ia_status'),
        ]);

        if (temas) state.themes = JSON.parse(temas);

        if (cfg) {
            const c = JSON.parse(cfg);
            Object.assign(state.apis, c);
            if (c.notas)          state.notas             = c.notas;
            if (c.cidade_padrao)  state.weather.city      = c.cidade_padrao;
        }

        if (iaRaw) {
            const ia = JSON.parse(iaRaw);
            state.ia = { modo: ia.modo || 'ollama', modelo: ia.modelo || '', ollama: !!ia.ollama };
            _updateIABadge();
        }

        const temaAtivo = await _bridge('obter_tema_ativo');
        const ta = temaAtivo?.replace(/^"|"$/g, '') || '';
        if (ta && state.themes[ta]) {
            state.theme = ta;
            _applyTheme(ta);
        }
    } catch(e) {
        addLog('warn', 'Dados do sistema indisponíveis — usando padrões');
    }
    renderPage();
}


function _bridge(method) {
    return new Promise(res => {
        if (!window.jarvis || typeof window.jarvis[method] !== 'function') return res(null);
        try { window.jarvis[method](r => res(r)); }
        catch(e) { res(null); }
    });
}


function _bridgeCall(method, arg) {
    return new Promise(res => {
        if (!window.jarvis || typeof window.jarvis[method] !== 'function') return res(null);
        try { window.jarvis[method](arg, r => res(r)); }
        catch(e) { res(null); }
    });
}


function boot() {
    _buildNav();
    _startClock();
    _startMetricSimulation();
    _injetarCSS();
    navegarPara(0);
    document.addEventListener('keydown', _konamiHandler);
    addLog('ok', 'J.A.R.V.I.S MARK XXVIII inicializado');
    addLog('info', 'Aguardando bridge Qt...');
}


function _injetarCSS() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes alertSlideIn {
            from { opacity:0; transform:translateY(16px) scale(.97); }
            to   { opacity:1; transform:translateY(0)    scale(1);   }
        }
    `;
    document.head.appendChild(style);
}


function _buildNav() {
    const nav = document.getElementById('navBtns');
    if (!nav) return;
    PAGES.forEach((p, i) => {
        const btn = document.createElement('button');
        btn.className = 'nav-btn' + (i === 0 ? ' active' : '');
        btn.id = `nb${i}`;
        btn.innerHTML = `<span class="nav-icon">${p.icon}</span>${p.label}`;
        btn.onclick = () => navegarPara(i);
        btn.style.animation = `navIn .3s var(--ease) ${i * 0.04}s both`;
        nav.appendChild(btn);
    });
}


function navegarPara(i) {
    if (i < 0 || i >= PAGES.length) return;
    state.page = i;

    PAGES.forEach((_, j) =>
        document.getElementById(`nb${j}`)?.classList.toggle('active', j === i)
    );

    const titleEl = document.getElementById('pageTitle');
    if (titleEl) {
        titleEl.style.opacity   = '0';
        titleEl.style.transform = 'translateY(-6px)';
        setTimeout(() => {
            titleEl.textContent          = PAGES[i].label + ' ◈ J.A.R.V.I.S';
            titleEl.style.transition     = 'opacity .2s, transform .2s';
            titleEl.style.opacity        = '1';
            titleEl.style.transform      = 'translateY(0)';
        }, 90);
    }

    renderPage();
}


function renderPage() {
    const area = document.getElementById('content');
    if (!area) return;
    area.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'pg-enter';
    area.appendChild(wrap);

    const fns = [pgWeather, pgDash, pgVisao, pgMonitor, pgChat, pgNotas, pgIA, pgConfig, pgTemas];
    (fns[state.page] || pgWeather)(wrap);
}


async function pgWeather(wrap) {
    const searchRow = document.createElement('div');
    searchRow.className = 'weather-search-row';
    searchRow.innerHTML = `
        <input class="input" id="wxCity" placeholder="Buscar cidade..."
               value="${esc(state.weather.city)}" style="max-width:320px;">
        <button class="btn btn-accent" onclick="buscarClima()">BUSCAR</button>
        <button class="btn btn-ghost"  onclick="atualizarClima()">↺ ATUALIZAR</button>
    `;
    wrap.appendChild(searchRow);

    document.getElementById('wxCity')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') buscarClima();
    });

    const wxWrap = document.createElement('div');
    wxWrap.id = 'wxWrap';
    wrap.appendChild(wxWrap);

    if (state.weather.loading || state.weather.temp === null) {
        _fetchWeather(state.weather.city);
    } else {
        _renderWeather(wxWrap);
    }
}


async function buscarClima() {
    const input = document.getElementById('wxCity');
    const city  = (input?.value || '').trim();
    if (!city) return;

    state.weather.city    = city;
    state.weather.loading = true;
    state.weather.error   = null;

    if (window.jarvis) window.jarvis.salvar_configuracao('cidade_padrao', city);
    _fetchWeather(city);
}


async function atualizarClima() {
    state.weather.loading = true;
    state.weather.error   = null;
    _fetchWeather(state.weather.city);
}


async function _fetchWeather(city) {
    const wxWrap = document.getElementById('wxWrap');
    if (!wxWrap) return;

    wxWrap.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:center;height:280px;gap:12px;
                    color:var(--text3);font-family:var(--mono);font-size:13px;letter-spacing:2px;">
            <span style="animation:rotateSlow .8s linear infinite;display:inline-block;">◈</span>
            SOLICITANDO DADOS AO NÚCLEO PYTHON...
        </div>`;

    if (window.jarvis) window.jarvis.solicitar_clima(city);
}


function _parseWeatherData(data, city) {
    const wxWrap = document.getElementById('wxWrap');
    if (!wxWrap) return;

    try {
        const cur  = (data.current_condition && data.current_condition[0]) || {};
        const area = (data.nearest_area && data.nearest_area[0]) || {
            areaName: [{value: city}], country: [{value: ''}],
        };

        state.weather = {
            ...state.weather,
            city:     area.areaName[0].value || city,
            country:  area.country[0].value || '',
            temp:     parseInt(cur.temp_C)    || 0,
            feels:    parseInt(cur.FeelsLikeC)|| 0,
            desc:     cur.weatherDesc ? cur.weatherDesc[0].value : 'N/A',
            icon:     wxIcon(cur.weatherDesc ? cur.weatherDesc[0].value : ''),
            humidity: parseInt(cur.humidity)       || 0,
            wind:     parseInt(cur.windspeedKmph)  || 0,
            uv:       parseInt(cur.uvIndex)        || 0,
            pressure: parseInt(cur.pressure)       || 0,
            vis:      parseInt(cur.visibility)     || 0,
            loading:  false,
            error:    null,
            forecast: data.weather ? data.weather.slice(0, 6).map(d => ({
                date: d.date,
                hi:   parseInt(d.maxtempC),
                lo:   parseInt(d.mintempC),
                desc: d.hourly && d.hourly[4] ? d.hourly[4].weatherDesc[0].value : '',
            })) : [],
        };

        _renderWeather(wxWrap);
    } catch(e) {
        state.weather.loading = false;
        state.weather.error   = 'Falha na decodificação';
        _renderWeatherError();
    }
}


function _renderWeatherError() {
    const wxWrap = document.getElementById('wxWrap');
    if (!wxWrap) return;
    wxWrap.innerHTML = `
        <div class="weather-main" style="align-items:center;justify-content:center;
             min-height:200px;text-align:center;gap:18px;">
            <div style="font-size:48px;">🌐</div>
            <div style="font-family:var(--mono);font-size:14px;color:var(--red);
                 letter-spacing:1.5px;font-weight:700;">${esc(state.weather.error)}</div>
            <div style="font-size:14px;color:var(--text3);">
                Verifique a conexão ou o nome da cidade.
            </div>
            <button class="btn btn-accent" onclick="atualizarClima()">TENTAR NOVAMENTE</button>
        </div>`;
}


function _renderWeather(wxWrap) {
    const wx = state.weather;
    if (!wxWrap) return;

    const DOWS = ['DOM','SEG','TER','QUA','QUI','SEX','SÁB'];
    const forecastHTML = wx.forecast.map((d, i) => {
        const dt  = new Date(d.date + 'T12:00:00');
        const dow = i === 0 ? 'HOJE' : DOWS[dt.getDay()];
        return `
            <div class="forecast-day" style="animation:pageEnter .3s var(--ease) ${i * 0.05}s both;">
                <div class="forecast-dow">${dow}</div>
                <div class="forecast-icon">${wxIcon(d.desc)}</div>
                <div class="forecast-hi">${d.hi}°</div>
                <div class="forecast-lo">${d.lo}°</div>
            </div>`;
    }).join('');

    const tCol = wx.temp > 35 ? 'var(--red)'    :
                 wx.temp > 28 ? 'var(--orange)'  :
                 wx.temp > 18 ? 'var(--accent)'  : 'var(--purple)';

    wxWrap.innerHTML = `
        <div class="weather-hero">
            <div class="weather-main" style="animation:pageEnter .35s var(--ease) .05s both;">
                <div class="weather-icon-big">${wx.icon}</div>
                <div class="weather-city">${esc(wx.city)}${wx.country ? ', ' + esc(wx.country) : ''}</div>
                <div class="weather-temp" style="color:${tCol};">${wx.temp}<sup>°C</sup></div>
                <div class="weather-desc">${esc(wx.desc)}</div>
                <div class="weather-feels">Sensação térmica: ${wx.feels}°C</div>
            </div>

            <div class="weather-stats-grid" style="animation:pageEnter .35s var(--ease) .1s both;">
                ${_wxStat('💧','UMIDADE',     wx.humidity + '%',  '',             'var(--accent)')}
                ${_wxStat('💨','VENTO',       wx.wind + ' km/h',  '',             'var(--accent2)')}
                ${_wxStat('🌡️','PRESSÃO',    wx.pressure + ' hPa','',            'var(--yellow)')}
                ${_wxStat('☀️','ÍNDICE UV',  String(wx.uv),       _uvLabel(wx.uv),_uvColor(wx.uv))}
                ${_wxStat('👁️','VISIBILIDADE',wx.vis + ' km',     '',             'var(--purple)')}
                ${_wxStat('🌡️','SENSAÇÃO',   wx.feels + '°C',     '',             tCol)}
            </div>
        </div>

        <div class="weather-forecast" style="animation:pageEnter .35s var(--ease) .15s both;">
            <div class="forecast-label">PREVISÃO — PRÓXIMOS 6 DIAS</div>
            <div class="forecast-row">
                ${forecastHTML || '<div style="color:var(--text3);font-family:var(--mono);font-size:13px;">Sem dados de previsão.</div>'}
            </div>
        </div>

        <div style="display:flex;gap:12px;animation:pageEnter .35s var(--ease) .2s both;">
            ${_wxAlerts(wx)}
        </div>
    `;
}


function _wxStat(icon, label, val, sub, col) {
    return `
        <div class="weather-stat">
            <div class="stat-label">${icon} ${label}</div>
            <div class="stat-val" style="color:${col};">${val}</div>
            ${sub ? `<div class="stat-sub">${sub}</div>` : ''}
        </div>`;
}


function _uvLabel(uv) {
    if (uv <= 2) return 'BAIXO';
    if (uv <= 5) return 'MODERADO';
    if (uv <= 7) return 'ALTO';
    return 'EXTREMO';
}


function _uvColor(uv) {
    if (uv <= 2) return 'var(--accent2)';
    if (uv <= 5) return 'var(--yellow)';
    return 'var(--red)';
}


function _wxAlerts(wx) {
    const tips = [];
    if (wx.temp     > 35)  tips.push({ icon:'🔥', msg:'Calor extremo — hidrate-se constantemente.',    col:'var(--red)'    });
    if (wx.uv       > 7)   tips.push({ icon:'☀️', msg:'UV alto — use protetor solar FPS 50+.',         col:'var(--orange)' });
    if (wx.wind     > 60)  tips.push({ icon:'💨', msg:'Vento forte — cuidado ao dirigir.',             col:'var(--yellow)' });
    if (wx.humidity > 90)  tips.push({ icon:'💧', msg:'Alta umidade — sensação de calor amplificada.', col:'var(--accent)' });

    if (!tips.length) return `
        <div class="weather-stat" style="flex:1;">
            <div class="stat-label">✅ CONDIÇÕES</div>
            <div style="font-size:15px;color:var(--accent2);font-weight:700;margin-top:8px;">
                Clima estável — sem alertas ativos.
            </div>
        </div>`;

    return tips.map(t => `
        <div class="weather-stat" style="flex:1;border-color:${t.col}33;">
            <div class="stat-label">${t.icon} ALERTA</div>
            <div style="font-size:13px;color:${t.col};font-weight:700;margin-top:6px;">${t.msg}</div>
        </div>`).join('');
}


function pgDash(wrap) {
    const m = state.metricas;

    wrap.innerHTML = `
        <div class="dash-grid">
            ${_metricCard('CPU',        'v-cpu','p-cpu', Math.round(m.cpu)+'%', m.cpu, 'var(--accent)')}
            ${_metricCard('MEMÓRIA RAM','v-ram','p-ram', Math.round(m.ram)+'%', m.ram, 'var(--accent)')}
            ${_metricCard('GPU',        'v-gpu','p-gpu', Math.round(m.gpu)+'%', m.gpu, 'var(--orange)')}
        </div>

        <div class="dash-bottom">
            <div class="card" style="padding:22px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),var(--accent2));"></div>
                <div style="margin-top:6px;">
                    <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                         color:var(--text3);letter-spacing:3px;margin-bottom:18px;">
                         ESPECIFICAÇÕES DO SISTEMA
                    </div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:9px;">
                        ${_spec('DISCO USO',  Math.round(m.disco)+'%')}
                        ${_spec('FREQ CPU',   m.freq+' MHz')}
                        ${_spec('RAM EM USO', m.ram_usada+' / '+m.ram_total+' GB')}
                        ${_spec('GPU TEMP',   m.gpu_temp+'°C')}
                        ${_spec('LATÊNCIA',   m.ping+' ms')}
                        ${_spec('UPTIME',     _uptime())}
                        ${_spec('DOWNLOAD',   m.net_in+' MB/s')}
                        ${_spec('UPLOAD',     m.net_out+' MB/s')}
                    </div>
                </div>
            </div>

            <div class="card" style="padding:22px;">
                <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                     color:var(--text3);letter-spacing:3px;margin-bottom:14px;margin-top:6px;">
                     LOG DE ATIVIDADE
                </div>
                <div class="log-stream" id="logStream"></div>
            </div>
        </div>

        <div class="quick-grid">
            ${_quickBtn('🔒','BLOQUEAR TELA', 'bloquear',       'var(--purple)', 'rgba(136,85,255,.05)')}
            ${_quickBtn('📸','CAPTURAR TELA', 'captura',        'var(--accent)', 'rgba(0,200,255,.05)')}
            ${_quickBtn('🗑️','LIMPAR LIXEIRA','limpar lixeira', 'var(--red)',    'rgba(255,34,85,.05)')}
            ${_quickBtn('🖥️','MINIMIZAR TUDO','minimizar',      'var(--accent2)','rgba(0,255,157,.05)')}
            ${_quickBtn('❌','FECHAR JANELA', 'fechar',         'var(--orange)', 'rgba(255,122,0,.05)')}
            ${_quickBtn('💼','MODO TRABALHO', 'trabalho',       'var(--yellow)', 'rgba(255,199,0,.05)')}
        </div>
    `;

    _renderLog();
    _updateMetrics();
}


function _metricCard(lbl, idV, idP, val, pct, cor) {
    const col = pct > 85 ? 'var(--red)' : pct > 65 ? 'var(--orange)' : cor;
    return `
        <div class="metric-card">
            <div class="card-accent" style="background:linear-gradient(90deg,${col},transparent);"></div>
            <div class="metric-label" style="margin-top:6px;">${lbl}</div>
            <div class="metric-val" id="${idV}" style="color:${col};">${val}</div>
            <div class="metric-bar">
                <div class="metric-fill" id="${idP}"
                     style="width:${pct}%;background:linear-gradient(90deg,${col},${col}88);"></div>
            </div>
        </div>`;
}


function _spec(k, v) {
    return `
        <div class="spec-block">
            <div class="spec-label">${k}</div>
            <div class="spec-val">${v}</div>
        </div>`;
}


function _quickBtn(icon, label, cmd, col, bg) {
    return `
        <div class="quick-btn" style="--hover-col:${bg};color:${col};border-color:var(--border);"
             onclick="enviarComando('${cmd}')"
             onmouseover="this.style.borderColor='${col}40'"
             onmouseout="this.style.borderColor='var(--border)'">
            <span class="quick-icon">${icon}</span>
            <span class="quick-label" style="color:${col};">${label}</span>
        </div>`;
}


function _uptime() {
    const s = Math.floor((Date.now() - state.metricas.uptime_start) / 1000);
    return `${_zp(Math.floor(s/3600))}:${_zp(Math.floor((s%3600)/60))}:${_zp(s%60)}`;
}


function _updateMetrics() {
    const m    = state.metricas;
    const _set  = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    const _setW = (id, p) => { const e = document.getElementById(id); if (e) e.style.width  = p+'%'; };
    const _setC = (id, c) => { const e = document.getElementById(id); if (e) e.style.color  = c; };

    const cpuC = m.cpu > 85 ? 'var(--red)' : m.cpu > 65 ? 'var(--orange)' : 'var(--accent)';
    _set('v-cpu', Math.round(m.cpu)+'%'); _setW('p-cpu', m.cpu); _setC('v-cpu', cpuC);

    const ramC = m.ram > 85 ? 'var(--red)' : m.ram > 70 ? 'var(--orange)' : 'var(--accent)';
    _set('v-ram', Math.round(m.ram)+'%'); _setW('p-ram', m.ram); _setC('v-ram', ramC);

    const gpuC = m.gpu > 85 ? 'var(--red)' : m.gpu > 65 ? 'var(--orange)' : 'var(--orange)';
    _set('v-gpu', Math.round(m.gpu)+'%'); _setW('p-gpu', m.gpu); _setC('v-gpu', gpuC);
}


function pgChat(wrap) {
    wrap.innerHTML = `
        <div class="chat-wrap">
            <div class="chat-history" id="chatHistory"></div>
            <div class="chat-input-row">
                <input class="input" id="chatIn"
                       placeholder="Fale com J.A.R.V.I.S..." style="flex:1;">
                <button class="btn btn-accent" onclick="enviarChat()">ENVIAR</button>
            </div>
        </div>`;

    _renderChat();
    const ci = document.getElementById('chatIn');
    ci?.addEventListener('keydown', e => { if (e.key === 'Enter') enviarChat(); });
    ci?.focus();
}


function enviarChat() {
    const ci  = document.getElementById('chatIn');
    const msg = ci?.value.trim();
    if (!msg) return;
    ci.value = '';
    state.chatHist.push({ role: 'user', text: msg });
    _renderChat();
    _showTyping();

    if (window.jarvis) {
        window.jarvis.executar_comando(msg);
    } else {
        const demo = [
            'Modo demonstração ativo. Bridge Qt não conectada.',
            'Sistemas operacionais. Aguardando conexão com o núcleo.',
            'Entendido, Chefe. Processando na fila de comandos.',
        ];
        setTimeout(() => {
            document.getElementById('typingIndicator')?.remove();
            state.chatHist.push({ role: 'jarvis', text: demo[state.chatHist.length % demo.length] });
            _renderChat();
        }, 1100 + Math.random() * 600);
    }
}


function _showTyping() {
    const h = document.getElementById('chatHistory');
    if (!h) return;
    const d = document.createElement('div');
    d.id        = 'typingIndicator';
    d.className = 'msg jarvis';
    d.innerHTML = `
        <div class="msg-role">J.A.R.V.I.S</div>
        <div class="msg-bubble">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>`;
    h.appendChild(d);
    h.scrollTop = h.scrollHeight;
}


function _renderChat() {
    const h = document.getElementById('chatHistory');
    if (!h) return;
    if (!state.chatHist.length) {
        h.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;
                 justify-content:center;height:100%;gap:20px;
                 color:var(--text3);font-family:var(--mono);
                 font-size:13px;letter-spacing:2px;">
                <div style="font-size:52px;filter:drop-shadow(0 0 18px var(--accent));
                     animation:floatIcon 4s ease-in-out infinite;">◈</div>
                <div style="font-weight:700;">CHAT NEURAL PRONTO</div>
                <div style="font-size:11px;letter-spacing:3px;">DIGA ALGO PARA J.A.R.V.I.S</div>
            </div>`;
        return;
    }
    h.innerHTML = state.chatHist.map(m => `
        <div class="msg ${m.role}">
            <div class="msg-role">${m.role === 'user' ? 'VOCÊ' : 'J.A.R.V.I.S'}</div>
            <div class="msg-bubble">${esc(m.text)}</div>
        </div>`).join('');
    h.scrollTop = h.scrollHeight;
}


function pgNotas(wrap) {
    wrap.innerHTML = `
        <div class="notes-wrap">
            <div class="notes-toolbar">
                <button class="btn btn-accent" onclick="salvarNotas()">💾 SALVAR</button>
                <button class="btn btn-ghost"  onclick="limparNotas()">🗑️ LIMPAR</button>
                <span style="flex:1;"></span>
                <span style="font-family:var(--mono);font-size:11px;font-weight:700;
                     color:var(--text3);letter-spacing:2px;" id="notasStatus">—</span>
            </div>
            <textarea class="notes-textarea" id="notasTxt"
                      spellcheck="false"
                      placeholder="Escreva notas táticas aqui...">${esc(state.notas)}</textarea>
        </div>`;

    const ta = document.getElementById('notasTxt');
    if (ta) {
        document.getElementById('notasStatus').textContent = `${ta.value.length} chars`;
        ta.addEventListener('input', e => {
            state.notas = e.target.value;
            document.getElementById('notasStatus').textContent = `${e.target.value.length} chars`;
        });
    }
}


function salvarNotas() {
    if (window.jarvis) window.jarvis.salvar_configuracao('notas', state.notas);
    toast('✓ Notas salvas.');
}


function limparNotas() {
    state.notas = '';
    const t = document.getElementById('notasTxt');
    if (t) { t.value = ''; document.getElementById('notasStatus').textContent = '0 chars'; }
    toast('Notas limpas.', 'warn');
}


function pgIA(wrap) {
    const { ia } = state;
    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">MODELO DE IA</div>
                <div class="page-sub">Selecione e gerencie o motor de inteligência</div>
            </div>
        </div>

        <div class="ia-grid">
            <div class="ia-option ${ia.modo === 'ollama' ? 'ia-active' : ''}"
                 onclick="trocarIA('ollama')">
                <div class="ia-option-header">
                    <div class="ia-name" style="color:var(--accent);">OLLAMA</div>
                    <div class="ia-badge-dot ${ia.ollama ? 'online' : ''} ${ia.modo === 'ollama' ? 'active-dot' : ''}"></div>
                </div>
                <div class="ia-desc">LLM local via Ollama. Privacidade total, sem API key. Requer ollama serve.</div>
                <div class="ia-model-tag">${ia.modo === 'ollama' && ia.modelo ? ia.modelo : 'nenhum detectado'}</div>
            </div>

            <div class="ia-option ${ia.modo === 'gemini' ? 'ia-active' : ''}"
                 onclick="trocarIA('gemini')">
                <div class="ia-option-header">
                    <div class="ia-name" style="color:var(--yellow);">GEMINI</div>
                    <div class="ia-badge-dot ${ia.modo === 'gemini' ? 'active-dot' : ''}"></div>
                </div>
                <div class="ia-desc">Google Gemini via API. Maior capacidade, requer chave configurada.</div>
                <div class="ia-model-tag">${ia.modo === 'gemini' ? 'gemini-pro' : '—'}</div>
            </div>
        </div>

        <div class="card" style="padding:22px;margin-top:0;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:3px;margin-bottom:18px;margin-top:6px;">
                 STATUS DO MOTOR
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                ${_iaStatus('MODO ATIVO', ia.modo.toUpperCase(), ia.modo === 'ollama' ? 'var(--accent)' : 'var(--yellow)')}
                ${_iaStatus('OLLAMA', ia.ollama ? 'ONLINE' : 'OFFLINE', ia.ollama ? 'var(--accent2)' : 'var(--red)')}
                ${_iaStatus('MODELO', ia.modelo || 'N/A', 'var(--text)')}
            </div>
        </div>

        <div style="display:flex;gap:12px;">
            <button class="btn btn-accent" onclick="atualizarStatusIA()">↺ ATUALIZAR STATUS</button>
            <button class="btn btn-ghost"  onclick="testarIA()">▶ TESTAR IA</button>
        </div>
    `;
}


function _iaStatus(lbl, val, col) {
    return `
        <div style="padding:14px;background:var(--surface);border:1px solid var(--border);border-radius:10px;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--text3);letter-spacing:2.5px;margin-bottom:9px;">${lbl}</div>
            <div style="font-family:var(--orb);font-size:16px;font-weight:700;color:${col};">${val}</div>
        </div>`;
}


async function trocarIA(modo) {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    const res = await _bridgeCall('alternar_ia', modo);
    if (res) {
        try { const r = JSON.parse(res); toast(r.msg || 'Modo alterado.'); } catch(e) {}
    }
    state.ia.modo = modo;
    if (state.page === 6) renderPage();
}


async function atualizarStatusIA() {
    const raw = await _bridge('obter_ia_status');
    if (raw) {
        try {
            const ia = JSON.parse(raw);
            state.ia = { modo: ia.modo || 'ollama', modelo: ia.modelo || '', ollama: !!ia.ollama };
            _updateIABadge();
            if (state.page === 6) renderPage();
            toast('✓ Status IA atualizado.');
        } catch(e) {}
    } else {
        toast('Status IA indisponível.', 'warn');
    }
}


function testarIA() {
    enviarComando('olá jarvis');
    navegarPara(4);
}


function toggleEditConfig() {
    state.configEdit = !state.configEdit;
    if (state.page === 7) renderPage();
    toast(state.configEdit ? '🔓 Edição liberada.' : '🔒 Configurações bloqueadas.');
}


function pgConfig(wrap) {
    const apiFields = [
        { key:'gemini',      label:'GEMINI API KEY',    tip:'Google AI Studio'  },
        { key:'qwen',        label:'QWEN API KEY',      tip:'Alibaba Cloud'     },
        { key:'smartthings', label:'SMARTTHINGS TOKEN', tip:'SmartThings API'   },
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
                        <input class="api-input" id="api_${f.key}" type="password"
                               placeholder="${f.tip}"
                               value="${esc(state.apis[f.key] || '')}"
                               ${state.configEdit ? '' : 'readonly'}
                               style="transition:all .3s;${state.configEdit ? '' : 'opacity:.5;cursor:not-allowed;border-color:transparent;'}"
                               oninput="_onApiInput('${f.key}', this.value)">
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


function _onApiInput(key, val) {
    state.apis[key] = val;
    const dot = document.getElementById(`dot_${key}`);
    if (dot) dot.className = 'api-status ' + (val ? 'ok' : '');
}


function salvarConfig() {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    const keys = ['gemini','qwen','smartthings','spotify_id','spotify_sec','nome_mestre','cidade_padrao'];
    let saved = 0;
    keys.forEach(k => {
        if (state.apis[k] !== undefined) { window.jarvis.salvar_configuracao(k, state.apis[k]); saved++; }
    });
    toast(`✓ ${saved} configurações salvas.`);
    if (state.configEdit) toggleEditConfig();
}


function pgTemas(wrap) {
    const ids = Object.keys(state.themes);

    wrap.innerHTML = `
        <div class="page-header">
            <div>
                <div class="page-title">PROTOCOLO VISUAL</div>
                <div class="page-sub">Selecione o esquema de cores da interface</div>
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
                    const active = state.theme === id;
                    return `
                        <div class="theme-card ${active ? 'active-theme' : ''}"
                             style="border-color:${active ? a1 : 'var(--border)'};"
                             onclick="aplicarTema('${id}')">
                            <div class="theme-preview">
                                <div class="theme-swatch" style="background:${a1};"></div>
                                <div class="theme-swatch" style="background:${a2};"></div>
                                <div class="theme-swatch" style="background:${a3};"></div>
                            </div>
                            <div class="theme-name" style="color:${a1};">${id}</div>
                            <button class="theme-apply-btn"
                                    style="border-color:${a1};color:${a1};
                                           background:${active ? a1+'1a' : 'transparent'};">
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
        </div>
    `;
}


function aplicarTema(id) {
    if (!state.themes[id]) return;
    state.theme = id;
    _applyTheme(id);
    if (window.jarvis) window.jarvis.salvar_configuracao('tema_ativo', id);
    if (state.page === 8) renderPage();
    toast(`Tema ${id} ativado.`);
}


function _applyTheme(id) {
    const t = state.themes[id];
    if (!t) return;
    const r = document.documentElement;
    r.style.setProperty('--accent',  t.accent    || '#00c8ff');
    r.style.setProperty('--accent2', t.secondary || '#00ff9d');
    r.style.setProperty('--bg',      t.bg);
    r.style.setProperty('--card',    t.card);
    r.style.setProperty('--border',  t.border);
    r.style.setProperty('--border2', t.border);
    r.style.setProperty('--text',    t.text_pri);
    r.style.setProperty('--text2',   t.text_sec);
    r.style.setProperty('--red',     t.danger);
    r.style.setProperty('--surface', t.surface || t.card);
}


function enviarComando(cmd) {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    window.jarvis.executar_comando(cmd);
    addLog('info', '▶ ' + cmd);
    toast('▶ ' + cmd.toUpperCase().slice(0, 60));
}


function addLog(tipo, msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    state.logs.unshift({ tipo, msg: String(msg), ts });
    if (state.logs.length > 100) state.logs.pop();
    _renderLog();
}


function _renderLog() {
    const el = document.getElementById('logStream');
    if (!el) return;
    el.innerHTML = state.logs.slice(0, 28).map(e => `
        <div class="log-line">
            <span class="log-ts">${e.ts}</span>
            <span class="log-${e.tipo}">${esc(e.msg)}</span>
        </div>`).join('');
}


function _updateIABadge() {
    const el = document.getElementById('iaBadge');
    if (!el) return;
    const { ia } = state;
    const col   = ia.modo === 'ollama' ? 'var(--accent)' : 'var(--yellow)';
    const dot   = ia.ollama
        ? `<span style="width:6px;height:6px;border-radius:50%;background:var(--accent2);
                 display:inline-block;box-shadow:0 0 5px var(--accent2);"></span>`
        : '';
    const model = ia.modelo ? ia.modelo.slice(0, 14) : '—';
    el.innerHTML = `${dot}<span style="color:${col};">${ia.modo.toUpperCase()}</span>
                    <span style="color:var(--text3);">◈</span>
                    <span style="color:var(--text2);font-size:10px;">${model}</span>`;
}


function toast(msg, type = '') {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = String(msg);
    el.className   = 'show' + (type ? ' ' + type : '');
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = ''; }, 3400);
}


function _startClock() {
    const el   = document.getElementById('clock');
    const tick = () => { if (el) el.textContent = new Date().toTimeString().slice(0, 8); };
    tick();
    setInterval(tick, 1000);
}


function _startMetricSimulation() {
    const α = 0.18;

    const tick = () => {
        const m = state.metricas;

        m._cpu_raw = clamp(m._cpu_raw + (Math.random() - .46) * 8,   2,  96);
        m._ram_raw = clamp(m._ram_raw + (Math.random() - .49) * 2.5, 18, 92);
        m._gpu_raw = clamp(m._gpu_raw + (Math.random() - .46) * 10,  0,  90);

        m.cpu = +(m.cpu * (1 - α) + m._cpu_raw * α).toFixed(1);
        m.ram = +(m.ram * (1 - α) + m._ram_raw * α).toFixed(1);
        m.gpu = +(m.gpu * (1 - α) + m._gpu_raw * α).toFixed(1);

        m.net_in   = +(Math.random() * 2.4).toFixed(2);
        m.net_out  = +(Math.random() * 0.7).toFixed(2);
        m.ping     = Math.floor(16 + Math.random() * 55);
        m.freq     = Math.floor(2000 + Math.random() * 1600);
        m.gpu_temp = Math.floor(36 + m.gpu * 0.42);
        m.ram_usada = +((m.ram / 100) * m.ram_total).toFixed(1);

        if (state.page === 1) _updateMetrics();
    };

    tick();
    setInterval(tick, 1400);
}


function clamp(v, mn, mx) { return Math.min(mx, Math.max(mn, v)); }
function _zp(n)            { return String(n).padStart(2, '0'); }


function esc(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}


function abrirModal(id)  { document.getElementById(id)?.classList.add('open'); }
function fecharModal(id) { document.getElementById(id)?.classList.remove('open'); }
function confirmarDesligamento() { abrirModal('modalShutdown'); }


function fecharPainel() {
    fecharModal('modalClose');
    document.body.style.transition = 'opacity .4s ease';
    document.body.style.opacity    = '0';
    setTimeout(() => { document.body.style.display = 'none'; }, 420);
}


function desligarJarvis() {
    fecharModal('modalShutdown');
    addLog('err', 'SHUTDOWN INICIADO');
    if (window.jarvis?.desligar_sistema) window.jarvis.desligar_sistema();

    const scr = document.createElement('div');
    scr.className = 'shutdown-screen';
    scr.innerHTML = `
        <div class="shutdown-glyph">⏻</div>
        <div class="shutdown-text">J.A.R.V.I.S OFFLINE</div>
        <div class="shutdown-progress"><div class="shutdown-bar"></div></div>`;
    document.body.appendChild(scr);
    scr.style.opacity    = '0';
    scr.style.transition = 'opacity .4s';
    requestAnimationFrame(() => { scr.style.opacity = '1'; });
    setTimeout(() => { scr.style.opacity = '0'; }, 2500);
    setTimeout(() => { document.body.innerHTML = ''; }, 3100);
}


const _K = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown',
            'ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];


function _konamiHandler(e) {
    state.konami.push(e.key);
    state.konami = state.konami.slice(-10);
    if (state.konami.join(',') !== _K.join(',')) return;
    state.konami = [];

    let hue = 0;
    const lp = setInterval(() => {
        document.documentElement.style.setProperty('--accent',  `hsl(${hue},100%,60%)`);
        document.documentElement.style.setProperty('--accent2', `hsl(${(hue+120)%360},100%,60%)`);
        hue = (hue + 4) % 360;
    }, 50);
    toast('✦ MODO ARCO-ÍRIS ATIVADO ↑↑↓↓←→←→BA');
    setTimeout(() => {
        clearInterval(lp);
        if (state.theme) _applyTheme(state.theme);
    }, 8000);
}


window.addEventListener('DOMContentLoaded', boot);