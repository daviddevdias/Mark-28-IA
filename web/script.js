/*
   1. CONSTANTES E CONFIGURAÇÕES
 */
const CORES_CAT = {
    'SISTEMA':    '#ff2255',
    'INTERFACE':  '#aa44ff',
    'TERMINAL':   '#00d4ff',
    'WEB':        '#00ff88',
    'MÍDIA':      '#ff8c00',
    'SMART HOME': '#ff6600',
    'CLIMA':      '#00ddff',
    'UTILIDADES': '#7788aa',
    'MONITOR':    '#00ff88',
    'GERAL':      '#44556f',
};

const PAGINAS = [
    { 
        id: 'home',     
        rotulo: 'DIAGNÓSTICO',    
        icone: '◉' 
    },
    { 
        id: 'biblio',   
        rotulo: 'HOLO-BIBLIO',    
        icone: '◈' 
    },
    { 
        id: 'terminal', 
        rotulo: 'TERMINAL',       
        icone: '▶' 
    },
    { 
        id: 'chat',     
        rotulo: 'CHAT NEURAL',    
        icone: '◎' 
    },
    { 
        id: 'rede',     
        rotulo: 'REDE',           
        icone: '◐' 
    },
    { 
        id: 'notas',    
        rotulo: 'NOTAS',          
        icone: '◑' 
    },
    { 
        id: 'api',      
        rotulo: 'API KEYS',       
        icone: '◒' 
    },
    { 
        id: 'temas',    
        rotulo: 'VISUAL',         
        icone: '◓' 
    },
    { 
        id: 'tools',    
        rotulo: 'FERRAMENTAS',    
        icone: '⬡' 
    },
];

const CAMPOS_API = [
    { 
        chave: 'gemini',       
        rotulo: 'GEMINI AI',    
        emoji: '✦', 
        cor: '#4285F4' 
    },
    { 
        chave: 'qwen',         
        rotulo: 'QWEN COG',     
        emoji: '◈', 
        cor: '#ff6a00' 
    },
    { 
        chave: 'smartthings',  
        rotulo: 'SMARTTHINGS',  
        emoji: '⌂', 
        cor: '#1abcfe' 
    },
    { 
        chave: 'spotify_id',   
        rotulo: 'SPOTIFY ID',   
        emoji: '♪', 
        cor: '#1db954' 
    },
    { 
        chave: 'spotify_sec',  
        rotulo: 'SPOTIFY SEC',  
        emoji: '♫', 
        cor: '#1db954' 
    },
];

/*
   2. ESTADO GLOBAL DO SISTEMA
 */
const estado = {
    pagina: 0,
    tema: '',
    temasDoPython: {},
    notas: '// ÁREA DE NOTAS TÁTICAS\n',
    apis: { 
        gemini: '', 
        qwen: '', 
        smartthings: '', 
        spotify_id: '', 
        spotify_sec: '' 
    },
    apisDesbloqueadas: {},
    senhaAtual: '',
    tamanhoSenha: 24,
    opcoesSenha: { 
        maiusculas: true, 
        minusculas: true, 
        numeros: true, 
        especiais: true 
    },
    konami: [],
    comandosDoBanco: [],
    ia: { 
        modo: 'gemini', 
        gemini_disponivel: true, 
        ollama_disponivel: false 
    },
    metricas: {
        cpu: 0, 
        ram: 0, 
        gpu: 0,
        net_in: 0, 
        net_out: 0, 
        ping: 0, 
        disco: 0,
        freq: 2400, 
        uptime: 0,
        ram_usada: 0, 
        ram_total: 16,
        disco_livre: 250, 
        gpu_temp: 0,
    },
    logEntradas: [],
    terminalHistorico: [],
    chatHistorico: [],
    terminalCmds: [],
    terminalCmdIdx: -1,
};

/*
   3. INICIALIZAÇÃO E BRIDGE (QWEBCHANNEL)
 */
const scriptQWebChannel = document.createElement('script');
scriptQWebChannel.src = 'qrc:///qtwebchannel/qwebchannel.js';
document.head.appendChild(scriptQWebChannel);

scriptQWebChannel.onload = () => {
    new QWebChannel(qt.webChannelTransport, ch => {
        window.jarvis = ch.objects.jarvis;
        window.jarvis.dados_para_ui.connect(raw => {
            receberDoJarvis(JSON.parse(raw));
        });
        _carregarDados();
    });
};

async function _carregarDados() {
    const [temas, configs, biblioteca, temaAtivo, iaStatusRaw] = await Promise.all([
        _bridge('obter_temas_sistema'),
        _bridge('obter_configuracoes_atuais'),
        _bridge('obter_biblioteca_comandos'),
        _bridge('obter_tema_ativo'),
        _bridge('obter_ia_status'),
    ]);

    estado.temasDoPython = JSON.parse(temas || '{}');
    estado.comandosDoBanco = JSON.parse(biblioteca || '[]');

    const cfg = JSON.parse(configs || '{}');
    Object.assign(estado.apis, cfg);
    
    if (cfg.notas) {
        estado.notas = cfg.notas;
    }

    const iaStatus = JSON.parse(iaStatusRaw || '{}');
    estado.ia = {
        modo: iaStatus.modo || 'gemini',
        gemini_disponivel: iaStatus.gemini_disponivel !== false,
        ollama_disponivel: iaStatus.ollama_disponivel === true,
    };

    const ta = temaAtivo ? temaAtivo.replace(/^"|"$/g, '') : '';
    if (ta && estado.temasDoPython[ta]) {
        estado.tema = ta;
        _aplicarTema(ta);
    }

    renderizarPagina();
    _atualizarToggleIA();
}

function _bridge(metodo) {
    return new Promise(res => {
        if (!window.jarvis || !window.jarvis[metodo]) {
            return res(null);
        }
        window.jarvis[metodo](r => res(r));
    });
}

function receberDoJarvis(dados) {
    if (dados.cpu !== undefined) {
        estado.metricas.cpu = dados.cpu;
        estado.metricas.ram = dados.ram;
        if (estado.pagina === 0) {
            atualizarMetricas();
        }
    }

    if (dados.resposta !== undefined && dados.resposta !== null) {
        const respStr = typeof dados.resposta === 'string'
            ? dados.resposta
            : JSON.stringify(dados.resposta);
            
        adicionarLog('ok', respStr.slice(0, 80));
        toast(respStr.slice(0, 90));
    }

    if (dados.erro !== undefined && dados.erro !== null) {
        const erroStr = typeof dados.erro === 'string'
            ? dados.erro
            : JSON.stringify(dados.erro);
            
        adicionarLog('err', erroStr.slice(0, 80));
        toast(erroStr.slice(0, 90), 'erro');
    }

    if (dados.ia_status) {
        estado.ia = {
            modo: dados.ia_status.modo,
            gemini_disponivel: dados.ia_status.gemini_disponivel,
            ollama_disponivel: dados.ia_status.ollama_disponivel,
        };
        _atualizarToggleIA();
    }
}

function iniciarApp() {
    _construirNav();
    _relogio();
    _simularMetricas();
    navegarPara(0);
    
    document.addEventListener('keydown', _konami);
    
    adicionarLog('ok', 'C.O.R.E inicializado com sucesso');
    adicionarLog('info', 'Bridge aguardando conexão...');
    
    _injetarEstilosGlobais();
}

/*
   4. SISTEMA DE LOGS E EVENTOS GERAIS
 */
