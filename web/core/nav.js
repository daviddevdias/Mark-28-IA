'use strict';







function setupNavScrollArrows() {
    const sc = document.getElementById('topnavScroll');
    const L = document.getElementById('navScrollLeft');
    const R = document.getElementById('navScrollRight');
    if (!sc || !L || !R) return;

    const step = () => Math.max(120, Math.floor(sc.clientWidth * 0.55));

    const sync = () => {
        const max = Math.max(0, sc.scrollWidth - sc.clientWidth - 1);
        const x = sc.scrollLeft;
        L.disabled = max <= 0 || x <= 1;
        R.disabled = max <= 0 || x >= max - 1;
    };

    const tapAnim = (btn) => {
        if (!btn || btn.disabled) return;
        btn.classList.remove('tap-anim');
        void btn.offsetWidth;
        btn.classList.add('tap-anim');
    };

    L.addEventListener('click', () => {
        tapAnim(L);
        sc.scrollBy({ left: -step(), behavior: 'smooth' });
    });
    R.addEventListener('click', () => {
        tapAnim(R);
        sc.scrollBy({ left: step(), behavior: 'smooth' });
    });
    sc.addEventListener('scroll', sync, { passive: true });
    window.addEventListener('resize', sync, { passive: true });
    if (typeof ResizeObserver !== 'undefined') {
        try {
            new ResizeObserver(sync).observe(sc);
        } catch (e) { }
    }
    queueMicrotask(sync);
    setTimeout(sync, 400);
}







function buildNav() {
    const nav = document.getElementById('navBtns');
    if (!nav) return;
    PAGES.forEach((p, i) => {
        const btn = document.createElement('button');
        btn.className = 'nav-btn' + (i === 0 ? ' active' : '');
        btn.id = `nb${i}`;
        btn.innerHTML = `<span class="nav-icon">${p.icon}</span>${p.label}`;
        btn.onclick = () => navegarPara(i);
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