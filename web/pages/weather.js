'use strict';

function wxIcon(desc) {
    if (!desc) return '🌡️';
    const d = desc.toLowerCase();
    const map = [
        ['thunder', '⛈️'], ['storm', '⛈️'], ['blizzard', '🌨️'], ['snow', '❄️'],
        ['sleet', '🌨️'], ['fog', '🌫️'], ['mist', '🌫️'], ['haze', '🌫️'],
        ['drizzle', '🌦️'], ['rain', '🌧️'], ['overcast', '☁️'],
        ['partly', '⛅'], ['cloud', '⛅'], ['clear', '☀️'], ['sunny', '☀️'],
        ['tornado', '🌪️'], ['wind', '💨'],
    ];
    for (const [k, v] of map) if (d.includes(k)) return v;
    return '🌡️';
}
window.wxIcon = wxIcon;

function wxConditionKey(desc) {
    if (!desc) return 'clear';
    const d = desc.toLowerCase();
    if (d.includes('thunder') || d.includes('storm')) return 'storm';
    if (d.includes('snow') || d.includes('blizzard') || d.includes('sleet')) return 'snow';
    if (d.includes('rain') || d.includes('drizzle')) return 'rain';
    if (d.includes('fog') || d.includes('mist') || d.includes('haze')) return 'fog';
    if (d.includes('cloud') || d.includes('overcast')) return 'cloudy';
    return 'clear';
}

function normalizeWeather(raw, cityFallback) {
    if (!raw || raw.error) return null;
    if (raw.current_condition && raw.current_condition[0]) {
        const cur = raw.current_condition[0];
        const area = (raw.nearest_area && raw.nearest_area[0]) || {};
        const cn = area.areaName?.[0]?.value || cityFallback || '';
        const co = area.country?.[0]?.value || '';
        const rawDesc = cur.weatherDesc?.[0]?.value || '';
        const ptDesc = cur.lang_pt?.[0]?.value || rawDesc;
        const forecast = (raw.weather || []).slice(0, 6).map(d => {
            const h = d.hourly && d.hourly[4];
            const fd = h?.weatherDesc?.[0]?.value || '';
            const fp = h?.lang_pt?.[0]?.value || fd;
            return {
                date: d.date || '',
                hi: parseInt(d.maxtempC) || 0,
                lo: parseInt(d.mintempC) || 0,
                desc: fp || fd,
                rain: parseFloat(h?.precipMM || 0),
                chanceRain: parseInt(h?.chanceofrain || 0),
            };
        });
        return {
            city: cn, country: co,
            temp: parseInt(cur.temp_C) || 0,
            feels: parseInt(cur.FeelsLikeC) || 0,
            desc: ptDesc || rawDesc,
            icon: wxIcon(rawDesc),
            condition: wxConditionKey(rawDesc),
            humidity: parseInt(cur.humidity) || 0,
            wind: parseInt(cur.windspeedKmph) || 0,
            windDir: cur.winddir16Point || '',
            uv: parseInt(cur.uvIndex) || 0,
            pressure: parseInt(cur.pressure) || 0,
            vis: parseInt(cur.visibility) || 0,
            cloud: parseInt(cur.cloudcover) || 0,
            forecast, source: 'wttr',
        };
    }
    if (raw.main?.temp !== undefined) {
        const desc = raw.weather?.[0]?.description || 'N/A';
        return {
            city: raw.name || cityFallback || '',
            country: raw.sys?.country || '',
            temp: Math.round(raw.main.temp),
            feels: Math.round(raw.main.feels_like || raw.main.temp),
            desc,
            icon: wxIcon(desc),
            condition: wxConditionKey(desc),
            humidity: raw.main.humidity || 0,
            wind: Math.round((raw.wind?.speed || 0) * 3.6),
            windDir: degToCard(raw.wind?.deg),
            uv: 0,
            pressure: raw.main.pressure || 0,
            vis: Math.round((raw.visibility || 0) / 1000),
            cloud: raw.clouds?.all || 0,
            forecast: [], source: 'owm',
        };
    }
    return null;
}