function enviarComando(cmd) {
    if (!window.jarvis) { 
        toast('Bridge não conectada.', 'erro'); 
        return; 
    }
    window.jarvis.executar_comando(cmd);
    toast('▶ ' + cmd.toUpperCase().slice(0, 50));
    adicionarLog('info', 'Executando: ' + cmd);
}

function adicionarLog(tipo, msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    estado.logEntradas.unshift({ tipo, msg, ts });
    
    if (estado.logEntradas.length > 60) {
        estado.logEntradas.pop();
    }
    _renderizarLog();
}

function _renderizarLog() {
    const el = document.getElementById('logStream');
    if (!el) return;
    
    el.innerHTML = estado.logEntradas.slice(0, 20).map(e => /*html*/`
        <div class="log-linha">
            <span class="log-ts">${e.ts}</span>
            <span class="log-${e.tipo}">${_escHtml(e.msg)}</span>
        </div>
    `).join('');
}

/*
   5. INJEÇÃO DE CSS VIA JS
 */
function _injetarEstilosGlobais() {
    const style = document.createElement('style');
    style.textContent = /*css*/`
        .cabecalho-pagina { 
            text-align: center; 
            margin-bottom: 18px; 
        }
        .cabecalho-pagina h2 { 
            font-size: 26px !important; 
            font-weight: 700 !important; 
            letter-spacing: 6px; 
            text-align: center; 
            margin-bottom: 8px; 
        }
        body, input, textarea, button, select { 
            font-weight: 600 !important; 
        }
        .label-secao { 
            font-size: 13px !important; 
            font-weight: 700 !important; 
            letter-spacing: 3px; 
        }
        .rotulo-metrica { 
            font-size: 12px !important; 
            font-weight: 700 !important; 
            letter-spacing: 2px; 
        }
        .valor-metrica { 
            font-size: 28px !important; 
            font-weight: 700 !important; 
        }
        .chave-rede { 
            font-size: 11px !important; 
            font-weight: 700 !important; 
        }
        .valor-rede { 
            font-size: 16px !important; 
            font-weight: 700 !important; 
        }
        .biblio-cmd { 
            font-size: 15px !important; 
            font-weight: 700 !important; 
            color: #aabbcc !important; 
            letter-spacing: 1px; 
        }
        .biblio-desc { 
            font-size: 12px !important; 
            font-weight: 600 !important; 
        }
        .biblio-label { 
            font-size: 11px !important; 
            font-weight: 700 !important; 
        }
        .nome-tema { 
            font-size: 16px !important; 
            font-weight: 700 !important; 
            letter-spacing: 2px; 
        }
        .btn-tema { 
            font-size: 12px !important; 
            font-weight: 700 !important; 
        }
        .btn-nav { 
            font-size: 12px !important; 
            font-weight: 700 !important; 
            letter-spacing: 1px; 
        }
        .log-linha { 
            font-size: 12px !important; 
            font-weight: 600 !important; 
        }
        .log-ts { 
            font-size: 11px !important; 
            font-weight: 600 !important; 
        }
        .chave-espec { 
            font-size: 11px !important; 
            font-weight: 700 !important; 
        }
        .val-espec { 
            font-size: 12px !important; 
            font-weight: 600 !important; 
        }
        .terminal-input, .entrada, .biblio-busca, .entrada-api { 
            font-size: 14px !important; 
            font-weight: 600 !important; 
        }
        .terminal-saida { 
            font-size: 13px !important; 
            font-weight: 600 !important; 
        }
        .terminal-prompt { 
            font-size: 13px !important; 
            font-weight: 700 !important; 
        }
        .chat-msg { 
            font-size: 14px !important; 
            font-weight: 600 !important; 
        }
        .btn { 
            font-size: 13px !important; 
            font-weight: 700 !important; 
            letter-spacing: 2px; 
        }
        .secao-titulo span { 
            font-size: 15px !important; 
            font-weight: 700 !important; 
            letter-spacing: 3px; 
        }
        #tituloPagina { 
            font-size: 20px !important; 
            font-weight: 700 !important; 
            letter-spacing: 4px; 
        }
        #relogio { 
            font-size: 18px !important; 
            font-weight: 700 !important; 
        }
        .sub-metrica { 
            font-size: 12px !important; 
            font-weight: 600 !important; 
        }
        .rotulo-api-label { 
            font-size: 14px !important; 
            font-weight: 700 !important; 
        }
        .distintivo { 
            font-size: 11px !important; 
            font-weight: 700 !important; 
        }
        .etiqueta { 
            font-size: 12px !important; 
            font-weight: 700 !important; 
        }

        #iaBadge {
            display: flex; 
            align-items: center; 
            gap: 5px;
            padding: 3px 10px; 
            border-radius: 4px;
            border: 1px solid var(--borda2);
            cursor: pointer; 
            transition: border-color .2s, box-shadow .2s;
            user-select: none;
        }
        #iaBadge:hover { 
            box-shadow: 0 0 8px rgba(0,212,255,.18); 
        }

        .ia-btn-modo {
            flex: 1; 
            padding: 11px 8px; 
            border-radius: 6px;
            cursor: pointer; 
            transition: all .2s; 
            text-align: center;
            background: transparent; 
            border: 1px solid var(--borda2);
            color: var(--texto2);
        }
        .ia-btn-modo:hover { 
            color: var(--texto); 
        }
        .ia-btn-modo .ia-label { 
            font-family: var(--orb); 
            font-size: 11px; 
            font-weight: 700; 
            letter-spacing: 1px; 
            margin-bottom: 3px; 
        }
        .ia-btn-modo .ia-sub { 
            font-family: var(--mono); 
            font-size: 9px; 
            opacity: .65; 
        }
        .ia-btn-modo .ia-ativo { 
            font-family: var(--mono); 
            font-size: 8px; 
            margin-top: 4px; 
            letter-spacing: 1px; 
        }

        .ia-dot {
            width: 7px; 
            height: 7px; 
            border-radius: 50%;
            display: inline-block; 
            transition: background .4s;
        }
        .ia-provider {
            display: flex; 
            align-items: center; 
            gap: 7px;
            font-family: var(--mono); 
            font-size: 10px; 
            color: var(--texto2); 
            font-weight: 700;
        }
        .ia-provider small { 
            font-size: 9px; 
            color: var(--texto3); 
        }
        .ia-dica {
            margin-top: 10px; 
            font-family: var(--mono); 
            font-size: 10px;
            color: var(--texto3); 
            line-height: 1.7; 
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);
}

/*
   6. NAVEGAÇÃO E UI PRINCIPAL
 */
function _construirNav() {
    const nav = document.getElementById('botoesNav');
    PAGINAS.forEach((p, i) => {
        const btn = document.createElement('button');
        btn.className = 'btn-nav' + (i === 0 ? ' ativo' : '');
        btn.innerHTML = `<span class="icone">${p.icone}</span>${p.rotulo}`;
        btn.onclick = () => navegarPara(i);
        btn.id = `bnav${i}`;
        nav.appendChild(btn);
    });
}

function navegarPara(i) {
    estado.pagina = i;
    PAGINAS.forEach((_, j) => {
        const b = document.getElementById(`bnav${j}`);
        if (b) {
            b.classList.toggle('ativo', j === i);
        }
    });
    
    document.getElementById('tituloPagina').textContent = PAGINAS[i].rotulo + ' ◈ C.O.R.E';
    renderizarPagina();
}

function renderizarPagina() {
    const area = document.getElementById('conteudo-principal');
    const fns = [
        pgDiagnostico, 
        pgBiblio, 
        pgTerminal, 
        pgChat,
        pgRede, 
        pgNotas, 
        pgApi, 
        pgTemas, 
        pgFerramentas,
    ];
    
    area.innerHTML = '';
    fns[estado.pagina]();
}

function _relogio() {
    const upd = () => {
        document.getElementById('relogio').textContent = new Date().toTimeString().slice(0, 8);
    };
    upd(); 
    setInterval(upd, 1000);
}

function _simularMetricas() {
    estado.metricas.uptime = Date.now();
    const tick = () => {
        const m = estado.metricas;
        m.cpu = _clamp(m.cpu + (Math.random() - .47) * 7, 3, 94);
        m.ram = _clamp(m.ram + (Math.random() - .49) * 2.5, 20, 90);
        m.gpu = _clamp(m.gpu + (Math.random() - .47) * 9, 0, 88);
        m.net_in = Math.max(0, +(Math.random() * 2.2).toFixed(2));
        m.net_out = Math.max(0, +(Math.random() * .55).toFixed(2));
        m.ping = Math.floor(18 + Math.random() * 65);
        m.disco = _clamp(m.disco + (Math.random() - .499) * .4, 28, 82);
        m.freq = Math.floor(2200 + Math.random() * 1300);
        m.gpu_temp = Math.floor(38 + m.gpu * .42);
        m.ram_usada = +((m.ram / 100) * m.ram_total).toFixed(1);
        
        if (estado.pagina === 0) {
            atualizarMetricas();
        }
    };
    tick(); 
    setInterval(tick, 800);
}

/*
   7. PÁGINAS E COMPONENTES ESPECÍFICOS
 */


// DIAGNÓSTICO

function pgDiagnostico() {
    const area = document.getElementById('conteudo-principal');
    const m = estado.metricas;
    
    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>DIAGNÓSTICO DO NÚCLEO</h2>
            <div class="linha-destaque"></div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:10px;">
            ${_cartaoMetrica('PROCESSADOR', 'v-cpu', 'p-cpu', Math.round(m.cpu) + '%', m.cpu, 'var(--destaque)', '')}
            ${_cartaoMetrica('MEMÓRIA RAM', 'v-ram', 'p-ram', Math.round(m.ram) + '%', m.ram, 'var(--destaque)', '')}
            ${_cartaoGpu(m)}
        </div>

        <div style="display:grid; grid-template-columns:1.6fr 1fr; gap:10px; margin-bottom:10px;">
            <div class="cartao">
                <div class="barra-topo" style="background:linear-gradient(90deg,#00aaff,#00ff88);"></div>
                <div class="grade-rede">
                    <div class="item-rede">
                        <div class="chave-rede">DOWNLOAD</div>
                        <div class="valor-rede" id="v-net-in" style="color:var(--verde);">${m.net_in} MB/s</div>
                    </div>
                    <div class="item-rede">
                        <div class="chave-rede">UPLOAD</div>
                        <div class="valor-rede" id="v-net-out" style="color:var(--verde);">${m.net_out} MB/s</div>
                    </div>
                    <div class="item-rede">
                        <div class="chave-rede">LATÊNCIA</div>
                        <div class="valor-rede" id="v-ping" style="color:var(--verde);">${m.ping} ms</div>
                    </div>
                </div>
            </div>
            
            <div class="cartao" style="display:flex; flex-direction:column; justify-content:center; padding:12px 14px; gap:6px;">
                <div class="label-secao">ARMAZENAMENTO</div>
                <div style="font-family:var(--orb); font-size:22px; font-weight:700; color:var(--amarelo);" id="v-disco">
                    ${Math.round(m.disco)}%
                </div>
                <div class="trilha">
                    <div class="barra" id="p-disco" style="width:${m.disco}%; background:linear-gradient(90deg,var(--amarelo),#ff8c00);"></div>
                </div>
                <div class="sub-metrica" id="v-disco-livre">${m.disco_livre} GB livre</div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px;">
            <div class="cartao">
                <div class="barra-topo" style="background:linear-gradient(90deg,var(--destaque),transparent);"></div>
                <div style="padding:10px 14px; display:flex; flex-direction:column; gap:5px;">
                    <div class="label-secao">ESPECIFICAÇÕES DO SISTEMA</div>
                    ${_espec('PLATAFORMA',  'Windows 10 x64')}
                    ${_espec('ARQUITETURA', 'AMD64')}
                    ${_espec('NÚCLEOS',     '8 / 16')}
                    ${_espec('FREQUÊNCIA',  `<span id="v-freq">${m.freq} MHz</span>`)}
                    ${_espec('RAM EM USO',  `<span id="v-ram-det">${m.ram_usada} / ${m.ram_total} GB</span>`)}
                    ${_espec('TEMPO ATIVO', `<span id="v-uptime">00:00:00</span>`)}
                    ${_espec('GPU TEMP',    `<span id="v-gputemp">${m.gpu_temp}°C</span>`)}
                </div>
            </div>
            
            <div class="cartao">
                <div class="barra-topo" style="background:linear-gradient(90deg,var(--verde),transparent);"></div>
                <div style="padding:10px 12px;">
                    <div class="label-secao" style="margin-bottom:7px;">LOG DE ATIVIDADE</div>
                    <div class="log-stream" id="logStream"></div>
                </div>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; margin-bottom:20px;">
            ${_cartaoAcaoRapida('BLOQUEAR TELA',  '⊡', 'bloquear',       'var(--roxo)')}
            ${_cartaoAcaoRapida('CAPTURA TELA',   '⊟', 'captura',        'var(--destaque)')}
            ${_cartaoAcaoRapida('LIMPAR LIXEIRA', '⊠', 'limpar lixeira', 'var(--vermelho)')}
        </div>
    `;
    
    _renderizarLog();
    atualizarMetricas();
}

