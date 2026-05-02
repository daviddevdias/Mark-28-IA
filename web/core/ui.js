'use strict';

function injetarCSS() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes alertSlideIn {
            from { opacity:0; transform:translateY(18px) scale(.96); }
            to   { opacity:1; transform:translateY(0)    scale(1);   }
        }
        @keyframes pageEnter {
            from { opacity:0; transform:translateY(14px); }
            to   { opacity:1; transform:translateY(0); }
        }
    `;
    document.head.appendChild(style);
}

function addLog(tipo, msg) {
    const ts = new Date().toTimeString().slice(0, 8);
    state.logs.unshift({ tipo, msg: String(msg), ts });
    if (state.logs.length > 100) state.logs.pop();
    renderLog();
}

function renderLog() {
    const el = document.getElementById('logStream');
    if (!el) return;
    el.innerHTML = state.logs.slice(0, 30).map(e => `
        <div class="log-line">
            <span class="log-ts">${e.ts}</span>
            <span class="log-${e.tipo}">${esc(e.msg)}</span>
        </div>`).join('');
}

function updateIABadge() {
    const el = document.getElementById('iaBadge');
    if (!el) return;
    const { ia } = state;
    const col  = ia.modo === 'ollama' ? 'var(--accent)' : 'var(--yellow)';
    const dot  = ia.ollama
        ? `<span style="width:7px;height:7px;border-radius:50%;background:var(--accent2);
                 display:inline-block;box-shadow:0 0 6px var(--accent2);flex-shrink:0;"></span>`
        : '';
    const model = ia.modelo ? ia.modelo.slice(0, 14) : '—';
    el.innerHTML = `${dot}
        <span style="color:${col};font-family:var(--orb);font-size:11px;letter-spacing:1.5px;">${ia.modo.toUpperCase()}</span>
        <span style="color:var(--border3);">◈</span>
        <span style="color:var(--text2);font-size:11px;font-family:var(--mono);">${model}</span>`;
}

function toast(msg, type = '') {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = String(msg);
    el.className   = 'show' + (type ? ' ' + type : '');
    clearTimeout(el.timer);
    el.timer = setTimeout(() => { el.className = ''; }, 3400);
}

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
    ocultarPainelQt();
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