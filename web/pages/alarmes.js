'use strict';

async function carregarAlarmesBridge() {
    const raw = await bridge('obter_alarmes');
    if (raw) {
        try { state.alarmes.lista = JSON.parse(raw); } catch(e) { state.alarmes.lista = []; }
    }
}
window.carregarAlarmesBridge = carregarAlarmesBridge;

function pgAlarmes(wrap) {
    const alarmes = state.alarmes.lista || [];
    const pendentes = alarmes.filter(a => a.status === 'pendente');
    const concluidos = alarmes.filter(a => a.status === 'concluido');
    const filtro = state.alarmes.filtro || 'todos';

    const visiveis = filtro === 'pendentes' ? pendentes
                   : filtro === 'concluidos' ? concluidos
                   : alarmes;

    wrap.innerHTML = `
        <div class="page-header" style="margin-bottom:16px;">
            <div>
                <div class="page-title">⏰ CENTRAL DE ALARMES</div>
                <div class="page-sub">Agendamento · Alertas · Soneca · Controle total</div>
            </div>
            <button class="btn btn-accent" onclick="abrirModalNovoAlarme()">＋ NOVO ALARME</button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">
            ${alarmeStatCard('ATIVOS', pendentes.length, 'var(--accent2)', '⏰')}
            ${alarmeStatCard('CONCLUÍDOS', concluidos.length, 'var(--text3)', '✅')}
            ${alarmeStatCard('TOTAL', alarmes.length, 'var(--accent)', '◈')}
        </div>

        <div class="card" style="padding:20px;margin-bottom:14px;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--accent),transparent);"></div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:4px;margin-bottom:18px;">
                <span style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:3px;">NOVO ALARME RÁPIDO</span>
            </div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;">
                <div style="display:flex;flex-direction:column;gap:6px;">
                    <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;">HORA</label>
                    <input class="input" type="time" id="alarmeHoraRapida" style="width:140px;">
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-width:180px;">
                    <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;">MISSÃO</label>
                    <input class="input" type="text" id="alarmeMissaoRapida" placeholder="Ex: Reunião, Medicação..." maxlength="120">
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;">
                    <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;">DATA (opt.)</label>
                    <input class="input" type="date" id="alarmeDataRapida" style="width:160px;">
                </div>
                <button class="btn btn-accent" onclick="criarAlarmeRapido()" style="align-self:flex-end;">▶ CRIAR</button>
            </div>
            <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                <span style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;">DIAS SEMANAIS:</span>
                ${['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'].map((d,i) => `
                    <label style="cursor:pointer;display:flex;align-items:center;gap:4px;font-family:var(--mono);font-size:11px;color:var(--text2);">
                        <input type="checkbox" class="dia-check" data-idx="${i}" style="accent-color:var(--accent);">
                        ${d}
                    </label>`).join('')}
                <label style="cursor:pointer;display:flex;align-items:center;gap:4px;font-family:var(--mono);font-size:11px;color:var(--accent2);margin-left:8px;">
                    <input type="checkbox" id="alarmeRepetir"> REPETIR
                </label>
            </div>
        </div>

        <div class="card" style="padding:18px;flex:1;">
            <div class="card-accent" style="background:linear-gradient(90deg,var(--accent2),transparent);"></div>
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;margin-top:4px;">
                <div style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:3px;">
                    LISTA DE ALARMES
                </div>
                <div style="display:flex;gap:6px;">
                    ${['todos','pendentes','concluidos'].map(f => `
                        <button class="btn ${filtro === f ? 'btn-accent' : 'btn-ghost'}"
                                style="font-size:10px;padding:5px 12px;"
                                onclick="filtrarAlarmes('${f}')">
                            ${f.toUpperCase()}
                        </button>`).join('')}
                    <button class="btn btn-ghost" style="font-size:10px;padding:5px 12px;"
                            onclick="limparConcluidos()">🗑 LIMPAR CONCLUÍDOS</button>
                </div>
            </div>
            <div id="alarmesList" style="max-height:340px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;">
                ${renderAlarmesListHTML(visiveis)}
            </div>
        </div>

        ${renderModalNovoAlarme()}
    `;

    document.getElementById('alarmeHoraRapida').value = new Date().toTimeString().slice(0,5);
}

window.pgAlarmes = pgAlarmes;

function alarmeStatCard(label, val, cor, icon) {
    return `
        <div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:8px;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2.5px;">${icon} ${label}</div>
            <div style="font-family:var(--orb,var(--mono));font-size:26px;font-weight:700;color:${cor};">${val}</div>
        </div>`;
}