function _cartaoMetrica(lbl, idV, idP, val, pct, cor, extra) {
    return /*html*/`
        <div class="cartao cartao-metrica">
            <div class="barra-topo" style="background:linear-gradient(90deg,${cor},var(--verde));"></div>
            <div class="metrica-interna">
                <div class="rotulo-metrica">${lbl}</div>
                <div class="valor-metrica" id="${idV}" style="color:${cor};">${val}</div>
                <div class="trilha">
                    <div class="barra" id="${idP}" style="width:${pct}%; background:linear-gradient(90deg,${cor},var(--verde));"></div>
                </div>
                ${extra}
            </div>
        </div>`;
}

function _cartaoGpu(m) {
    return /*html*/`
        <div class="cartao cartao-metrica">
            <div class="barra-topo" style="background:linear-gradient(90deg,var(--laranja),#ff4400);"></div>
            <div class="metrica-interna">
                <div class="rotulo-metrica">PROCESSADOR GRÁFICO</div>
                <div class="valor-metrica" id="v-gpu" style="color:var(--laranja);">${Math.round(m.gpu)}%</div>
                <div class="trilha">
                    <div class="barra" id="p-gpu" style="width:${m.gpu}%; background:linear-gradient(90deg,var(--laranja),#ff4400);"></div>
                </div>
                <div class="sub-metrica" id="v-gputemp2">${m.gpu_temp}°C</div>
            </div>
        </div>`;
}

function _cartaoAcaoRapida(label, icone, handler, cor) {
    return /*html*/`
        <div class="cartao" 
             onclick="enviarComando('${handler}')"
             style="cursor:pointer; padding:14px 16px; display:flex; align-items:center; gap:12px; transition:border-color .2s;"
             onmouseover="this.style.borderColor='${cor}'"
             onmouseout="this.style.borderColor=''">
            <span style="font-size:22px; color:${cor};">${icone}</span>
            <div>
                <div style="font-family:var(--mono); font-size:11px; color:var(--texto3); letter-spacing:2px; font-weight:700;">AÇÃO RÁPIDA</div>
                <div style="font-family:var(--orb); font-size:13px; font-weight:700; color:${cor};">${label}</div>
            </div>
        </div>`;
}

