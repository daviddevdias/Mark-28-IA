'use strict';

let alarmClockInterval = null;







async function carregarAlarmesBridge() {
    if (!window.jarvis || typeof window.jarvis.obter_alarmes !== 'function') return;
    const raw = await bridge('obter_alarmes');
    if (raw) {
        try {
            const lista = JSON.parse(raw);
            if (Array.isArray(lista)) state.alarmes.lista = lista;
        } catch(e) {}
    }
}
window.carregarAlarmesBridge = carregarAlarmesBridge;







function iniciarVerificadorAlarmes() {
    if (window.alarmCheckerRunning) return;
    window.alarmCheckerRunning = true;
    setInterval(() => {
        const agora = new Date();
        const hhmm  = agora.toTimeString().slice(0,5);
        const hoje  = agora.toISOString().slice(0,10);
        const diaSem = (agora.getDay() + 6) % 7; 

        state.alarmes.lista.forEach(a => {
            if (a.status !== 'pendente') return;
            if (a.hora !== hhmm) return;
            
            if (a.data && a.data !== hoje) return;
            
            if (a.dias_semana && a.dias_semana.length && !a.dias_semana.includes(diaSem)) return;
            
            a.ultimo_disparo = new Date().toISOString();
            if (!a.repetir) a.status = 'concluido';
            mostrarNotificacaoAlarme(a);
            if (state.page === PG.ALARMES) renderPage();
        });
    }, 30000);
}
iniciarVerificadorAlarmes();







function pgAlarmes(wrap) {
    if (alarmClockInterval) { clearInterval(alarmClockInterval); alarmClockInterval = null; }

    const alarmes   = state.alarmes.lista || [];
    const pendentes = alarmes.filter(a => a.status === 'pendente');
    const concluidos= alarmes.filter(a => a.status === 'concluido');
    const filtro    = state.alarmes.filtro || 'todos';
    const visiveis  = filtro === 'pendentes' ? pendentes
                    : filtro === 'concluidos' ? concluidos : alarmes;

    wrap.innerHTML = `

    <div class="alm-shell">

      <div class="alm-header">
        <div>
          <div class="alm-title">⏰ CENTRAL DE ALARMES</div>
          <div class="alm-sub">Agendamento · Alertas · Soneca · Controle total</div>
        </div>
        <button class="alm-new-btn" onclick="abrirModalNovoAlarme()">＋ NOVO ALARME</button>
      </div>

      <div class="alm-stats">
        <div class="alm-stat" style="border-color:var(--accent2)33;">
          <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent2);"></div>
          <div class="alm-stat-lbl">⏰ ATIVOS</div>
          <div class="alm-stat-val" style="color:var(--accent2);">${pendentes.length}</div>
        </div>
        <div class="alm-stat" style="border-color:var(--accent)33;">
          <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent);"></div>
          <div class="alm-stat-lbl">◈ TOTAL</div>
          <div class="alm-stat-val" style="color:var(--accent);">${alarmes.length}</div>
        </div>
        <div class="alm-stat" style="border-color:var(--text3)33;">
          <div style="position:absolute;top:0;left:0;right:0;height:2px;background:var(--text3);"></div>
          <div class="alm-stat-lbl">✅ CONCLUÍDOS</div>
          <div class="alm-stat-val" style="color:var(--text3);">${concluidos.length}</div>
        </div>
      </div>

      <div class="alm-quick">
        <div class="alm-quick-title">NOVO ALARME RÁPIDO</div>
        <div class="alm-quick-row">
          <div class="alm-field">
            <div class="alm-label">HORA</div>
            <input class="alm-inp" type="time" id="alarmeHoraRapida">
          </div>
          <div class="alm-field" style="flex:1;min-width:160px;">
            <div class="alm-label">MISSÃO</div>
            <input class="alm-inp" type="text" id="alarmeMissaoRapida"
                   placeholder="Ex: Reunião, Medicação..." maxlength="120">
          </div>
          <div class="alm-field">
            <div class="alm-label">DATA (opcional)</div>
            <input class="alm-inp" type="date" id="alarmeDataRapida">
          </div>
          <button class="alm-create-btn" onclick="criarAlarmeRapido()">▶ CRIAR</button>
        </div>
        <div class="alm-days">
          <span class="alm-label">DIAS:</span>
          ${['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'].map((d,i) => `
            <label class="alm-day-lbl">
              <input type="checkbox" class="dia-check" data-idx="${i}"
                    style="accent-color:var(--accent);width:24px;height:24px;">
              ${d}
            </label>`).join('')}
          <label class="alm-rep-lbl">
            <input type="checkbox" id="alarmeRepetir"
                  style="accent-color:var(--accent2);width:20px;height:20px;">
            REPETIR
          </label>
        </div>
      </div>

      <div class="alm-list-wrap">
        <div class="alm-list-header">
          <div style="font-family:var(--mono);font-size:14px;font-weight:700;
               color:var(--text3);letter-spacing:3px;">LISTA DE ALARMES</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <div class="alm-filter-row">
              ${['todos','pendentes','concluidos'].map(f => `
                <button class="alm-filter-btn ${filtro===f?'active':''}"
                        onclick="filtrarAlarmes('${f}')">${f.toUpperCase()}</button>`).join('')}
            </div>
            <button class="alm-filter-btn" onclick="limparConcluidos()">🗑 LIMPAR CONCLUÍDOS</button>
          </div>
        </div>
        <div class="alm-list" id="alarmesList">
          ${renderAlarmItems(visiveis)}
        </div>
      </div>

      ${renderModalNovoAlarme()}
    </div>`;

    const inp = document.getElementById('alarmeHoraRapida');
    if (inp) inp.value = new Date().toTimeString().slice(0,5);

    document.getElementById('alarmeMissaoRapida')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') criarAlarmeRapido();
    });
}
window.pgAlarmes = pgAlarmes;







