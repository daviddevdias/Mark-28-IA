'use strict';

function pgChat(wrap) {
    wrap.innerHTML = `
        <style>
            .msg { animation: msgEnter 0.32s var(--ease) both; }
            .chat-history { scroll-behavior: smooth; }
        </style>
        <div class="chat-wrap" style="height:calc(100vh - 500px);min-height:360px;">
            <div class="chat-history" id="chatHistory" style="height:100%;"></div>
            <div class="chat-input-row">
                <input class="input" id="chatIn"
                       placeholder="Fale com J.A.R.V.I.S..."
                       style="flex:1;font-size:14px;font-weight:700;">
                <button class="btn btn-accent" onclick="enviarChat()"
                        style="padding:10px 20px;font-size:12px;letter-spacing:2px;font-weight:700;">
                    ENVIAR
                </button>
            </div>
        </div>`;

    renderChat();

    const ci = document.getElementById('chatIn');
    if (ci) {
        ci.addEventListener('keydown', e => { if (e.key === 'Enter') enviarChat(); });
        ci.focus();
    }
}
window.pgChat = pgChat;

function enviarChat() {
    const ci  = document.getElementById('chatIn');
    const msg = ci?.value.trim();
    if (!msg) return;

    ci.value = '';
    state.chatHist.push({ role: 'user', text: msg });
    renderChat();
    showTyping();

    if (window.jarvis) {
        window.jarvis.executar_comando(msg);
    } else {
        const demo = ['Modo demonstração ativo.', 'Sistemas operacionais prontos.', 'Entendido, Chefe.'];
        setTimeout(() => {
            document.getElementById('typingIndicator')?.remove();
            state.chatHist.push({ role: 'jarvis', text: demo[state.chatHist.length % demo.length] });
            renderChat();
        }, 1000 + Math.random() * 500);
    }
}
window.enviarChat = enviarChat;

function receberMensagemJarvis(data) {
    document.getElementById('typingIndicator')?.remove();
    if (data.resposta) {
        state.chatHist.push({ role: 'jarvis', text: data.resposta });
        renderChat();
    }
    if (data.erro) {
        state.chatHist.push({ role: 'jarvis', text: 'ERRO: ' + data.erro });
        renderChat();
    }
}
window.receberMensagemJarvis = receberMensagemJarvis;

function showTyping() {
    const h = document.getElementById('chatHistory');
    if (!h) return;
    const d = document.createElement('div');
    d.id = 'typingIndicator';
    d.className = 'msg jarvis';
    d.innerHTML = `
        <div class="msg-role" style="font-weight:700;">J.A.R.V.I.S</div>
        <div class="msg-bubble" style="padding:10px 14px;">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>`;
    h.appendChild(d);
    h.scrollTop = h.scrollHeight;
}
window.showTyping = showTyping;

function renderChat() {
    const h = document.getElementById('chatHistory');
    if (!h) return;

    if (!state.chatHist.length) {
        h.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;
                 justify-content:center;max-height:500px;gap:14px;
                 color:var(--text3);font-family:var(--mono);
                 font-size:12px;letter-spacing:2px;text-align:center;">
                <div style="font-size:44px;filter:drop-shadow(0 0 16px var(--accent));
                     animation:floatIcon 4s ease-in-out infinite;">◈</div>
                <div style="font-family:var(--orb);font-size:14px;font-weight:700;opacity:.7;letter-spacing:4px;">LINK NEURAL ATIVO</div>
                <div style="font-size:14px;opacity:.4;font-weight:700;">Digite uma mensagem para iniciar</div>
            </div>`;
        return;
    }

    h.innerHTML = state.chatHist.map((m, idx) => `
        <div class="msg ${m.role}" style="margin-bottom:10px;animation-delay:${idx * .04}s">
            <div class="msg-role" style="font-weight:700;">${m.role === 'user' ? 'VOCÊ' : 'J.A.R.V.I.S'}</div>
            <div class="msg-bubble" style="padding:10px 14px;font-weight:700;">
                ${esc(m.text)}
            </div>
        </div>`).join('');

    h.scrollTop = h.scrollHeight;
}
window.renderChat = renderChat;