function _espec(chave, valor) {
    return /*html*/`
        <div class="linha-espec">
            <div class="chave-espec">${chave}</div>
            <div class="val-espec">${valor}</div>
        </div>`;
}

function atualizarMetricas() {
    const m = estado.metricas;
    const s = (id, v) => { 
        const el = document.getElementById(id); 
        if (el) el.textContent = v; 
    };
    const sc = (id, c) => { 
        const el = document.getElementById(id); 
        if (el) el.style.color = c; 
    };
    const sw = (id, p) => { 
        const el = document.getElementById(id); 
        if (el) el.style.width = p + '%'; 
    };

    const cCpu = m.cpu > 85 ? 'var(--vermelho)' : m.cpu > 60 ? 'var(--laranja)' : 'var(--destaque)';
    s('v-cpu', Math.round(m.cpu) + '%'); 
    sw('p-cpu', m.cpu); 
    sc('v-cpu', cCpu);

    const cRam = m.ram > 85 ? 'var(--vermelho)' : 'var(--destaque)';
    s('v-ram', Math.round(m.ram) + '%'); 
    sw('p-ram', m.ram); 
    sc('v-ram', cRam);

    const cGpu = m.gpu > 85 ? 'var(--vermelho)' : 'var(--laranja)';
    s('v-gpu', Math.round(m.gpu) + '%'); 
    sw('p-gpu', m.gpu); 
    sc('v-gpu', cGpu);
    s('v-gputemp2', m.gpu_temp + '°C');

    s('v-net-in',  m.net_in  + ' MB/s');
    s('v-net-out', m.net_out + ' MB/s');

    const cPing = m.ping > 150 ? 'var(--vermelho)' : m.ping < 50 ? 'var(--verde)' : 'var(--amarelo)';
    s('v-ping', m.ping + ' ms'); 
    sc('v-ping', cPing);

    s('v-disco', Math.round(m.disco) + '%'); 
    sw('p-disco', m.disco);
    s('v-disco-livre', m.disco_livre + ' GB livre');

    s('v-freq',    m.freq     + ' MHz');
    s('v-ram-det', m.ram_usada + ' / ' + m.ram_total + ' GB');
    s('v-gputemp', m.gpu_temp  + '°C');

    const seg = Math.floor((Date.now() - m.uptime) / 1000);
    const h   = Math.floor(seg / 3600);
    const min = Math.floor((seg % 3600) / 60);
    const sc2 = seg % 60;
    
    s('v-uptime', `${_zp(h)}:${_zp(min)}:${_zp(sc2)}`);
}


// HOLO-BIBLIO

function pgBiblio() {
    const area = document.getElementById('conteudo-principal');
    const cats = [...new Set(estado.comandosDoBanco.map(c => c.cat))].sort();

    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>HOLO-BIBLIO</h2>
            <div class="linha-destaque"></div>
        </div>
        
        <div class="biblio-filtros">
            <select id="bCat" class="biblio-select" onchange="_filtrarBiblio()">
                <option value="">TODAS AS CATEGORIAS</option>
                ${cats.map(c => `<option value="${c}">${c}</option>`).join('')}
            </select>
            <input id="bBusca" class="biblio-busca" placeholder="Pesquisar comando..." oninput="_filtrarBiblio()">
            <span class="biblio-hint">CLIQUE PARA EXECUTAR</span>
        </div>
        
        <div class="grade-biblio" id="gradeBiblio"></div>
    `;

    window._cmdsCache = estado.comandosDoBanco;
    _filtrarBiblio();
}

function _filtrarBiblio() {
    const busca = (document.getElementById('bBusca')?.value || '').toLowerCase();
    const cat = document.getElementById('bCat')?.value || '';
    
    const lista = (window._cmdsCache || []).filter(c =>
        (!cat || c.cat === cat) &&
        (!busca || c.cmd.toLowerCase().includes(busca) || c.desc.toLowerCase().includes(busca))
    );

    const grade = document.getElementById('gradeBiblio');
    if (!grade) return;

    if (!lista.length) {
        grade.innerHTML = /*html*/`
            <div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--texto3); font-family:var(--mono); font-size:13px; font-weight:700;">
                Nenhum comando encontrado.
            </div>`;
        return;
    }

    grade.innerHTML = lista.map((cmd, i) => {
        const cor = CORES_CAT[cmd.cat] || '#44556f';
        const he  = (cmd.handler || '').replace(/'/g, "\\'");
        
        return /*html*/`
            <div class="cartao-biblio animar" 
                 style="animation-delay:${i * .02}s"
                 onmouseover="this.style.borderColor='${cor}'; this.style.transform='translateY(-2px)'"
                 onmouseout="this.style.borderColor=''; this.style.transform=''"
                 onclick="executarBiblio('${he}')">
                <div class="biblio-topo" style="background:${cor};"></div>
                <div class="biblio-corpo">
                    <div class="biblio-linha1">
                        <div class="biblio-cmd">${_escHtml(cmd.cmd)}</div>
                        <span class="biblio-poder">${cmd.poder || '⚡'}</span>
                    </div>
                    <div class="biblio-desc">${_escHtml(cmd.desc)}</div>
                </div>
                <div class="biblio-rodape">
                    <div class="biblio-dot" style="background:${cor};"></div>
                    <span class="biblio-label">EXECUTAR</span>
                </div>
            </div>`;
    }).join('');
}

function executarBiblio(handler) {
    if (!handler || !handler.trim()) { 
        toast('Handler não definido.', 'aviso'); 
        return; 
    }
    enviarComando(handler.trim());
}


// TERMINAL

function pgTerminal() {
    const area = document.getElementById('conteudo-principal');
    const atalhos = [
        'status sistema',
        'clima',
        'minha memória',
        'monitorar tela',
        'desligar monitor',
        'monitor status'
    ];

    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>TERMINAL NEURAL</h2>
            <div class="linha-destaque"></div>
        </div>
        
        <div class="terminal-box">
            <div class="terminal-topbar">
                <div class="terminal-dot" style="background:#ff2255;"></div>
                <div class="terminal-dot" style="background:#ffcc00;"></div>
                <div class="terminal-dot" style="background:#00ff88;"></div>
                <span class="terminal-titulo">C.O.R.E ◈ SHELL</span>
            </div>
            
            <div class="terminal-saida" id="termSaida">
                <span style="color:var(--destaque);">C.O.R.E</span>
                <span style="color:var(--texto3);"> Neural Terminal — Digite um comando abaixo</span><br>
            </div>
            
            <div class="terminal-input-row">
                <span class="terminal-prompt">core@system:~$</span>
                <input class="terminal-input" id="termInput" placeholder="execute um comando..." onkeydown="_termKeydown(event)">
            </div>
        </div>
        
        <div style="margin-top:10px; display:flex; gap:6px; flex-wrap:wrap;">
            ${atalhos.map(c => `
                <span class="etiqueta" onclick="_termAtalho('${c}')">${c}</span>
            `).join('')}
        </div>
    `;
    
    document.getElementById('termInput')?.focus();
}