function renderAlarmItems(lista) {
    if (!lista || !lista.length) return `
        <div class="alm-empty">
            <div class="alm-empty-icon">⏰</div>
            <div>Nenhum alarme nesta categoria.</div>
            <div style="font-size:14px;opacity:.6; font-weight: 700;">Use o formulário acima para criar um alarme.</div>
        </div>`;

    return lista.map(a => {
        const ok  = a.status === 'pendente';
        const cor = ok ? 'var(--accent)' : 'var(--text3)';
        const bg  = ok ? 'var(--accent)08' : 'var(--surface,var(--bg))';
        const DIAS = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'];
        const diasStr = a.dias_semana && a.dias_semana.length
            ? a.dias_semana.map(d=>DIAS[d]).join(', ')
            : (a.data || 'Hoje');
        const metaParts = [diasStr];
        if (a.repetir) metaParts.push('REPETIR');
        if (!ok) metaParts.push('CONCLUÍDO');

        return `
        <div class="alm-item" style="border-color:${cor}33;background:${bg};border-left-color:${cor};">
            <div class="alm-time" style="color:${cor};">${esc(a.hora)}</div>
            <div class="alm-info">
                <div class="alm-mission">${esc(a.missao || 'Alarme')}</div>
                <div class="alm-meta">${esc(metaParts.join(' · '))}</div>
            </div>
            ${ok ? `
            <div class="alm-actions">
                <button class="alm-btn snooze"
                        onclick="snoozeAlarme('${esc(a.hora)}','${esc(a.missao||'')}')">
                    💤 SONECA
                </button>
                <button class="alm-btn danger"
                        onclick="removerAlarme('${esc(a.hora)}','${esc(a.missao||'')}','${esc(a.data||'')}')">
                    ✕
                </button>
            </div>` : ''}
        </div>`;
    }).join('');
}
window.renderAlarmesListHTML = renderAlarmItems;