function degToCard(deg) {
    if (deg == null) return '';
    return ['N', 'NE', 'L', 'SE', 'S', 'SO', 'O', 'NO'][Math.round(deg / 45) % 8];
}

function pgWeather(wrap) {
    const currentCity = state.apis.cidade_padrao || state.weather.city || 'São Paulo';
    state.weather.city = currentCity;

    wrap.innerHTML = `

    <div class="wx-root">
        <div class="wx-topbar">
            <div class="wx-search-wrap">
                <input class="wx-input" id="wxCity" placeholder="Buscar cidade..." value="${esc(currentCity)}" autocomplete="off">
            </div>
            <button class="wx-btn" onclick="buscarClima()">BUSCAR</button>
            <button class="wx-btn-ghost" onclick="atualizarClima()">↺ ATUALIZAR</button>
            <div id="wxSourceBadge"></div>
        </div>
        <div id="wxMain" style="flex:1;min-height:0;display:flex;flex-direction:column;gap:16px;"></div>
    </div>`;

    document.getElementById('wxCity')?.addEventListener('keydown', e => { if (e.key === 'Enter') buscarClima(); });

    if (state.weather.norm) renderWeatherFull(state.weather.norm);
    else fetchWeather(currentCity);
}
window.pgWeather = pgWeather;

function buscarClima() {
    const city = (document.getElementById('wxCity')?.value || '').trim();
    if (!city) return;
    state.weather.city = city;
    state.weather.norm = null;
    state.weather.error = null;
    if (window.jarvis) window.jarvis.salvar_configuracao('cidade_padrao', city);
    fetchWeather(city);
}
window.buscarClima = buscarClima;

function atualizarClima() {
    state.weather.norm = null;
    state.weather.error = null;
    fetchWeather(state.apis.cidade_padrao || state.weather.city || 'São Paulo');
}
window.atualizarClima = atualizarClima;