function _termKeydown(e) {
    const inp = e.target;
    
    if (e.key === 'Enter') {
        const cmd = inp.value.trim();
        if (!cmd) return;
        
        estado.terminalCmds.unshift(cmd);
        estado.terminalCmdIdx = -1;
        
        _termOutput(`<span style="color:var(--destaque);">$</span> ${_escHtml(cmd)}`);
        enviarComando(cmd);
        inp.value = '';
        
    } else if (e.key === 'ArrowUp') {
        estado.terminalCmdIdx = Math.min(estado.terminalCmdIdx + 1, estado.terminalCmds.length - 1);
        inp.value = estado.terminalCmds[estado.terminalCmdIdx] || '';
        e.preventDefault();
        
    } else if (e.key === 'ArrowDown') {
        estado.terminalCmdIdx = Math.max(estado.terminalCmdIdx - 1, -1);
        inp.value = estado.terminalCmds[estado.terminalCmdIdx] || '';
        e.preventDefault();
    }
}

function _termAtalho(cmd) {
    const input = document.getElementById('termInput');
    input.value = cmd;
    input.focus();
}

function _termOutput(html) {
    const s = document.getElementById('termSaida');
    if (!s) return;
    
    s.innerHTML += `<div style="line-height:1.7;">${html}</div>`;
    s.scrollTop = s.scrollHeight;
}


// CHAT NEURAL

function pgChat() {
    const area = document.getElementById('conteudo-principal');
    
    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>CHAT NEURAL</h2>
            <div class="linha-destaque"></div>
        </div>
        
        <div class="chat-box">
            <div class="chat-msgs" id="chatMsgs">
                <div class="chat-msg core">
                    <strong>C.O.R.E</strong>
                    Sistemas online. Como posso ajudar, Chefe?
                </div>
            </div>
            
            <div class="chat-input-row">
                <input class="entrada full" id="chatInput" placeholder="Mensagem para o C.O.R.E..." onkeydown="if(event.key==='Enter') enviarChat()">
                <button class="btn btn-destaque" onclick="enviarChat()">ENVIAR</button>
            </div>
        </div>
    `;
}

function enviarChat() {
    const inp = document.getElementById('chatInput');
    const msg = inp?.value?.trim();
    
    if (!msg) return;
    
    inp.value = '';
    _chatMsg('user', msg);
    enviarComando(msg);
    
    setTimeout(() => {
        _chatMsg('core', '▸ Processando...');
    }, 200);
}

function _chatMsg(role, txt) {
    const box = document.getElementById('chatMsgs');
    if (!box) return;
    
    const d = document.createElement('div');
    d.className = `chat-msg ${role}`;
    
    d.innerHTML = role === 'core'
        ? `<strong>C.O.R.E</strong>${_escHtml(txt)}`
        : _escHtml(txt);
        
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
}


// REDE E CONEXÕES

function pgRede() {
    const area = document.getElementById('conteudo-principal');
    const ifaces = [
        { nome: 'Ethernet', ok: true,  ip: '192.168.0.10', v: '1000 Mbps' },
        { nome: 'Wi-Fi',    ok: true,  ip: '192.168.0.11', v: '300 Mbps'  },
        { nome: 'Loopback', ok: true,  ip: '127.0.0.1',    v: '—'         },
        { nome: 'VPN0',     ok: false, ip: 'N/A',          v: '—'         },
    ];

    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>REDE & CONEXÕES</h2>
            <div class="linha-destaque" style="background:linear-gradient(90deg,#00aaff,transparent);"></div>
        </div>
        
        <div class="grade4" style="margin-bottom:10px;">
            ${ifaces.map(f => /*html*/`
                <div class="cartao cartao-interface">
                    <div class="barra-topo" style="background:${f.ok ? 'var(--verde)' : 'var(--vermelho)'};"></div>
                    <div class="interface-interna">
                        <div class="nome-interface" style="color:${f.ok ? 'var(--texto)' : 'var(--texto3)'}; font-size:15px; font-weight:700;">
                            ${f.nome}
                        </div>
                        <div class="status-iface">
                            <div class="ponto" style="background:${f.ok ? 'var(--verde)' : 'var(--vermelho)'};"></div>
                            <span style="color:${f.ok ? 'var(--verde)' : 'var(--vermelho)'}; font-size:11px; font-family:var(--mono); font-weight:700;">
                                ${f.ok ? 'ATIVO' : 'INATIVO'}
                            </span>
                        </div>
                        <div class="ip-iface" style="font-size:13px; font-weight:600;">${f.ip}</div>
                        <div style="font-family:var(--mono); font-size:11px; color:var(--texto3); margin-top:3px; font-weight:600;">
                            ${f.v}
                        </div>
                    </div>
                </div>`).join('')}
        </div>
        
        <div class="grade2">
            <div class="cartao ferramenta-ping">
                <div class="label-secao" style="margin-bottom:7px;">PING MANUAL</div>
                <div class="linha-ping">
                    <input id="inputPing" class="entrada" value="8.8.8.8" style="flex:1;">
                    <button class="btn btn-destaque" onclick="dispararPing()">PINGAR</button>
                    <div class="resultado-ping" id="resPing" style="font-size:16px; font-weight:700;">—</div>
                </div>
                <div style="font-family:var(--mono); font-size:11px; color:var(--texto3); font-weight:600;">Timeout 2s</div>
            </div>
            
            <div class="cartao" style="padding:14px;">
                <div class="label-secao" style="margin-bottom:8px;">TRANSFERÊNCIA DA SESSÃO</div>
                <div style="font-family:var(--orb); font-size:18px; font-weight:700; color:var(--verde); margin-bottom:6px;">
                    Recebido: 1.24 GB
                </div>
                <div style="font-family:var(--orb); font-size:18px; font-weight:700; color:var(--destaque);">
                    Enviado: 0.38 GB
                </div>
            </div>
        </div>
    `;
}

function dispararPing() {
    const el = document.getElementById('resPing');
    el.textContent = '...'; 
    el.style.color = 'var(--texto2)';
    
    setTimeout(() => {
        const ms = Math.floor(18 + Math.random() * 180);
        const cor = ms > 150 ? 'var(--vermelho)' : ms < 50 ? 'var(--verde)' : 'var(--amarelo)';
        el.textContent = ms + ' ms'; 
        el.style.color = cor;
    }, 380 + Math.random() * 420);
}


// NOTAS TÁTICAS