function renderModalNovoAlarme() {
    return `
    <div class="modal-overlay" id="modalNovoAlarme" style="z-index: 99999;">
      <div class="modal-box warn" style="max-width:700px;max-height:auto;">
        <div class="modal-icon">⏰</div>
        <h3>NOVO ALARME</h3>
        <div style="display:flex;flex-direction:column;gap:14px;text-align:left;margin-top:18px;">
          <div>
            <div class="alm-label" style="display:block;margin-bottom:6px;">HORA *</div>
            <input class="alm-inp" type="time" id="modalAlarmeHora">
          </div>
          <div>
            <div class="alm-label" style="display:block;margin-bottom:6px;">MISSÃO</div>
            <input class="alm-inp" type="text" id="modalAlarmeMissao"
                  placeholder="Descrição do alarme" maxlength="120">
          </div>
          <div>
            <div class="alm-label" style="display:block;margin-bottom:6px;">DATA (opcional)</div>
            <input class="alm-inp" type="date" id="modalAlarmeData">
          </div>
          <div>
            <div class="alm-label" style="display:block;margin-bottom:12px;font-size:16px;font-weight:bold;color:var(--accent);">DIAS DA SEMANA</div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;">
              ${['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'].map((d,i) => `
                <label class="alm-day-lbl" style="font-size:14px;font-weight:700;padding:8px 12px;background:rgba(255,255,255,0.05);border-radius:8px;display:flex;align-items:center;gap:8px;cursor:pointer;">
                  <input type="checkbox" class="modal-dia-check" data-idx="${i}"
                        style="accent-color:var(--accent);width:24px;height:24px;cursor:pointer;">
                  ${d}
                </label>`).join('')}
            </div>
          </div>

          <label style="display:flex;align-items:center;gap:12px;cursor:pointer;
                  font-family:var(--mono);font-size:16px;font-weight:bold;color:var(--text);margin-bottom:24px;padding:12px;background:rgba(255,255,255,0.05);border-radius:8px;">
            <input type="checkbox" id="modalAlarmeRepetir"
                  style="accent-color:var(--accent);width:24px;height:24px;cursor:pointer;">
            REPETIR
          </label>

          </div>
          <div class="modal-btns" style="display:flex;gap:16px;margin-top:10px;">
            <button class="btn btn-accent" onclick="confirmarNovoAlarme()" style="padding:14px 28px;font-size:14px;">CRIAR ALARME</button>
            <button class="btn btn-ghost"  onclick="fecharModal('modalNovoAlarme')" style="padding:14px 28px;font-size:14px;">CANCELAR</button>
          </div>
      </div>
    </div>`;
}
window.renderModalNovoAlarme = renderModalNovoAlarme;







function abrirModalNovoAlarme() {
    const ov = document.getElementById('modalNovoAlarme');
    if (!ov) { renderPage(); return; }
    const inp = document.getElementById('modalAlarmeHora');
    if (inp) inp.value = new Date().toTimeString().slice(0,5);
    ov.classList.add('open');
}
window.abrirModalNovoAlarme = abrirModalNovoAlarme;







function confirmarNovoAlarme() {
    const hora    = document.getElementById('modalAlarmeHora')?.value    || '';
    const missao  = document.getElementById('modalAlarmeMissao')?.value.trim() || 'Alarme';
    const data    = document.getElementById('modalAlarmeData')?.value    || '';
    const rep     = document.getElementById('modalAlarmeRepetir')?.checked || false;
    const dias    = [...document.querySelectorAll('.modal-dia-check:checked')]
                      .map(el => parseInt(el.dataset.idx));
    if (!hora) { toast('Hora obrigatória.', 'err'); return; }
    salvarAlarme({ hora, missao, data: data||null, repetir: rep, dias_semana: dias.length?dias:null });
    fecharModal('modalNovoAlarme');
}
window.confirmarNovoAlarme = confirmarNovoAlarme;







function criarAlarmeRapido() {
    const hora    = document.getElementById('alarmeHoraRapida')?.value    || '';
    const missao  = document.getElementById('alarmeMissaoRapida')?.value.trim() || 'Alarme';
    const data    = document.getElementById('alarmeDataRapida')?.value    || '';
    const rep     = document.getElementById('alarmeRepetir')?.checked    || false;
    const dias    = [...document.querySelectorAll('.dia-check:checked')]
                      .map(el => parseInt(el.dataset.idx));
    if (!hora) { toast('Informe a hora.', 'err'); return; }
    salvarAlarme({ hora, missao, data: data||null, repetir: rep, dias_semana: dias.length?dias:null });
    const m = document.getElementById('alarmeMissaoRapida');
    if (m) m.value = '';
    const d = document.getElementById('alarmeDataRapida');
    if (d) d.value = '';
    document.querySelectorAll('.dia-check').forEach(c => c.checked=false);
    const r = document.getElementById('alarmeRepetir');
    if (r) r.checked = false;
}
window.criarAlarmeRapido = criarAlarmeRapido;







