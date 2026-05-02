'use strict';

function boot() {
    buildNav();
    setupNavScrollArrows();
    startClock();
    startMetricSimulation();
    startBgCanvas();
    injetarCSS();
    navegarPara(0);
    document.addEventListener('keydown', konamiHandler);
    addLog('ok',   'J.A.R.V.I.S MARK XXVIII inicializado');
    addLog('info', 'Aguardando bridge Qt...');
}

function renderPage() {
    const area = document.getElementById('content');
    if (!area) return;
    area.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'pg-enter';
    area.appendChild(wrap);

    const fns = [
        pgWeather,
        pgDash,
        pgAlarmes,
        pgComandos,
        pgVoz,
        pgVisao,
        pgMonitor,
        pgChat,
        pgNotas,
        pgIA,
        pgConfig,
        pgTemas,
    ];

    const fn = fns[state.page];
    if (typeof fn === 'function') {
        fn(wrap);
    } else {
        wrap.innerHTML = `<div style="padding:60px;text-align:center;color:var(--text3);
            font-family:var(--mono);font-size:15px;letter-spacing:3px;">
            Página não implementada.</div>`;
    }
}

function enviarComando(cmd) {
    if (!window.jarvis) { toast('Bridge não conectada.', 'err'); return; }
    window.jarvis.executar_comando(cmd);
    addLog('info', '▶ ' + cmd);
    toast('▶ ' + cmd.toUpperCase().slice(0, 60));
}

function startClock() {
    const el   = document.getElementById('clock');
    const tick = () => { if (el) el.textContent = new Date().toTimeString().slice(0, 8); };
    tick();
    setInterval(tick, 1000);
}

function startMetricSimulation() {
    const blend = 0.18;
    const tick = () => {
        const m = state.metricas;
        m._cpu_raw = clamp(m._cpu_raw + (Math.random() - .46) * 8,   2,  96);
        m._ram_raw = clamp(m._ram_raw + (Math.random() - .49) * 2.5, 18, 92);
        m._gpu_raw = clamp(m._gpu_raw + (Math.random() - .46) * 10,  0,  90);

        m.cpu = +(m.cpu * (1 - blend) + m._cpu_raw * blend).toFixed(1);
        m.ram = +(m.ram * (1 - blend) + m._ram_raw * blend).toFixed(1);
        m.gpu = +(m.gpu * (1 - blend) + m._gpu_raw * blend).toFixed(1);

        m.net_in   = +(Math.random() * 2.4).toFixed(2);
        m.net_out  = +(Math.random() * 0.7).toFixed(2);
        m.ping     = Math.floor(16 + Math.random() * 55);
        m.freq     = Math.floor(2000 + Math.random() * 1600);
        m.gpu_temp = Math.floor(36 + m.gpu * 0.42);
        m.ram_usada = +((m.ram / 100) * m.ram_total).toFixed(1);

        if (state.page === PG.DASH) updateMetrics();
    };
    tick();
    setInterval(tick, 1400);
}

function startBgCanvas() {
    const canvas = document.getElementById('bgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resize = () => {
        canvas.width  = window.innerWidth;
        canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize, { passive: true });

    const PARTICLE_COUNT = 60;
    const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        vx: (Math.random() - .5) * .3,
        vy: (Math.random() - .5) * .3,
        r: Math.random() * 1.8 + .4,
        alpha: Math.random() * .5 + .1,
        pulse: Math.random() * Math.PI * 2,
    }));

    const HEX_GRID = [];
    const HEX_SIZE = 55;
    const buildHex = () => {
        HEX_GRID.length = 0;
        const W = window.innerWidth, H = window.innerHeight;
        const dx = HEX_SIZE * 1.75, dy = HEX_SIZE * Math.sqrt(3);
        for (let row = -1; row < H / dy + 2; row++) {
            for (let col = -1; col < W / dx + 2; col++) {
                const ox = col % 2 === 0 ? 0 : dy / 2;
                HEX_GRID.push({ x: col * dx, y: row * dy + ox });
            }
        }
    };
    buildHex();
    window.addEventListener('resize', buildHex, { passive: true });

    let frame = 0;
    const draw = () => {
        const W = canvas.width, H = canvas.height;
        ctx.clearRect(0, 0, W, H);
        frame++;

        ctx.strokeStyle = 'rgba(255,180,0,0.028)';
        ctx.lineWidth = .7;
        HEX_GRID.forEach(({ x, y }) => {
            ctx.beginPath();
            for (let i = 0; i < 6; i++) {
                const a = (Math.PI / 3) * i - Math.PI / 6;
                const px = x + HEX_SIZE * Math.cos(a);
                const py = y + HEX_SIZE * Math.sin(a);
                i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.stroke();
        });

        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.pulse += .018;
            if (p.x < -2) p.x = W + 2;
            if (p.x > W + 2) p.x = -2;
            if (p.y < -2) p.y = H + 2;
            if (p.y > H + 2) p.y = -2;

            const alpha = p.alpha * (0.6 + 0.4 * Math.sin(p.pulse));
            const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
            grad.addColorStop(0, `rgba(255,180,0,${alpha})`);
            grad.addColorStop(1, 'rgba(255,180,0,0)');
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r * 4, 0, Math.PI * 2);
            ctx.fill();
        });

        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 140) {
                    const alpha = (1 - dist / 140) * 0.07;
                    ctx.strokeStyle = `rgba(255,180,0,${alpha})`;
                    ctx.lineWidth = .5;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(draw);
    };
    draw();
}

function clamp(v, mn, mx) { return Math.min(mx, Math.max(mn, v)); }
function zp(n)             { return String(n).padStart(2, '0'); }

const sequenciaKonami = [
    'ArrowUp','ArrowUp','ArrowDown','ArrowDown',
    'ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'
];

function konamiHandler(e) {
    state.konami.push(e.key);
    state.konami = state.konami.slice(-10);
    if (state.konami.join(',') !== sequenciaKonami.join(',')) return;
    state.konami = [];

    let hue = 0;
    const lp = setInterval(() => {
        document.documentElement.style.setProperty('--accent',  `hsl(${hue},100%,60%)`);
        document.documentElement.style.setProperty('--accent2', `hsl(${(hue + 120) % 360},100%,60%)`);
        hue = (hue + 4) % 360;
    }, 50);
    toast('✦ MODO ARCO-ÍRIS ATIVADO ↑↑↓↓←→←→BA');
    setTimeout(() => {
        clearInterval(lp);
        if (state.theme) applyTheme(state.theme);
    }, 8000);
}

window.addEventListener('DOMContentLoaded', boot);