function pgNotas() {
    const area = document.getElementById('conteudo-principal');
    
    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>NOTAS TÁTICAS</h2>
            <div class="linha-destaque" style="background:linear-gradient(90deg,var(--roxo),transparent);"></div>
        </div>
        
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <span style="font-family:var(--mono); font-size:11px; color:var(--texto3); font-weight:600;">
                ÚLTIMA EDIÇÃO: ${new Date().toLocaleString('pt-BR')}
            </span>
            <div style="display:flex; gap:6px;">
                <button class="btn btn-perigo" onclick="limparNotas()">LIMPAR</button>
                <button class="btn btn-roxo" onclick="salvarNotas()">SALVAR</button>
            </div>
        </div>
        
        <div class="botoes-modelo">
            <span style="font-family:var(--mono); font-size:10px; color:var(--texto3); align-self:center; font-weight:700;">MODELOS:</span>
            <span class="etiqueta" onclick="insertNota('IP: \\nMáscara: \\nGateway: \\n')">REDE IP</span>
            <span class="etiqueta" onclick="insertNota('# CMD\\n$ \\n# Saída:\\n')">COMANDO</span>
            <span class="etiqueta" onclick="insertNota('[ ] Primária\\n[ ] Secundária\\n')">TODO</span>
            <span class="etiqueta" onclick="insertNota('---\\nDATA: ${new Date().toLocaleDateString('pt-BR')}\\nLOG: \\n---\\n')">LOG</span>
        </div>
        
        <textarea id="notasTxt" class="area-notas">${_escHtml(estado.notas)}</textarea>
    `;
}

function salvarNotas() {
    const a = document.getElementById('notasTxt');
    if (!a) return;
    
    estado.notas = a.value;
    if (window.jarvis) {
        window.jarvis.salvar_configuracao('notas', estado.notas);
    }
    toast('Notas salvas.');
}

function limparNotas() {
    if (!confirm('Apagar todas as notas?')) return;
    
    estado.notas = '';
    const a = document.getElementById('notasTxt');
    if (a) {
        a.value = '';
    }
}

function insertNota(t) {
    const a = document.getElementById('notasTxt');
    if (a) { 
        a.value += t; 
        a.focus(); 
    }
}


// API KEYS E INTELIGÊNCIA ARTIFICIAL

function pgApi() {
    const area = document.getElementById('conteudo-principal');
    
    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>API KEYS & INTELIGÊNCIA</h2>
            <div class="linha-destaque"></div>
        </div>

        ${_renderizarSeletorIA()}

        <div class="secao-titulo" style="margin-top:20px;">
            <span style="color:var(--texto2);">CREDENCIAIS</span>
            <div class="secao-linha"></div>
        </div>
        
        <div style="font-family:var(--mono); font-size:20px; color:var(--texto3); margin-bottom:25px; font-weight:600; text-align:center;">
            CAMPOS BLOQUEADOS APÓS SALVAR — CLIQUE EM 🔒 PARA EDITAR
        </div>
        
        <div class="grade2">
            ${CAMPOS_API.map(c => _campoApi(c)).join('')}
        </div>
        
        <div style="max-width:860px; margin-top:16px; text-align:right;">
            <button class="btn btn-destaque" style="padding:10px 36px; letter-spacing:3px;" onclick="salvarApis()">
                GRAVAR NO NÚCLEO
            </button>
        </div>
    `;
    
    _atualizarToggleIA();
}

function _renderizarSeletorIA() {
    const ia = estado.ia;
    const cors = { 
        gemini: '#4285F4', 
        ollama: 'var(--verde)', 
        auto: 'var(--amarelo)' 
    };

    return /*html*/`
        <div class="secao-titulo" style="margin-top:0;">
            <span style="color:var(--destaque);">◈ NÚCLEO DE INTELIGÊNCIA</span>
            <div class="secao-linha"></div>
        </div>
        
        <div class="cartao" style="padding:18px 20px; margin-bottom:4px;">
            <div style="font-family:var(--mono); font-size:15px; color:var(--texto3); letter-spacing:2px; margin-bottom:14px; font-weight:700;">
                MODELO ATIVO — TROCA EM TEMPO REAL SEM REINICIALIZAÇÃO
            </div>

            <div style="display:flex; gap:8px; margin-bottom:18px;">
                ${_btnModoIA('gemini', '✦ GEMINI', 'Nuvem · Google AI', cors.gemini, ia.modo)}
                ${_btnModoIA('ollama', '⬡ OLLAMA', 'Local · Llama 3',   cors.ollama, ia.modo)}
                ${_btnModoIA('auto',   '◎ AUTO',   'Gemini + Fallback', cors.auto,   ia.modo)}
            </div>

            <div style="display:flex; gap:20px; padding:10px 14px; background:var(--fundo); border:1px solid var(--borda); border-radius:5px; align-items:center;">
                <div class="ia-provider" style="font-family:var(--mono); font-size:15px;">
                    <div class="ia-dot" id="ia-dot-gemini" style="background:${ia.gemini_disponivel !== false ? 'var(--verde)' : 'var(--vermelho)'};"></div>
                    GEMINI API
                </div>
                <div class="ia-provider" style="font-family:var(--mono); font-size:15px;">
                    <div class="ia-dot" id="ia-dot-ollama" style="background:${ia.ollama_disponivel === true ? 'var(--verde)' : 'var(--vermelho)'};"></div>
                    OLLAMA LOCAL
                    <small>:11434</small>
                </div>
                <div style="flex:1; text-align:right; font-family:var(--mono); font-size:15px; color:var(--texto3); font-weight:600;">
                    Iniciar Ollama: <span style="color:var(--verde);">ollama run llama3</span>
                </div>
            </div>

            <div class="ia-dica" style="font-family:var(--mono); font-size:15px;">
                <span style="color:var(--amarelo);">◎ AUTO</span> — tenta Gemini primeiro.
                Se falhar (sem chave ou cota), usa Ollama automaticamente.
            </div>
        </div>
    `;
}

function _btnModoIA(modo, label, sub, cor, modoAtivo) {
    const ativo = modoAtivo === modo;
    return /*html*/`
        <button id="ia-btn-${modo}" class="ia-btn-modo"
            onclick="alternarIA('${modo}')"
            style="border-color:${ativo ? cor : 'var(--borda2)'};
                   color:${ativo ? cor : 'var(--texto2)'};
                   background:${ativo ? `color-mix(in srgb,${cor} 12%,transparent)` : 'transparent'};
                   box-shadow:${ativo ? `0 0 12px color-mix(in srgb,${cor} 22%,transparent)` : 'none'};"
            onmouseover="this.style.borderColor='${cor}'; this.style.color='${cor}'"
            onmouseout="if(estado.ia.modo!=='${modo}') { this.style.borderColor='var(--borda2)'; this.style.color='var(--texto2)' }">
            <div class="ia-label">${label}</div>
            <div class="ia-sub">${sub}</div>
            ${ativo ? `<div class="ia-ativo" style="color:${cor};">● ATIVO</div>` : ''}
        </button>`;
}

function alternarIA(modo) {
    if (!window.jarvis) { 
        toast('Bridge não conectada.', 'erro'); 
        return; 
    }

    estado.ia.modo = modo;
    _atualizarToggleIA();

    const nomes = { 
        gemini: 'Gemini (nuvem)', 
        ollama: 'Ollama Llama 3 (local)', 
        auto: 'Auto' 
    };
    
    toast(`▶ IA: ${nomes[modo] || modo}`);
    adicionarLog('info', `IA alterada → ${modo.toUpperCase()}`);

    window.jarvis.alternar_ia(modo, resultado => {
        try {
            const r = JSON.parse(resultado || '{}');
            if (!r.ok) {
                toast('Erro ao alternar IA.', 'erro');
            }
        } catch (_) {}
    });
}

function _atualizarToggleIA() {
    const ia = estado.ia || { 
        modo: 'gemini', 
        gemini_disponivel: true, 
        ollama_disponivel: false 
    };
    const cors = { 
        gemini: '#4285F4', 
        ollama: 'var(--verde)', 
        auto: 'var(--amarelo)' 
    };
    const icons = { 
        gemini: '✦', 
        ollama: '⬡', 
        auto: '◎' 
    };
    
    const cor = cors[ia.modo] || 'var(--texto2)';
    const icon = icons[ia.modo] || '?';

    const badge = document.getElementById('iaBadge');
    if (badge) {
        badge.innerHTML = /*html*/`
            <span style="color:${cor}; font-size:11px;">${icon}</span>
            <span style="color:${cor}; font-family:var(--mono); font-size:10px; font-weight:700; letter-spacing:1px;">
                ${ia.modo.toUpperCase()}
            </span>`;
        badge.style.borderColor = cor;
    }

    ['gemini', 'ollama', 'auto'].forEach(m => {
        const btn = document.getElementById(`ia-btn-${m}`);
        if (!btn) return;
        
        const c = cors[m];
        const ativo = ia.modo === m;
        
        btn.style.borderColor = ativo ? c : 'var(--borda2)';
        btn.style.color = ativo ? c : 'var(--texto2)';
        btn.style.background = ativo ? `color-mix(in srgb,${c} 12%,transparent)` : 'transparent';
        btn.style.boxShadow = ativo ? `0 0 12px color-mix(in srgb,${c} 22%,transparent)` : 'none';
    });

    const dotG = document.getElementById('ia-dot-gemini');
    const dotO = document.getElementById('ia-dot-ollama');
    
    if (dotG) {
        dotG.style.background = ia.gemini_disponivel !== false ? 'var(--verde)' : 'var(--vermelho)';
    }
    if (dotO) {
        dotO.style.background = ia.ollama_disponivel === true ? 'var(--verde)' : 'var(--vermelho)';
    }
}