function renderAlarmesListHTML(alarmes) {
    if (!alarmes || !alarmes.length) {
        return `<div style="text-align:center;padding:40px;color:var(--text3);font-family:var(--mono);font-size:12px;letter-spacing:2px;">
            Nenhum alarme nesta categoria.
        </div>`;
    }
    return alarmes.map((a, i) => {
        const isPendente = a.status === 'pendente';
        const cor = isPendente ? 'var(--accent)' : 'var(--text3)';
        const diasLabel = a.dias_semana && a.dias_semana.length
            ? a.dias_semana.map(d => ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][d]).join(', ')
            : (a.data ? a.data : 'Hoje');
        return `
            <div style="padding:14px 16px;border-radius:10px;border:1px solid ${cor}33;
                        background:${cor}08;border-left:3px solid ${cor};
                        display:flex;align-items:center;gap:14px;">
                <div style="font-family:var(--orb,var(--mono));font-size:22px;font-weight:700;
                            color:${cor};min-width:72px;">${a.hora}</div>
                <div style="flex:1;">
                    <div style="font-size:14px;color:var(--text);font-weight:700;margin-bottom:3px;">
                        ${esc(a.missao || 'Alarme')}
                    </div>
                    <div style="font-family:var(--mono);font-size:10px;color:var(--text3);letter-spacing:1.5px;">
                        ${diasLabel}${a.repetir ? ' · REPETIR' : ''}${isPendente ? '' : ' · CONCLUÍDO'}
                    </div>
                </div>
                ${isPendente ? `
                <div style="display:flex;gap:6px;">
                    <button class="btn btn-ghost" style="font-size:11px;padding:5px 10px;"
                            onclick="snoozeAlarme('${esc(a.hora)}','${esc(a.missao || '')}')">
                        💤 SONECA
                    </button>
                    <button class="btn btn-danger" style="font-size:11px;padding:5px 10px;"
                            onclick="removerAlarme('${esc(a.hora)}','${esc(a.missao || '')}','${esc(a.data || '')}')">
                        ✕
                    </button>
                </div>` : ''}
            </div>`;
    }).join('');
}

function renderModalNovoAlarme() {
    return `
        <div class="modal-overlay" id="modalNovoAlarme">
            <div class="modal-box warn" style="max-width:500px;">
                <div class="modal-icon">⏰</div>
                <h3>NOVO ALARME</h3>
                <div style="display:flex;flex-direction:column;gap:12px;text-align:left;margin-top:16px;">
                    <div>
                        <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;display:block;margin-bottom:6px;">HORA *</label>
                        <input class="input" type="time" id="modalAlarmeHora">
                    </div>
                    <div>
                        <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;display:block;margin-bottom:6px;">MISSÃO</label>
                        <input class="input" type="text" id="modalAlarmeMissao" placeholder="Descrição do alarme" maxlength="120">
                    </div>
                    <div>
                        <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;display:block;margin-bottom:6px;">DATA (opcional)</label>
                        <input class="input" type="date" id="modalAlarmeData">
                    </div>
                    <div>
                        <label style="font-family:var(--mono);font-size:10px;font-weight:700;color:var(--text3);letter-spacing:2px;display:block;margin-bottom:8px;">DIAS DA SEMANA</label>
                        <div style="display:flex;gap:6px;flex-wrap:wrap;">
                            ${['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'].map((d,i) => `
                                <label style="cursor:pointer;display:flex;align-items:center;gap:4px;
                                              font-family:var(--mono);font-size:11px;color:var(--text2);
                                              padding:5px 10px;border:1px solid var(--border);border-radius:6px;">
                                    <input type="checkbox" class="modal-dia-check" data-idx="${i}" style="accent-color:var(--accent);">
                                    ${d}
                                </label>`).join('')}
                        </div>
                    </div>
                    <label style="cursor:pointer;display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;color:var(--text2);">
                        <input type="checkbox" id="modalAlarmeRepetir" style="accent-color:var(--accent);"> REPETIR ALARME
                    </label>
                </div>
                <div class="modal-btns">
                    <button class="btn btn-accent" onclick="confirmarNovoAlarme()">CRIAR ALARME</button>
                    <button class="btn btn-ghost" onclick="fecharModal('modalNovoAlarme')">CANCELAR</button>
                </div>
            </div>
        </div>`;
}

function abrirModalNovoAlarme() {
    const overlay = document.getElementById('modalNovoAlarme');
    if (!overlay) { renderPage(); return; }
    const now = new Date().toTimeString().slice(0,5);
    const inp = document.getElementById('modalAlarmeHora');
    if (inp) inp.value = now;
    overlay.classList.add('open');
}
window.abrirModalNovoAlarme = abrirModalNovoAlarme;

function confirmarNovoAlarme() {
    const hora    = document.getElementById('modalAlarmeHora')?.value || '';
    const missao  = document.getElementById('modalAlarmeMissao')?.value.trim() || 'Alarme';
    const data    = document.getElementById('modalAlarmeData')?.value || '';
    const repetir = document.getElementById('modalAlarmeRepetir')?.checked || false;
    const dias    = [...document.querySelectorAll('.modal-dia-check:checked')].map(el => parseInt(el.dataset.idx));

    if (!hora) { toast('Hora obrigatória.', 'err'); return; }

    salvarAlarme({ hora, missao, data: data || null, repetir, dias_semana: dias.length ? dias : null });
    fecharModal('modalNovoAlarme');
}
window.confirmarNovoAlarme = confirmarNovoAlarme;