function salvarAlarme({ hora, missao, data, repetir, dias_semana }) {
    const alarme = {
        hora, missao,
        status: 'pendente',
        repetir: repetir || !!(dias_semana && dias_semana.length),
        criado_em: new Date().toISOString(),
        ultimo_disparo: null,
        data: data || null,
        dias_semana: dias_semana && dias_semana.length ? dias_semana : null,
    };
    state.alarmes.lista.push(alarme);
    if (window.jarvis?.salvar_alarme) {
        try { window.jarvis.salvar_alarme(JSON.stringify(alarme)); } catch(e) {}
    }
    toast(`⏰ Alarme das ${hora} criado.`);
    addLog('info', `Alarme criado: ${hora} — ${missao}`);
    if (state.page === PG.ALARMES) renderPage();
}
window.salvarAlarme = salvarAlarme;







function removerAlarme(hora, missao, data) {
    state.alarmes.lista = state.alarmes.lista.filter(a =>
        !(a.hora === hora && a.missao === missao && (a.data||'') === (data||''))
    );
    if (window.jarvis?.remover_alarme) {
        try { window.jarvis.remover_alarme(JSON.stringify({hora,missao,data:data||null})); } catch(e) {}
    }
    toast(`Alarme das ${hora} removido.`, 'warn');
    if (state.page === PG.ALARMES) renderPage();
}
window.removerAlarme = removerAlarme;







function snoozeAlarme(hora, missao) {
    const nova = new Date(Date.now() + 10*60000);
    const h = nova.toTimeString().slice(0,5);
    const d = nova.toISOString().slice(0,10);
    salvarAlarme({ hora:h, missao:'💤 '+missao, data:d, repetir:false, dias_semana:null });
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
    if (window.jarvis?.limpar_alarmes_concluidos) {
        try { window.jarvis.limpar_alarmes_concluidos(); } catch(e) {}
    }
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
            background:linear-gradient(135deg,var(--surface,var(--bg)),var(--card));
            border-bottom:3px solid var(--accent);
            padding:18px 32px;display:flex;align-items:center;gap:20px;
            box-shadow:0 4px 40px rgba(255,180,0,.25);
            animation:alertSlideIn .3s ease;
        `;
        document.body.appendChild(notif);
    }
    notif.innerHTML = `
        <div style="font-size:32px;animation:floatIcon 1.5s ease-in-out infinite;">⏰</div>
        <div style="flex:1;">
            <div style="font-family:var(--mono);font-size:10px;font-weight:700;
                 color:var(--accent);letter-spacing:3px;margin-bottom:4px;">
                ALARME DISPARADO · ${esc(alarme.hora||'')}
            </div>
            <div style="font-size:16px;color:var(--text);font-weight:700;">
                ${esc(alarme.missao||'Alarme')}
            </div>
        </div>
        <div style="display:flex;gap:8px;">
            <button onclick="snoozeAlarme('${esc(alarme.hora)}','${esc(alarme.missao||'')}');fecharNotifAlarme();"
                    style="background:var(--yellow);color:#000;border:none;border-radius:8px;
                           padding:9px 16px;font-family:var(--mono);font-size:11px;
                           font-weight:700;cursor:pointer;">
                💤 SONECA 10min
            </button>
            <button onclick="pararAlarme();fecharNotifAlarme();"
                    style="background:transparent;border:1px solid var(--border);border-radius:8px;
                           padding:9px 16px;font-family:var(--mono);font-size:11px;
                           font-weight:700;cursor:pointer;color:var(--text2);">
                ⏹ PARAR
            </button>
        </div>
    `;
}
window.mostrarNotificacaoAlarme = mostrarNotificacaoAlarme;







function fecharNotifAlarme() { document.getElementById('alarmeNotif')?.remove(); }
window.fecharNotifAlarme = fecharNotifAlarme;







function pararAlarme() {
    state.alarmes.alarmeAtivo = false;
    if (window.jarvis?.parar_alarme) { try { window.jarvis.parar_alarme(); } catch(e) {} }
    fecharNotifAlarme();
    toast('Alarme parado.');
}
window.pararAlarme = pararAlarme;