function _campoApi(campo) {
    const tem = !!estado.apis[campo.chave];
    const bloq = tem && !estado.apisDesbloqueadas[campo.chave];
    const corBorda = tem ? campo.cor : 'var(--borda2)';

    return /*html*/`
        <div class="campo-api">
            <div class="rotulo-api">
                <span class="rotulo-api-label" style="color:${campo.cor};">${campo.emoji} ${campo.rotulo}</span>
                <div style="display:flex; align-items:center; gap:6px;">
                    <span class="distintivo ${tem ? 'ok' : 'nok'}">${tem ? 'VINCULADO' : 'PENDENTE'}</span>
                    ${tem ? `
                        <button class="btn-lock" id="lock-${campo.chave}" onclick="toggleLock('${campo.chave}')">
                            ${bloq ? '🔒' : '🔓'}
                        </button>
                    ` : ''}
                </div>
            </div>
            <div class="api-row">
                <input type="password" class="entrada-api" id="api-${campo.chave}"
                       placeholder="${campo.rotulo}..."
                       value="${_escAttr(estado.apis[campo.chave] || '')}"
                       ${bloq ? 'readonly' : ''}
                       style="border-color:${corBorda};">
            </div>
        </div>`;
}

function toggleLock(chave) {
    estado.apisDesbloqueadas[chave] = !estado.apisDesbloqueadas[chave];
    const inp = document.getElementById(`api-${chave}`);
    const btn = document.getElementById(`lock-${chave}`);
    const d = estado.apisDesbloqueadas[chave];
    
    if (inp) { 
        inp.readOnly = !d; 
        inp.style.opacity = d ? '1' : ''; 
    }
    if (btn) {
        btn.textContent = d ? '🔓' : '🔒';
    }
    if (d) { 
        inp?.focus(); 
        toast('Campo desbloqueado para edição.', 'aviso'); 
    } else {
        toast('Campo bloqueado.');
    }
}

function salvarApis() {
    CAMPOS_API.forEach(c => {
        const inp = document.getElementById(`api-${c.chave}`);
        if (inp) {
            const v = inp.value;
            estado.apis[c.chave] = v;
            if (window.jarvis && v) {
                window.jarvis.salvar_configuracao(c.chave, v);
            }
        }
    });
    
    CAMPOS_API.forEach(c => { 
        if (estado.apis[c.chave]) {
            estado.apisDesbloqueadas[c.chave] = false; 
        }
    });
    
    pgApi();
    toast('Credenciais gravadas no núcleo.');
}


// VISUAL E TEMAS

