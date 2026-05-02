'use strict';

// ─── Índices de página (devem ser idênticos à ordem de PAGES) ───────────────
const PG = {
    WEATHER:   0,
    DASH:      1,
    ALARMES:   2,
    COMANDOS:  3,
    VOZ:       4,
    VISAO:     5,
    MONITOR:   6,
    CHAT:      7,
    NOTAS:     8,
    IA:        9,
    CONFIG:    10,
    TEMAS:     11,
};
window.PG = PG;

// ─── Definição das páginas (ordem = índice PG acima) ────────────────────────
const PAGES = [
    { id: 'weather',   label: 'CLIMA',       icon: '◍'  },  // 0
    { id: 'dash',      label: 'DIAGNÓSTICO', icon: '⟡'  },  // 1
    { id: 'alarmes',   label: 'ALARMES',     icon: '⏰'  },  // 2
    { id: 'cmds',      label: 'COMANDOS',    icon: '⌬'  },  // 3
    { id: 'voz',       label: 'VOZ',         icon: '◉'  },  // 4
    { id: 'visao',     label: 'VISÃO IA',    icon: '◬'  },  // 5
    { id: 'monitor',   label: 'MONITOR',     icon: '⬡'  },  // 6
    { id: 'chat',      label: 'CHAT',        icon: '◇'  },  // 7
    { id: 'notas',     label: 'NOTAS',       icon: '⋮'  },  // 8
    { id: 'ia',        label: 'MODELO IA',   icon: '⟢'  },  // 9
    { id: 'config',    label: 'CONFIG',      icon: '⛭'  },  // 10
    { id: 'temas',     label: 'VISUAL',      icon: '◈'  },  // 11
];
window.PAGES = PAGES;

// ─── Ícones de clima ─────────────────────────────────────────────────────────
const WX_ICONS = {
    'Clear':'☀️','Sunny':'☀️','Clouds':'☁️','Overcast':'⛅',
    'Rain':'🌧️','Drizzle':'🌦️','Thunderstorm':'⛈️',
    'Snow':'❄️','Sleet':'🌨️','Mist':'🌫️','Fog':'🌫️',
    'Haze':'🌫️','Tornado':'🌪️','Partly cloudy':'⛅',
    'Blizzard':'🌨️','default':'🌡️',
};
window.WX_ICONS = WX_ICONS;

// ─── Cores por tipo de evento de monitor ─────────────────────────────────────
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
window.TIPO_COR = TIPO_COR;

// ─── Ícones por tipo de evento de monitor ────────────────────────────────────
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
window.TIPO_ICON = TIPO_ICON;

// ─── Estado global ───────────────────────────────────────────────────────────
const state = {
    page: 0,
    theme: '',
    themes: {},
    notas: '',
    apis: {
        gemini: '', qwen: '', smartthings: '', smartthings_tv_id: '',
        spotify_id: '', spotify_sec: '', nome_mestre: '', cidade_padrao: ''
    },
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

    alarmes: {
        lista: [],
        filtro: 'todos',
        alarmeAtivo: false,
    },

    konami: [],
    bridgeReady: false,

    voz: {
        speaking: false,
        vol: 0.1,
        deviceIndex: 0,
        microfones: [],
    },
    cmdLibrary: [],
    cmdFilter: '',
};
window.state = state;

// ─── Utilitários de estado ───────────────────────────────────────────────────
function resetMetrics() {
    const m = state.metricas;
    m.cpu = m.ram = m.gpu = m.disco = 0;
    m.net_in = m.net_out = m.ping = m.freq = 0;
    m.gpu_temp = m.ram_usada = 0;
    m._cpu_raw = m._ram_raw = m._gpu_raw = 0;
}
window.resetMetrics = resetMetrics;

function clearLogs() {
    state.logs = [];
    state.chatHist = [];
}
window.clearLogs = clearLogs;