async function fetchWeather(city) {
    const el = document.getElementById('wxMain');
    if (el) el.innerHTML = `
        <div class="wx-loading">
            <div class="wx-loading-rings">
                <div class="wx-ring"></div>
                <div class="wx-ring"></div>
                <div class="wx-ring"></div>
            </div>
            <div class="wx-loading-txt">CONSULTANDO SATÉLITE METEOROLÓGICO</div>
        </div>`;

    if (window.jarvis) {
        window.jarvis.solicitar_clima(city);
        return;
    }

    try {
        const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1&lang=pt`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        parseWeatherData(data, city);
    } catch (e) {
        if (el) el.innerHTML = `
            <div class="wx-loading" style="gap:18px;">
                <div style="font-size:56px">🌐</div>
                <div style="font-family:var(--mono);color:var(--red);font-size:13px;letter-spacing:3px;">BRIDGE QT AUSENTE</div>
                <div style="font-family:var(--mono);color:rgba(255,255,255,.3);font-size:11px;letter-spacing:1px;">Erro: ${esc(e.message)}</div>
            </div>`;
    }
}
window.fetchWeather = fetchWeather;

function parseWeatherData(raw, city) {
    try {
        const currentCity = state.apis.cidade_padrao || state.weather.city || 'São Paulo';
        const norm = normalizeWeather(raw, city || currentCity);
        if (!norm) { state.weather.error = raw?.error || 'Dados inválidos.'; renderWeatherError(); return; }
        state.weather.norm = norm;
        state.weather.city = norm.city || currentCity;
        state.weather.error = null;
        const inp = document.getElementById('wxCity');
        if (inp && norm.city) inp.value = norm.city;
        renderWeatherFull(norm);
    } catch (e) {
        state.weather.error = 'Erro: ' + e.message;
        renderWeatherError();
    }
}
window.parseWeatherData = parseWeatherData;

function renderWeatherError() {
    const el = document.getElementById('wxMain');
    if (!el) return;
    el.innerHTML = `
        <div class="wx-loading">
            <div style="font-size:60px">🌐</div>
            <div style="font-family:var(--orb);font-size:14px;color:var(--red);letter-spacing:3px;">
                ${esc(state.weather.error || 'Erro desconhecido')}
            </div>
            <button class="wx-btn" onclick="atualizarClima()">↺ TENTAR NOVAMENTE</button>
        </div>`;
}
window.renderWeatherError = renderWeatherError;

function startWeatherCanvas(condition, temp) {
    const canvas = document.getElementById('wxBgCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width  = canvas.offsetWidth  || 800;
    canvas.height = canvas.offsetHeight || 300;

    const W = canvas.width, H = canvas.height;
    let particles = [];

    const buildParticles = () => {
        particles = [];
        if (condition === 'rain' || condition === 'storm') {
            for (let i = 0; i < 120; i++) {
                particles.push({ x: Math.random() * W, y: Math.random() * H, vx: -1.5, vy: 12 + Math.random() * 8, len: 14 + Math.random() * 10, alpha: .15 + Math.random() * .25 });
            }
        } else if (condition === 'snow') {
            for (let i = 0; i < 80; i++) {
                particles.push({ x: Math.random() * W, y: Math.random() * H, vx: Math.sin(i) * .5, vy: 1 + Math.random() * 1.5, r: 1.5 + Math.random() * 2.5, alpha: .2 + Math.random() * .4, t: Math.random() * Math.PI * 2 });
            }
        } else if (condition === 'clear') {
            for (let i = 0; i < 40; i++) {
                const angle = (Math.PI * 2 / 40) * i;
                particles.push({ angle, speed: .003 + Math.random() * .005, len: 60 + Math.random() * 80, alpha: .04 + Math.random() * .06 });
            }
        } else if (condition === 'cloudy' || condition === 'fog') {
            for (let i = 0; i < 6; i++) {
                particles.push({ x: Math.random() * W, y: 20 + Math.random() * (H * .6), vx: .15 + Math.random() * .2, r: 60 + Math.random() * 80, alpha: .05 + Math.random() * .06 });
            }
        }
    };

    buildParticles();

    const tCol = temp > 32 ? '#ff6600' : temp > 22 ? '#ffb400' : temp > 10 ? '#00c8ff' : '#88aaff';

    const bgGrads = {
        clear:  ['#0a0800', '#1a1000'],
        rain:   ['#060810', '#03060d'],
        storm:  ['#04050c', '#020305'],
        snow:   ['#080c14', '#050810'],
        cloudy: ['#070a10', '#040608'],
        fog:    ['#08090e', '#05060a'],
    };
    const [gc1, gc2] = bgGrads[condition] || bgGrads.clear;

    let frame = 0;
    const tick = () => {
        if (!document.getElementById('wxBgCanvas')) return;
        frame++;
        const grad = ctx.createLinearGradient(0, 0, W, H);
        grad.addColorStop(0, gc1);
        grad.addColorStop(1, gc2);
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, W, H);

        if (condition === 'rain' || condition === 'storm') {
            ctx.strokeStyle = 'rgba(180,220,255,.35)';
            ctx.lineWidth = .8;
            particles.forEach(p => {
                ctx.globalAlpha = p.alpha;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(p.x + p.vx * 1.5, p.y + p.len);
                ctx.stroke();
                p.x += p.vx;
                p.y += p.vy;
                if (p.y > H) { p.y = -p.len; p.x = Math.random() * W; }
            });
            ctx.globalAlpha = 1;
            if (condition === 'storm' && Math.random() < .003) {
                ctx.fillStyle = 'rgba(200,220,255,.06)';
                ctx.fillRect(0, 0, W, H);
            }
        } else if (condition === 'snow') {
            particles.forEach(p => {
                ctx.globalAlpha = p.alpha;
                ctx.fillStyle = '#fff';
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
                p.t += .02;
                p.x += Math.sin(p.t) * .5 + p.vx;
                p.y += p.vy;
                if (p.y > H) { p.y = -5; p.x = Math.random() * W; }
            });
            ctx.globalAlpha = 1;
        } else if (condition === 'clear') {
            const cx = W * .75, cy = H * .25;
            const sunRad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 120);
            sunRad.addColorStop(0, tCol + '28');
            sunRad.addColorStop(1, 'transparent');
            ctx.fillStyle = sunRad;
            ctx.fillRect(0, 0, W, H);
            particles.forEach(p => {
                p.angle += p.speed;
                ctx.globalAlpha = p.alpha * (.7 + .3 * Math.sin(frame * .02 + p.angle));
                ctx.strokeStyle = tCol;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(cx + Math.cos(p.angle) * 35, cy + Math.sin(p.angle) * 35);
                ctx.lineTo(cx + Math.cos(p.angle) * (35 + p.len), cy + Math.sin(p.angle) * (35 + p.len));
                ctx.stroke();
            });
            ctx.globalAlpha = 1;
        } else if (condition === 'cloudy' || condition === 'fog') {
            particles.forEach(p => {
                ctx.globalAlpha = p.alpha * (.8 + .2 * Math.sin(frame * .01 + p.x * .01));
                const cg = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r);
                cg.addColorStop(0, 'rgba(180,200,220,.7)');
                cg.addColorStop(1, 'transparent');
                ctx.fillStyle = cg;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
                p.x += p.vx;
                if (p.x - p.r > W) p.x = -p.r;
            });
            ctx.globalAlpha = 1;
        }

        requestAnimationFrame(tick);
    };
    tick();
}

function renderWeatherFull(wx) {
    const el = document.getElementById('wxMain');
    if (!el) return;

    const tCol = wx.temp > 35 ? 'var(--red)' : wx.temp > 28 ? 'var(--orange)' : wx.temp > 18 ? 'var(--accent)' : '#7eb8ff';
    const uvLbl = wx.uv <= 2 ? 'BAIXO' : wx.uv <= 5 ? 'MODERADO' : wx.uv <= 7 ? 'ALTO' : 'EXTREMO';
    const uvCol = wx.uv <= 2 ? 'var(--accent2)' : wx.uv <= 5 ? 'var(--yellow,#ffd700)' : 'var(--red)';
    const DOWS  = ['DOM','SEG','TER','QUA','QUI','SEX','SÁB'];
    const today = new Date();

    const forecastHTML = wx.forecast.length ? wx.forecast.map((d, i) => {
        const dt  = d.date ? new Date(d.date + 'T12:00:00') : new Date(today.getTime() + i * 86400000);
        const dow = i === 0 ? 'HOJE' : DOWS[dt.getDay()];
        return `
        <div class="wx-fc" style="animation:pageEnter .4s var(--ease) ${i * .07}s both;">
            <div class="wx-fc-dow">${dow}</div>
            <div class="wx-fc-icon">${wxIcon(d.desc)}</div>
            <div class="wx-fc-hi" style="color:${tCol};">${d.hi}°</div>
            <div class="wx-fc-lo">${d.lo}°</div>
            ${d.chanceRain >= 20 ? `<div class="wx-fc-rain">💧${d.chanceRain}%</div>` : ''}
        </div>`;
    }).join('') : `<div style="color:rgba(255,255,255,.2);font-family:var(--mono);font-size:12px;grid-column:1/-1;text-align:center;padding:24px;">Previsão indisponível.</div>`;

    const alerts = [];
    if (wx.temp > 35) alerts.push({ i: '🔥', m: 'Calor extremo — hidrate-se', c: 'var(--red)' });
    if (wx.temp < 5)  alerts.push({ i: '🥶', m: 'Temperatura muito baixa', c: '#7eb8ff' });
    if (wx.uv > 7)    alerts.push({ i: '☀️', m: 'UV alto — protetor solar FPS 50+', c: 'var(--orange)' });
    if (wx.wind > 60) alerts.push({ i: '💨', m: 'Vento forte — cuidado ao dirigir', c: 'var(--yellow)' });
    if (wx.humidity > 90) alerts.push({ i: '💧', m: 'Alta umidade — sensação amplificada', c: 'var(--accent)' });

    const alertsHTML = alerts.length
        ? alerts.map(a => `
            <div class="wx-chip" style="border-color:${a.c}44;background:${a.c}10;">
                <span class="wx-chip-icon">${a.i}</span>
                <span class="wx-chip-txt" style="color:${a.c};">${a.m}</span>
            </div>`).join('')
        : `<div class="wx-chip" style="border-color:var(--accent2)33;background:var(--accent2)0d;flex:1;">
            <span class="wx-chip-icon">✅</span>
            <span class="wx-chip-txt" style="color:var(--accent2);">Condições estáveis — sem alertas ativos</span>
           </div>`;

    const badge = document.getElementById('wxSourceBadge');
    if (badge) badge.innerHTML = `<div class="wx-source"><div class="wx-source-dot"></div>${wx.source === 'owm' ? 'OWM' : 'WTTR.IN'}</div>`;

    el.innerHTML = html`
    <div style="animation:pageEnter .35s var(--ease) both;display:flex;flex-direction:column;gap:16px;">

      <div class="wx-hero">
        <div class="wx-canvas-wrap">
            <canvas id="wxBgCanvas"></canvas>
        </div>
        <div class="wx-hero-left">
            <div class="wx-hero-overlay"></div>
            <div class="wx-hero-content">
                <div class="wx-city-label">${esc(wx.city)}${wx.country ? ' · ' + esc(wx.country) : ''}</div>
                <div class="wx-temp-display" style="color:${tCol};">${wx.temp}<sup>°C</sup></div>
                <div class="wx-desc">${esc(wx.desc)}</div>
                <div class="wx-feels">Sensação ${wx.feels}°C &nbsp;·&nbsp; ${wx.windDir} ${wx.wind} km/h</div>
            </div>
            <div class="wx-icon-mega">${wx.icon}</div>
        </div>
        <div class="wx-stats-panel">
            <div class="wx-stat">
                <div class="wx-stat-lbl">💧 UMIDADE</div>
                <div class="wx-stat-val" style="color:var(--accent);">${wx.humidity}<span>%</span></div>
            </div>
            <div class="wx-stat">
                <div class="wx-stat-lbl">💨 VENTO</div>
                <div class="wx-stat-val" style="color:var(--accent2);">${wx.wind}<span> km/h</span></div>
                ${wx.windDir ? `<div class="wx-stat-sub">${wx.windDir}</div>` : ''}
            </div>
            <div class="wx-stat">
                <div class="wx-stat-lbl">🌡️ PRESSÃO</div>
                <div class="wx-stat-val" style="color:var(--yellow);">${wx.pressure}<span> hPa</span></div>
            </div>
            <div class="wx-stat">
                <div class="wx-stat-lbl">☀️ ÍNDICE UV</div>
                <div class="wx-stat-val" style="color:${uvCol};">${wx.uv || '—'}</div>
                <div class="wx-stat-sub">${uvLbl}</div>
            </div>
            <div class="wx-stat">
                <div class="wx-stat-lbl">👁️ VISIBILIDADE</div>
                <div class="wx-stat-val" style="color:rgba(200,210,255,.8);">${wx.vis}<span> km</span></div>
            </div>
            <div class="wx-stat">
                <div class="wx-stat-lbl">☁️ NEBULOSIDADE</div>
                <div class="wx-stat-val" style="color:rgba(180,200,220,.7);">${wx.cloud}<span>%</span></div>
            </div>
        </div>
      </div>

      <div class="wx-section-label">PREVISÃO · PRÓXIMOS 6 DIAS</div>
      <div class="wx-forecast-grid">${forecastHTML}</div>

      <div class="wx-section-label">ALERTAS ATIVOS</div>
      <div class="wx-alerts">${alertsHTML}</div>

    </div>`;

    requestAnimationFrame(() => startWeatherCanvas(wx.condition || 'clear', wx.temp));
}
window.renderWeatherFull = renderWeatherFull;

function renderWeather() {
    if (state.weather.norm) renderWeatherFull(state.weather.norm);
}
window.renderWeather = renderWeather;