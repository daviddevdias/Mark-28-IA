'use strict';


function receberDoJarvis(data) {
    if (data.cpu !== undefined) {
        state.metricas._cpu_raw = data.cpu;
        state.metricas._ram_raw = data.ram;
        if (state.page === PG.DASH) updateMetrics();
    }

    if (data.voz_speaking !== undefined) {
        state.voz.speaking = !!data.voz_speaking;
        state.voz.vol = typeof data.voz_vol === 'number' ? data.voz_vol : state.voz.vol;
        atualizarMedidorVoz();
    }

    if (data.resposta) {
        const s = String(data.resposta);
        addLog('ok', s.slice(0, 120));
        toast(s.slice(0, 90));
        const hist = state.chatHist;
        if (hist.length && hist[hist.length - 1]?.role === 'user') {
            document.getElementById('typingIndicator')?.remove();
            hist.push({ role: 'jarvis', text: s });
            if (state.page === PG.CHAT) renderChat();
        }
    }

    if (data.erro) {
        const msg = String(data.erro).slice(0, 200);
        addLog('err', msg);
        toast(msg.slice(0, 90), 'err');
    }

    if (data.ia_status) {
        state.ia = {
            modo:   data.ia_status.modo   || state.ia.modo,
            modelo: data.ia_status.modelo || '',
            ollama: !!data.ia_status.ollama,
        };
        updateIABadge();
        if (state.page === PG.IA) renderPage();
    }

    if (data.visao_status) {
        const el = document.getElementById('visaoLoader');
        if (el) { el.style.display = 'block'; el.textContent = data.visao_status; }
        toast(data.visao_status);
    }

    if (data.visao_img !== undefined || data.visao_resultado !== undefined) {
        if (typeof finalizarAnaliseVisual === 'function') {
            finalizarAnaliseVisual(data.visao_img || '', data.visao_resultado || '');
        }
        if (data.visao_resultado) addLog('ok', 'Análise visual concluída.');
    }

    if (data.visao_erro) {
        toast(data.visao_erro, 'err');
        addLog('err', 'Visão: ' + String(data.visao_erro).slice(0, 120));
        if (typeof finalizarAnaliseVisual === 'function') {
            finalizarAnaliseVisual('', JSON.stringify({
                ok: false,
                tipo: 'erro',
                resumo: data.visao_erro,
                problema: data.visao_erro,
                sugestao_rapida: '',
            }));
        }
    }

    if (data.monitor_status) {
        state.monitor.ativo = data.monitor_status === 'ativo';
        if (data.monitor_intervalo) state.monitor.intervalo = data.monitor_intervalo;
        if (state.page === PG.MONITOR) atualizarHeaderMonitor();
        addLog(
            state.monitor.ativo ? 'ok' : 'warn',
            state.monitor.ativo
                ? `Monitor ativo (${state.monitor.intervalo}s)`
                : 'Monitor desativado.'
        );
    }
    if (data.monitor_evento)  processarEventoMonitor(data.monitor_evento);
    if (data.monitor_dica) {
        state.monitor.ultima_dica = data.monitor_dica;
        exibirDicaMonitor(data.monitor_dica, data.monitor_tipo || state.monitor.ultimo_tipo);
        addLog('warn', 'Dica Jarvis: ' + data.monitor_dica.slice(0, 80));
    }

    if (data.clima_dados) {
        state.weather.loading = false;
        if (data.clima_dados.error) {
            state.weather.error = data.clima_dados.error;
            renderWeatherError();
        } else {
            parseWeatherData(data.clima_dados, data.cidade_buscada);
        }
    }

    if (data.alarmes_lista) {
        state.alarmes.lista = data.alarmes_lista;
        if (typeof Bus !== 'undefined') Bus.emit('alarmes:updated', data.alarmes_lista);
        if (state.page === PG.ALARMES) renderPage();
    }
    if (data.alarme_disparado) {
        state.alarmes.alarmeAtivo = true;
        if (typeof Bus !== 'undefined') Bus.emit('alarme:disparado', data.alarme_disparado);
        mostrarNotificacaoAlarme(data.alarme_disparado);
    }
    if (data.alarme_parado) {
        state.alarmes.alarmeAtivo = false;
        if (typeof Bus !== 'undefined') Bus.emit('alarme:parado', {});
    }
}
window.receberDoJarvis = receberDoJarvis;