function pgTemas() {
    const area = document.getElementById('conteudo-principal');
    const temas = estado.temasDoPython;
    const ids = Object.keys(temas);

    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>PROTOCOLO VISUAL</h2>
            <div class="linha-destaque"></div>
        </div>
        ${ids.length === 0
            ? `<div style="text-align:center; padding:40px; color:var(--texto3); font-family:var(--mono); font-size:13px; font-weight:700;">Carregando temas do Python...</div>`
            : ids.map(id => {
                const t = temas[id];
                const cor = t.accent || t.grad_a || '#00ff88';
                const cor2 = t.secondary || t.grad_b || '#00aa55';
                const ativo = estado.tema === id;
                
                return /*html*/`
                    <div class="linha-tema" onclick="aplicarTema('${id}')" style="border-color:${ativo ? cor : 'var(--borda)'}; padding:14px 18px;">
                        <div class="ponto-tema" style="background:${cor}; box-shadow:0 0 7px ${cor}55;"></div>
                        <div class="nome-tema" style="color:${cor}; font-size:17px; font-weight:700; letter-spacing:2px;">${id}</div>
                        <div style="display:flex; gap:5px; align-items:center;">
                            <div style="width:24px; height:9px; border-radius:3px; background:${cor};"></div>
                            <div style="width:24px; height:9px; border-radius:3px; background:${cor2};"></div>
                        </div>
                        <button class="btn-tema" style="border-color:${cor}; color:${cor}; background:${ativo ? cor + '22' : 'transparent'}; font-size:13px; font-weight:700; padding:6px 16px;">
                            ${ativo ? 'ATIVO' : 'APLICAR'}
                        </button>
                    </div>`;
            }).join('')
        }
        <div style="margin-top:14px; padding:14px 16px; background:var(--cartao); border:1px solid var(--borda); border-radius:6px;">
            <div style="font-family:var(--mono); font-size:10px; color:var(--texto3); letter-spacing:2px; margin-bottom:4px; font-weight:700;">PERSISTÊNCIA</div>
            <div style="font-size:13px; color:var(--texto2); font-weight:600;">Tema salvo em <span style="color:var(--destaque);">api/config_core.json</span> e restaurado no próximo boot.</div>
        </div>
    `;
}

function _aplicarTema(id) {
    const t = estado.temasDoPython[id];
    if (!t) return;
    
    const r = document.documentElement;
    
    // 1. Aplica as cores base definidas no theme.py
    r.style.setProperty('--destaque', t.accent);
    r.style.setProperty('--verde', t.secondary);
    r.style.setProperty('--fundo', t.bg);
    r.style.setProperty('--cartao', t.card);
    r.style.setProperty('--borda', t.border);
    
    // 2. Aplica a nova cor "surface" (ou usa o card como alternativa se não existir)
    r.style.setProperty('--superficie', t.surface || t.card);
    r.style.setProperty('--borda2', t.border);


    const degradeFundo = `radial-gradient(circle at 50% -10%, color-mix(in srgb, ${t.accent} 15%, ${t.bg}), ${t.bg} 80%)`;
    document.body.style.background = degradeFundo;
    
    const painelLateral = document.getElementById('barra-lateral');
    if (painelLateral) {
        const corTopo = t.surface || t.card;
        const degradeLateral = `linear-gradient(180deg, ${corTopo} 0%, color-mix(in srgb, ${t.bg} 85%, ${t.accent} 15%) 100%)`;
        painelLateral.style.background = degradeLateral;
    }
}

function aplicarTema(id) {
    if (!estado.temasDoPython[id]) return;
    
    estado.tema = id;
    _aplicarTema(id);
    
    if (window.jarvis) {
        window.jarvis.salvar_configuracao('tema_ativo', id);
    }
    
    pgTemas();
    toast('Tema ' + id + ' ativado.');
}


// FERRAMENTAS E UTILITÁRIOS INTERNOS

function pgFerramentas() {
    const area = document.getElementById('conteudo-principal');
    const toggleKeys = ['maiusculas', 'minusculas', 'numeros', 'especiais'];
    
    area.innerHTML = /*html*/`
        <div class="cabecalho-pagina animar">
            <h2>FERRAMENTAS DO SISTEMA</h2>
            <div class="linha-destaque" style="background:linear-gradient(90deg,var(--amarelo),transparent);"></div>
        </div>

        <div class="secao-titulo">
            <span style="color:var(--amarelo);">GERADOR DE SENHAS</span>
            <div class="secao-linha"></div>
        </div>
        
        <div class="cartao" style="padding:14px;">
            <div class="tela-senha" id="dispSenha">${estado.senhaAtual || 'Aguardando geração...'}</div>
            <div class="linha-range" style="margin-top:12px;">
                <label style="font-weight:700;">COMPRIMENTO</label>
                <input type="range" id="rngSenha" min="8" max="64" value="${estado.tamanhoSenha}"
                       oninput="document.getElementById('valSenha').textContent=this.value; estado.tamanhoSenha=+this.value">
                <span class="range-val" id="valSenha" style="font-size:15px; font-weight:700;">${estado.tamanhoSenha}</span>
            </div>
            
            <div class="opcoes-senha">
                ${toggleKeys.map(op => {
                    const lab = { 
                        maiusculas: 'A-Z', 
                        minusculas: 'a-z', 
                        numeros: '0-9', 
                        especiais: '!@#' 
                    }[op];
                    return /*html*/`
                    <div class="toggle-opcao ${estado.opcoesSenha[op] ? 'on' : ''}" id="opc-${op}" onclick="toggleOpcSenha('${op}')">
                        <div class="ponto"></div>
                        ${lab}
                    </div>`;
                }).join('')}
            </div>
            
            <div class="linha-botoes">
                <button class="btn btn-amarelo" onclick="gerarSenha()">GERAR CHAVE</button>
                <button class="btn btn-destaque" onclick="copiarSenha()">COPIAR</button>
            </div>
        </div>

        <div class="secao-titulo" style="margin-top:14px;">
            <span style="color:var(--destaque);">GERADOR DE HASH</span>
            <div class="secao-linha"></div>
        </div>
        
        <div class="cartao" style="padding:14px;">
            <input id="hashInput" class="entrada full" style="margin-bottom:9px;" placeholder="Texto para hash...">
            <div class="linha-botoes" style="margin-bottom:9px; margin-top:0;">
                <button class="btn btn-destaque" onclick="calcHash('SHA-256')">SHA-256</button>
                <button class="btn btn-verde"    onclick="calcHash('SHA-1')">SHA-1</button>
                <button class="btn btn-roxo"     onclick="calcMd5()">MD5</button>
            </div>
            <div class="tela-hash" id="hashRes">—</div>
        </div>

        <div class="secao-titulo" style="margin-top:14px;">
            <span style="color:var(--verde);">BASE64</span>
            <div class="secao-linha"></div>
        </div>
        
        <div class="cartao" style="padding:14px;">
            <input id="b64Input" class="entrada full" style="margin-bottom:9px;" placeholder="Texto ou Base64...">
            <div class="linha-botoes" style="margin-top:0;">
                <button class="btn btn-verde"    onclick="b64(true)">CODIFICAR</button>
                <button class="btn btn-destaque" onclick="b64(false)">DECODIFICAR</button>
            </div>
            <div class="tela-hash" id="b64Res" style="margin-top:9px;">—</div>
        </div>
    `;
}

function toggleOpcSenha(k) {
    estado.opcoesSenha[k] = !estado.opcoesSenha[k];
    const el = document.getElementById(`opc-${k}`);
    if (el) {
        el.classList.toggle('on', estado.opcoesSenha[k]);
    }
}

function gerarSenha() {
    let c = '';
    if (estado.opcoesSenha.maiusculas) c += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
    if (estado.opcoesSenha.minusculas) c += 'abcdefghijklmnopqrstuvwxyz';
    if (estado.opcoesSenha.numeros)    c += '0123456789';
    if (estado.opcoesSenha.especiais)  c += '!@#$%^&*_-+=?';
    
    if (!c) {
        c = 'ABCDEFabcdef0123456789';
    }
    
    const arr = new Uint8Array(estado.tamanhoSenha);
    crypto.getRandomValues(arr);
    
    estado.senhaAtual = Array.from(arr).map(b => c[b % c.length]).join('');
    
    const el = document.getElementById('dispSenha');
    if (el) { 
        el.textContent = estado.senhaAtual; 
        el.classList.remove('nova'); 
        void el.offsetWidth; // Reflow force hack to restart animation
        el.classList.add('nova'); 
    }
}

function copiarSenha() {
    if (!estado.senhaAtual) return;
    
    navigator.clipboard?.writeText(estado.senhaAtual).then(() => {
        toast('Senha copiada.');
    });
}

async function calcHash(alg) {
    const txt = document.getElementById('hashInput')?.value || '';
    const el = document.getElementById('hashRes');
    
    if (!txt || !el) return;
    
    const buf = await crypto.subtle.digest(alg, new TextEncoder().encode(txt));
    el.textContent = Array.from(new Uint8Array(buf))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}

function calcMd5() {
    const bytes = new Uint8Array(16); 
    crypto.getRandomValues(bytes);
    const el = document.getElementById('hashRes');
    
    if (el) {
        el.textContent = Array.from(bytes)
            .map(b => b.toString(16).padStart(2, '0'))
            .join('') + ' (simulado)';
    }
}

function b64(enc) {
    const txt = document.getElementById('b64Input')?.value || '';
    const el = document.getElementById('b64Res');
    
    if (!el) return;
    
    try {
        el.textContent = enc
            ? btoa(unescape(encodeURIComponent(txt)))
            : decodeURIComponent(escape(atob(txt)));
    } catch { 
        el.textContent = 'Erro de parsing.'; 
    }
}

/*
   8. FUNÇÕES AUXILIARES E GLOBAIS
 */
function confirmarDesligamento() {
    const alerta = document.getElementById('alertaSistema');
    if (alerta) {
        alerta.classList.add('mostrar');
    }
}

function toast(msg, tipo = '') {
    const el = document.getElementById('toast');
    if (!el) return;
    
    el.textContent = msg;
    el.className = 'mostrar' + (tipo ? ' ' + tipo : '');
    
    clearTimeout(el._t);
    el._t = setTimeout(() => {
        el.className = '';
    }, 3000);
}

function _clamp(v, mn, mx) { 
    return Math.min(mx, Math.max(mn, v)); 
}

function _zp(n) { 
    return String(n).padStart(2, '0'); 
}

function _escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function _escAttr(s) {
    return String(s)
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/*
   9. EASTER EGG (KONAMI CODE)
 */

const _KONAMI = [
    'ArrowUp', 'ArrowUp', 
    'ArrowDown', 'ArrowDown', 
    'ArrowLeft', 'ArrowRight', 
    'ArrowLeft', 'ArrowRight', 
    'b', 'a'
];

function _konami(e) {
    estado.konami.push(e.key);
    estado.konami = estado.konami.slice(-10);
    
    if (estado.konami.join(',') === _KONAMI.join(',')) {
        estado.konami = [];
        _candyMode();
    }
}

function _candyMode() {
    let hue = 0;
    const lp = setInterval(() => {
        document.documentElement.style.setProperty('--destaque', `hsl(${hue},100%,60%)`);
        document.documentElement.style.setProperty('--verde', `hsl(${(hue + 120) % 360},100%,55%)`);
        hue = (hue + 3) % 360;
    }, 50);
    
    toast('MODO CANDY ATIVADO! ↑↑↓↓←→←→BA');
    
    setTimeout(() => { 
        clearInterval(lp); 
        if (estado.tema) {
            _aplicarTema(estado.tema); 
        }
    }, 8000);
}

/*
   10. BOOT DA INTERFACE
 */
window.addEventListener('DOMContentLoaded', iniciarApp);