function criarAlarmeRapido() {
    const hora    = document.getElementById('alarmeHoraRapida')?.value || '';
    const missao  = document.getElementById('alarmeMissaoRapida')?.value.trim() || 'Alarme';
    const data    = document.getElementById('alarmeDataRapida')?.value || '';
    const repetir = document.getElementById('alarmeRepetir')?.checked || false;
    const dias    = [...document.querySelectorAll('.dia-check:checked')].map(el => parseInt(el.dataset.idx));

    if (!hora) { toast('Informe a hora.', 'err'); return; }

    salvarAlarme({ hora, missao, data: data || null, repetir, dias_semana: dias.length ? dias : null });
}
window.criarAlarmeRapido = criarAlarmeRapido;

function salvarAlarme({ hora, missao, data, repetir, dias_semana }) {
    const alarme = {
        hora, missao,
        status: 'pendente',
        repetir: repetir || (dias_semana && dias_semana.length > 0),
        musica: '',
        criado_em: new Date().toISOString(),
        ultimo_disparo: null,
        data: data || null,
        dias_semana: dias_semana && dias_semana.length ? dias_semana : null,
    };

    state.alarmes.lista.push(alarme);

    if (window.jarvis?.salvar_alarme) {
        window.jarvis.salvar_alarme(JSON.stringify(alarme));
    } else {
        const cmd = `alarme ${hora} ${missao}${data ? ' ' + data : ''}`;
        addLog('info', `▶ ${cmd}`);
    }

    toast(`⏰ Alarme das ${hora} criado.`);
    if (state.page === PG.ALARMES) renderPage();
}

function removerAlarme(hora, missao, data) {
    state.alarmes.lista = state.alarmes.lista.filter(a =>
        !(a.hora === hora && a.missao === missao && (a.data || '') === data)
    );

    if (window.jarvis?.remover_alarme) {
        window.jarvis.remover_alarme(JSON.stringify({ hora, missao, data: data || null }));
    } else {
        addLog('warn', `Alarme ${hora} removido.`);
    }

    toast(`Alarme das ${hora} removido.`, 'warn');
    if (state.page === PG.ALARMES) renderPage();
}
window.removerAlarme = removerAlarme;

function snoozeAlarme(hora, missao) {
    const agora = new Date();
    const nova = new Date(agora.getTime() + 10 * 60000);
    const h = nova.toTimeString().slice(0,5);
    const d = nova.toISOString().slice(0,10);
    salvarAlarme({ hora: h, missao: 'Soneca — ' + missao, data: d, repetir: false, dias_semana: null });
    toast(`💤 Soneca em 10 min — ${h}`);
}
window.snoozeAlarme = snoozeAlarme;

function filtrarAlarmes(f) {
    state.alarmes.filtro = f;
    if (state.page === PG.ALARMES) renderPage();
}
window.filtrarAlarmes = filtrarAlarmes;

function limparConcluidos() {
    state.alarmes.lista = state.alarmes.lista.filter(a => a.status !== 'concluido');
    if (window.jarvis?.limpar_alarmes_concluidos) window.jarvis.limpar_alarmes_concluidos();
    toast('Alarmes concluídos removidos.');
    if (state.page === PG.ALARMES) renderPage();
}
window.limparConcluidos = limparConcluidos;

function mostrarNotificacaoAlarme(alarme) {
    let notif = document.getElementById('alarmeNotif');
    if (!notif) {
        notif = document.createElement('div');
        notif.id = 'alarmeNotif';
        notif.style.cssText = `
            position:fixed;top:0;left:0;right:0;z-index:10000;
            background:linear-gradient(135deg,var(--surface),var(--card));
            border-bottom:2px solid var(--accent);
            padding:20px 32px;display:flex;align-items:center;gap:20px;
            box-shadow:0 4px 40px rgba(255,180,0,.3);
            animation:alertSlideIn .3s var(--ease);
        `;
        document.body.appendChild(notif);
    }
    notif.innerHTML = `
        <div style="font-size:36px;animation:floatIcon 1.5s ease-in-out infinite;">⏰</div>
        <div style="flex:1;">
            <div style="font-family:var(--orb);font-size:14px;font-weight:700;color:var(--accent);letter-spacing:3px;margin-bottom:4px;">
                ALARME DISPARADO · ${alarme.hora || ''}
            </div>
            <div style="font-size:16px;color:var(--text);font-weight:700;">${esc(alarme.missao || 'Alarme')}</div>
        </div>
        <div style="display:flex;gap:10px;">
            <button class="btn btn-warn" onclick="snoozeAlarme('${esc(alarme.hora)}','${esc(alarme.missao || '')}');fecharNotifAlarme();">
                💤 SONECA 10min
            </button>
            <button class="btn btn-ghost" onclick="pararAlarme();fecharNotifAlarme();">
                ⏹ PARAR
            </button>
        </div>
    `;
}

function fecharNotifAlarme() {
    document.getElementById('alarmeNotif')?.remove();
}
window.fecharNotifAlarme = fecharNotifAlarme;

function pararAlarme() {
    state.alarmes.alarmeAtivo = false;
    if (window.jarvis?.parar_alarme) window.jarvis.parar_alarme();
    else enviarComando('parar alarme');
    fecharNotifAlarme();
    toast('Alarme parado.');
}
window.pararAlarme = pararAlarme;