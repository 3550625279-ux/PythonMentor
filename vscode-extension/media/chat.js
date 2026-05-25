// @ts-nocheck
(function() {
    var vscode = acquireVsCodeApi();
    var messagesDiv = document.getElementById('messages');
    var msgInput = document.getElementById('msgInput');
    var sendBtn = document.getElementById('sendBtn');
    var clearBtn = document.getElementById('clearBtn');
    var endBtn = document.getElementById('endBtn');
    var statusText = document.getElementById('statusText');
    var currentBotDiv = null;
    var currentContentDiv = null;
    var rawText = '';

    vscode.postMessage({ command: 'webview_ready' });

    function doSend() {
        var text = msgInput.value.trim();
        if (!text) return;
        addMsg('user', text);
        msgInput.value = '';
        msgInput.style.height = 'auto';
        vscode.postMessage({ command: 'send', text: text });
        statusText.textContent = 'Thinking...';
        sendBtn.disabled = true;
        rawText = '';
        currentBotDiv = addMsg('bot', '');
        currentContentDiv = currentBotDiv.querySelector('.msg-content');
        currentContentDiv.innerHTML = '<span class="cursor"></span>';
    }

    function addMsg(role, content) {
        var div = document.createElement('div');
        div.className = 'msg ' + role;
        var c = document.createElement('div');
        c.className = 'msg-content';
        if (role === 'user') {
            c.textContent = content;
        } else if (content) {
            c.innerHTML = md(content);
        }
        div.appendChild(c);
        messagesDiv.appendChild(div);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        return div;
    }

    function md(text) {
        var h = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        h = h.replace(/```(\w*)\n([\s\S]*?)```/g, function(m, l, c) {
            return '<div class="code-block"><div class="code-header"><span>'+(l||'code')+'</span><button class="copy-btn">Copy</button></div><pre><code>'+c.trim()+'</code></pre></div>';
        });
        h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
        h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
        h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
        h = h.replace(/^(\s*)[-*] (.+)$/gm, '$1<li>$2</li>');
        h = h.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        h = h.replace(/\n\n/g, '</p><p>');
        h = '<p>'+h+'</p>';
        h = h.replace(/<p><\/p>/g, '');
        h = h.replace(/\n/g, '<br>');
        return h;
    }

    sendBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        doSend();
    });

    msgInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            e.stopPropagation();
            doSend();
        }
    });

    msgInput.addEventListener('input', function() {
        msgInput.style.height = 'auto';
        msgInput.style.height = Math.min(msgInput.scrollHeight, 100) + 'px';
    });

    clearBtn.addEventListener('click', function() {
        messagesDiv.innerHTML = '';
        currentBotDiv = null;
        currentContentDiv = null;
        rawText = '';
        statusText.textContent = 'Ready';
        vscode.postMessage({ command: 'clear' });
        addMsg('bot', 'Hello! I am PythonMentor. Ask any Python question and I will guide you to find the answer yourself.');
        msgInput.focus();
    });

    endBtn.addEventListener('click', function() {
        statusText.textContent = 'Ending session...';
        endBtn.disabled = true;
        vscode.postMessage({ command: 'endSession' });
    });

    messagesDiv.addEventListener('click', function(e) {
        if (e.target.classList.contains('copy-btn')) {
            var code = e.target.closest('.code-block').querySelector('code').textContent;
            navigator.clipboard.writeText(code).then(function() {
                e.target.textContent = 'Copied!';
                setTimeout(function() { e.target.textContent = 'Copy'; }, 2000);
            });
        }
    });

    window.addEventListener('message', function(event) {
        var msg = event.data;
        if (msg.command === 'token') {
            if (currentContentDiv) {
                rawText += msg.text;
                currentContentDiv.innerHTML = md(rawText) + '<span class="cursor"></span>';
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        } else if (msg.command === 'done') {
            if (currentContentDiv) {
                currentContentDiv.innerHTML = md(rawText);
            }
            statusText.textContent = 'Ready';
            sendBtn.disabled = false;
            currentBotDiv = null;
            currentContentDiv = null;
            rawText = '';
            msgInput.focus();
        } else if (msg.command === 'error') {
            if (currentContentDiv) {
                currentContentDiv.className = 'msg-content err';
                currentContentDiv.textContent = 'Error: ' + msg.text;
            }
            statusText.textContent = 'Ready';
            sendBtn.disabled = false;
            currentBotDiv = null;
            currentContentDiv = null;
            rawText = '';
        } else if (msg.command === 'status') {
            statusText.textContent = msg.text || 'Thinking...';
        } else if (msg.command === 'diagnose') {
            addMsg('user', msg.text);
            vscode.postMessage({ command: 'send', text: msg.text });
            statusText.textContent = 'Thinking...';
            sendBtn.disabled = true;
            rawText = '';
            currentBotDiv = addMsg('bot', '');
            currentContentDiv = currentBotDiv.querySelector('.msg-content');
            currentContentDiv.innerHTML = '<span class="cursor"></span>';
        } else if (msg.command === 'session_ended') {
            endBtn.disabled = false;
            var summary = msg.summary;
            if (summary && summary.topics_covered && summary.topics_covered.length > 0) {
                addMsg('bot', '**Session ended.** Topics covered: ' + summary.topics_covered.join(', ') + '\n\nYour progress has been saved. Send a new message to start a fresh session.');
            } else {
                addMsg('bot', '**Session ended.** Your progress has been saved.\n\nSend a new message to start a fresh session.');
            }
            currentBotDiv = null;
            currentContentDiv = null;
            rawText = '';
            sendBtn.disabled = false;
            statusText.textContent = 'Ready';
            msgInput.focus();
        }
    });

    addMsg('bot', 'Hello! I am PythonMentor! Ask any Python question and I will guide you to find the answer yourself.\n\n**First time?** The backend will start automatically. This may take a few minutes on first run.\n\n**Need to configure LLM?** Click the gear icon ⚙️ or run "PythonMentor: Configure API Keys" command.');
    msgInput.focus();
})();
