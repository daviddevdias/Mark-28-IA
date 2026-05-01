'use strict';

const Bus = (() => {
    const listeners = {};
    return {
        on(ev, fn) {
            (listeners[ev] = listeners[ev] || []).push(fn);
        },
        off(ev, fn) {
            if (!listeners[ev]) return;
            listeners[ev] = listeners[ev].filter(f => f !== fn);
        },
        emit(ev, data) {
            (listeners[ev] || []).forEach(fn => { try { fn(data); } catch(e) { console.error('[BUS]', ev, e); } });
        },
    };
})();

window.Bus = Bus;