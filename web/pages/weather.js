'use strict';

function wxIcon(desc) {
    if (!desc) return '🌡️';
    const d = desc.toLowerCase();
    for (const [k, v] of Object.entries(WX_ICONS)) {
        if (d.includes(k.toLowerCase())) return v;
    }
    return WX_ICONS.default;
}
window.wxIcon = wxIcon;

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
        fetchWeather(state.weather.city);
    } else {
        renderWeather(wxWrap);
    }
}
window.pgWeather = pgWeather;

async function buscarClima() {
    const input = document.getElementById('wxCity');
    const city  = (input?.value || '').trim();
    if (!city) return;
    state.weather.city    = city;
    state.weather.loading = true;
    state.weather.error   = null;
    if (window.jarvis) window.jarvis.salvar_configuracao('cidade_padrao', city);
    fetchWeather(city);
}
window.buscarClima = buscarClima;

async function atualizarClima() {
    state.weather.loading = true;
    state.weather.error   = null;
    fetchWeather(state.weather.city);
}
window.atualizarClima = atualizarClima;

async function fetchWeather(city) {
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
window.fetchWeather = fetchWeather;

function parseWeatherData(data, city) {
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
        renderWeather(wxWrap);
    } catch(e) {
        state.weather.loading = false;
        state.weather.error   = 'Falha na decodificação';
        renderWeatherError();
    }
}
window.parseWeatherData = parseWeatherData;

function renderWeatherError() {
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
window.renderWeatherError = renderWeatherError;

function renderWeather(wxWrap) {
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
    const tCol = wx.temp > 35 ? 'var(--red)' : wx.temp > 28 ? 'var(--orange)' : wx.temp > 18 ? 'var(--accent)' : 'var(--purple)';
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
                ${wxStat('💧','UMIDADE',      wx.humidity + '%',   '',             'var(--accent)')}
                ${wxStat('💨','VENTO',        wx.wind + ' km/h',   '',             'var(--accent2)')}
                ${wxStat('🌡️','PRESSÃO',     wx.pressure + ' hPa','',            'var(--yellow)')}
                ${wxStat('☀️','ÍNDICE UV',   String(wx.uv),        uvLabel(wx.uv),uvColor(wx.uv))}
                ${wxStat('👁️','VISIBILIDADE',wx.vis + ' km',      '',             'var(--purple)')}
                ${wxStat('🌡️','SENSAÇÃO',    wx.feels + '°C',      '',             tCol)}
            </div>
        </div>
        <div class="weather-forecast" style="animation:pageEnter .35s var(--ease) .15s both;">
            <div class="forecast-label">PREVISÃO — PRÓXIMOS 6 DIAS</div>
            <div class="forecast-row">
                ${forecastHTML || '<div style="color:var(--text3);font-family:var(--mono);font-size:13px;">Sem dados de previsão.</div>'}
            </div>
        </div>
        <div style="display:flex;gap:12px;animation:pageEnter .35s var(--ease) .2s both;">
            ${wxAlerts(wx)}
        </div>
    `;
}
window.renderWeather = renderWeather;

function wxStat(icon, label, val, sub, col) {
    return `
        <div class="weather-stat">
            <div class="stat-label">${icon} ${label}</div>
            <div class="stat-val" style="color:${col};">${val}</div>
            ${sub ? `<div class="stat-sub">${sub}</div>` : ''}
        </div>`;
}

function uvLabel(uv) {
    if (uv <= 2) return 'BAIXO';
    if (uv <= 5) return 'MODERADO';
    if (uv <= 7) return 'ALTO';
    return 'EXTREMO';
}

function uvColor(uv) {
    if (uv <= 2) return 'var(--accent2)';
    if (uv <= 5) return 'var(--yellow)';
    return 'var(--red)';
}

function wxAlerts(wx) {
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