function bridge(method) {
    return new Promise(res => {
        if (!window.jarvis || typeof window.jarvis[method] !== 'function') return res(null);
        try { window.jarvis[method](r => res(r)); }
        catch (e) { res(null); }
    });
}


function bridgeCall(method, arg) {
    return new Promise(res => {
        if (!window.jarvis || typeof window.jarvis[method] !== 'function') return res(null);
        try { window.jarvis[method](arg, r => res(r)); }
        catch (e) { res(null); }
    });
}
window.bridge     = bridge;
window.bridgeCall = bridgeCall;

const scriptWebChannel = document.createElement('script');
scriptWebChannel.src   = 'qrc:///qtwebchannel/qwebchannel.js';
document.head.appendChild(scriptWebChannel);

scriptWebChannel.onload = () => {
    try {
        new QWebChannel(qt.webChannelTransport, ch => {
            window.jarvis = ch.objects.jarvis;
            state.bridgeReady = true;
            window.jarvis.dados_para_ui.connect(raw => {
                try { receberDoJarvis(JSON.parse(raw)); }
                catch (e) { console.error('[BRIDGE] Parse error:', e, raw); }
            });
            loadData();
        });
    } catch (e) {
        addLog('warn', 'Modo demonstração ativo — bridge Qt não detectada');
    }
};


async function loadData() {
    try {
        const [temas, cfg, iaRaw, vozRaw, cmdsRaw] = await Promise.all([
            bridge('obter_temas_sistema'),
            bridge('obter_configuracoes_atuais'),
            bridge('obter_ia_status'),
            bridge('obter_config_voz'),
            bridge('obter_biblioteca_comandos'),
        ]);

        if (temas) {
            try { state.themes = JSON.parse(temas); } catch (e) {}
        }

        if (cfg) {
            try {
                const c = JSON.parse(cfg);
                Object.assign(state.apis, c);
                if (c.notas)         state.notas         = c.notas;
                if (c.cidade_padrao) {
                    state.apis.cidade_padrao = c.cidade_padrao;
                    state.weather.city  = c.cidade_padrao;
                    if (state.page === PG.WEATHER && typeof fetchWeather === 'function') {
                        fetchWeather(c.cidade_padrao);
                    }
                }
            } catch (e) {}
        }

        if (iaRaw) {
            try {
                const ia = JSON.parse(iaRaw);
                state.ia = { modo: ia.modo || 'ollama', modelo: ia.modelo || '', ollama: !!ia.ollama };
                if (typeof updateIABadge === 'function') updateIABadge();
            } catch (e) {}
        }

        if (vozRaw) {
            try {
                const v = JSON.parse(vozRaw);
                state.voz.deviceIndex = Number(v.device_index) || 0;
                state.voz.microfones  = Array.isArray(v.microfones) ? v.microfones : [];
            } catch (e) {}
        }

        if (cmdsRaw) {
            try { state.cmdLibrary = JSON.parse(cmdsRaw); } catch (e) { state.cmdLibrary = []; }
        }

        const temaAtivo = await bridge('obter_tema_ativo');
        let ta = '';
        if (temaAtivo) {
            try {
                const parsed = JSON.parse(temaAtivo);
                ta = typeof parsed === 'string' ? parsed : '';
            } catch (e) {
                ta = String(temaAtivo).replace(/^["']|["']$/g, '');
            }
        }
        if (ta && state.themes[ta]) {
            state.theme = ta;
            if (typeof applyTheme === 'function') applyTheme(ta);
        }

        if (typeof carregarAlarmesBridge === 'function') await carregarAlarmesBridge();

    } catch (e) {
        if (typeof addLog === 'function') addLog('warn', 'Dados do sistema indisponíveis — usando padrões');
    }

    if (typeof renderPage === 'function') renderPage();
    setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
}
window.loadData = loadData;