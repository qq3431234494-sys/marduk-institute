const bgEffect = {
    init() {
        const canvas = document.querySelector('.bg-canvas');
        if (!canvas) return;

        const glow = document.createElement('div');
        glow.style.cssText = `
            position: absolute;
            width: 400px; height: 400px; border-radius: 50%;
            background: radial-gradient(circle, rgba(255,107,43,0.1), transparent 70%);
            pointer-events: none;
            transition: transform 0.3s ease-out, opacity 0.3s;
            opacity: 0; filter: blur(50px);
        `;
        canvas.appendChild(glow);

        let rafId = null;
        document.addEventListener('mousemove', (e) => {
            if (rafId) cancelAnimationFrame(rafId);
            rafId = requestAnimationFrame(() => {
                glow.style.opacity = '1';
                glow.style.transform = `translate(${e.clientX - 200}px, ${e.clientY - 200}px)`;
            });
        });

        document.addEventListener('mouseleave', () => {
            glow.style.opacity = '0';
        });
    }
};

const hud = {
    init() {
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);
        this.animateSyncBar(0);
        this.startMagiNetwork();
    },

    updateClock() {
        const el = document.getElementById('footerTime');
        if (el) {
            const now = new Date();
            el.textContent = now.toTimeString().split(' ')[0];
        }
    },

    animateSyncBar(score) {
        const bar = document.getElementById('syncBar');
        const value = document.getElementById('syncValue');
        if (bar) bar.style.width = score + '%';
        if (value) value.textContent = score + '%';
    },

    startMagiNetwork() {
        const nodes = [
            { id: 'pingT01', online: true, base: 3, range: 8 },
            { id: 'pingB02', online: true, base: 45, range: 30 },
            { id: 'pingM03', online: true, base: 55, range: 25 },
            { id: 'pingN04', online: false, base: 0, range: 0 },
            { id: 'pingH05', online: true, base: 12, range: 10 }
        ];

        const logMessages = [
            { from: 'MAGI-T01', to: 'MAGI-H05', msg: 'SYNC candidate_db checksum OK' },
            { from: 'MAGI-B02', to: 'MAGI-T01', msg: 'REQUEST pattern_analysis module v3.2' },
            { from: 'MAGI-T01', to: 'MAGI-M03', msg: 'PUSH evaluation_criteria update' },
            { from: 'MAGI-H05', to: 'MAGI-T01', msg: 'ACK interview_protocol received' },
            { from: 'MAGI-M03', to: 'MAGI-B02', msg: 'QUERY salary_benchmark data EAST-ASIA' },
            { from: 'MAGI-T01', to: 'MAGI-B02', msg: 'HANDSHAKE deliberation_sync OK' },
            { from: 'MAGI-B02', to: 'MAGI-H05', msg: 'FORWARD candidate_hash a3f8e2' },
            { from: 'MAGI-H05', to: 'MAGI-M03', msg: 'PING latency_test 12ms' },
            { from: 'MAGI-T01', to: 'MAGI-B02', msg: 'BROADCAST verdict_protocol v2.1' },
            { from: 'MAGI-M03', to: 'MAGI-T01', msg: 'REPORT anomaly_score 0.02 LOW' },
            { from: 'MAGI-B02', to: 'MAGI-H05', msg: 'REQUEST language_model zh-CN' },
            { from: 'MAGI-T01', to: 'MAGI-M03', msg: 'VERIFY integrity_check PASS' },
            { from: 'MAGI-H05', to: 'MAGI-B02', msg: 'SYNC interview_template batch_47' },
            { from: 'MAGI-N04', to: 'MAGI-T01', msg: 'TIMEOUT retry_connection...' }
        ];

        const updatePings = () => {
            nodes.forEach(node => {
                const el = document.getElementById(node.id);
                const dot = document.getElementById(node.id.replace('ping', 'dot'));
                if (!el) return;
                if (!node.online) {
                    el.textContent = 'OFFLINE';
                    el.className = 'node-ping offline';
                    if (dot) dot.className = 'node-dot offline';
                    return;
                }
                const ping = node.base + Math.floor(Math.random() * node.range);
                el.textContent = ping + 'ms';
                el.className = 'node-ping' + (ping > 60 ? ' high' : '');
                if (dot) dot.className = 'node-dot online' + (ping > 60 ? ' high' : '');
            });
        };

        let logIndex = 0;
        const addLog = () => {
            const logEl = document.getElementById('magiNetLog');
            if (!logEl) return;
            const entry = logMessages[logIndex % logMessages.length];
            logIndex++;
            const now = new Date();
            const ts = now.toTimeString().split(' ')[0];
            const line = document.createElement('div');
            line.className = 'log-line';
            line.innerHTML = `<span class="log-from">${entry.from}</span> → <span class="log-to">${entry.to}</span> ${entry.msg} [${ts}]`;
            logEl.appendChild(line);
            if (logEl.children.length > 4) {
                logEl.removeChild(logEl.firstChild);
            }
        };

        updatePings();
        addLog();
        setInterval(updatePings, 2000 + Math.random() * 1000);
        setInterval(addLog, 3000 + Math.random() * 2000);
    }
};

const auth = {
    token: null,
    username: null,
    pendingRecoveryKey: null,

    init() {
        this.token = localStorage.getItem('auth_token');
        this.username = localStorage.getItem('auth_username');

        const redirectParam = new URLSearchParams(window.location.search).get('redirect');
        if (this.token && redirectParam) {
            window.location.href = redirectParam;
            return;
        }

        if (this.token) {
            if (sessionStorage.getItem('disclaimer_confirmed')) {
                this.showApp();
            } else {
                this.showDisclaimer();
            }
        } else {
            this.showAuth();
        }

        this.bindAuthTabs();
        this.bindLoginForm();
        this.bindRegisterForm();
        this.bindForgotForm();
        this.bindRecoveryKeyModal();
        document.getElementById('btnLogout').addEventListener('click', () => this.logout());
    },

    showAuth() {
        document.getElementById('authOverlay').style.display = 'flex';
        document.getElementById('appMain').style.display = 'none';
    },

    showApp() {
        document.getElementById('authOverlay').style.display = 'none';
        document.getElementById('appMain').style.display = 'flex';
        document.getElementById('headerUsername').textContent = this.username || '--';
    },

    logout() {
        this.token = null;
        this.username = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_username');
        sessionStorage.removeItem('disclaimer_confirmed');
        this.showAuth();
    },

    bindAuthTabs() {
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const mode = tab.dataset.auth;
                document.getElementById('loginForm').style.display = mode === 'login' ? 'flex' : 'none';
                document.getElementById('registerForm').style.display = mode === 'register' ? 'flex' : 'none';
                document.getElementById('forgotForm').style.display = mode === 'forgot' ? 'flex' : 'none';
                document.getElementById('loginError').textContent = '';
                document.getElementById('registerError').textContent = '';
                document.getElementById('forgotError').textContent = '';
                document.getElementById('forgotSuccess').textContent = '';
            });
        });
    },

    bindLoginForm() {
        const captchaImg = document.getElementById('captchaImg');
        let captchaId = '';

        const loadCaptcha = async () => {
            try {
                const res = await fetch('/api/captcha?' + Date.now());
                captchaId = res.headers.get('X-Captcha-Id') || '';
                const blob = await res.blob();
                captchaImg.src = URL.createObjectURL(blob);
                document.getElementById('loginCaptcha').value = '';
            } catch (_) {}
        };

        captchaImg.addEventListener('click', loadCaptcha);
        loadCaptcha();

        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;
            const captcha_code = document.getElementById('loginCaptcha').value.trim();
            const errorEl = document.getElementById('loginError');
            const btn = document.getElementById('loginBtn');

            errorEl.textContent = '';
            btn.disabled = true;
            btn.textContent = '登录中...';

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, captcha_id: captchaId, captcha_code })
                });

                const data = await res.json();

                if (!res.ok) {
                    errorEl.textContent = data.error || '登录失败';
                    loadCaptcha();
                    return;
                }

                this.token = data.token;
                this.username = data.username;
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('auth_username', data.username);

                const redirectParam = new URLSearchParams(window.location.search).get('redirect');
                if (redirectParam) {
                    window.location.href = redirectParam;
                    return;
                }

                this.showDisclaimer();
            } catch (err) {
                errorEl.textContent = '网络错误，请重试';
            } finally {
                btn.disabled = false;
                btn.textContent = '登录';
            }
        });
    },

    bindRegisterForm() {
        document.getElementById('registerForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('regUsername').value.trim();
            const password = document.getElementById('regPassword').value;
            const confirm = document.getElementById('regPasswordConfirm').value;
            const errorEl = document.getElementById('registerError');
            const btn = document.getElementById('registerBtn');

            errorEl.textContent = '';

            if (password !== confirm) {
                errorEl.textContent = '两次输入的密码不一致';
                return;
            }

            btn.disabled = true;
            btn.textContent = '注册中...';

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await res.json();

                if (!res.ok) {
                    errorEl.textContent = data.error || '注册失败';
                    return;
                }

                this.token = data.token;
                this.username = data.username;
                localStorage.setItem('auth_token', data.token);
                localStorage.setItem('auth_username', data.username);

                if (data.recovery_key) {
                    this.pendingRecoveryKey = data.recovery_key;
                    this.pendingRedirect = new URLSearchParams(window.location.search).get('redirect');
                    this.showRecoveryKeyModal(data.recovery_key);
                } else {
                    const redirectParam = new URLSearchParams(window.location.search).get('redirect');
                    if (redirectParam) {
                        window.location.href = redirectParam;
                        return;
                    }
                    this.showDisclaimer();
                }
            } catch (err) {
                errorEl.textContent = '网络错误，请重试';
            } finally {
                btn.disabled = false;
                btn.textContent = '注册';
            }
        });
    },

    bindForgotForm() {
        document.getElementById('forgotForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('forgotUsername').value.trim();
            const recovery_key = document.getElementById('forgotRecoveryKey').value.trim();
            const new_password = document.getElementById('forgotNewPassword').value;
            const errorEl = document.getElementById('forgotError');
            const successEl = document.getElementById('forgotSuccess');
            const btn = document.getElementById('forgotBtn');

            errorEl.textContent = '';
            successEl.textContent = '';
            btn.disabled = true;
            btn.textContent = '重置中...';

            try {
                const res = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, recovery_key, new_password })
                });

                const data = await res.json();

                if (!res.ok) {
                    errorEl.textContent = data.error || '重置失败';
                    return;
                }

                successEl.textContent = '密码重置成功！请切换到登录页面使用新密码登录。';
                document.getElementById('forgotUsername').value = '';
                document.getElementById('forgotRecoveryKey').value = '';
                document.getElementById('forgotNewPassword').value = '';
            } catch (err) {
                errorEl.textContent = '网络错误，请重试';
            } finally {
                btn.disabled = false;
                btn.textContent = '重置密码';
            }
        });
    },

    bindRecoveryKeyModal() {
        document.getElementById('recoveryKeyCopyBtn').addEventListener('click', () => {
            const key = this.pendingRecoveryKey || document.getElementById('recoveryKeyDisplay').textContent;
            if (navigator.clipboard) {
                navigator.clipboard.writeText(key).then(() => {
                    const btn = document.getElementById('recoveryKeyCopyBtn');
                    btn.textContent = '已复制';
                    setTimeout(() => { btn.textContent = '复制验证码'; }, 2000);
                });
            } else {
                const el = document.getElementById('recoveryKeyDisplay');
                const range = document.createRange();
                range.selectNodeContents(el);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                document.execCommand('copy');
                const btn = document.getElementById('recoveryKeyCopyBtn');
                btn.textContent = '已复制';
                setTimeout(() => { btn.textContent = '复制验证码'; }, 2000);
            }
        });

        document.getElementById('recoveryKeyConfirmBtn').addEventListener('click', () => {
            document.getElementById('recoveryKeyModal').style.display = 'none';
            this.pendingRecoveryKey = null;
            if (this.pendingRedirect) {
                window.location.href = this.pendingRedirect;
                this.pendingRedirect = null;
                return;
            }
            this.showDisclaimer();
        });

        document.getElementById('disclaimerConfirmBtn').addEventListener('click', () => {
            document.getElementById('disclaimerModal').style.display = 'none';
            sessionStorage.setItem('disclaimer_confirmed', '1');
            this.showApp();
        });
    },

    showDisclaimer() {
        document.getElementById('disclaimerModal').style.display = 'flex';
    },

    showRecoveryKeyModal(key) {
        document.getElementById('recoveryKeyDisplay').textContent = key;
        document.getElementById('recoveryKeyModal').style.display = 'flex';
    },

    authHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`
        };
    }
};

const app = {
    resumeId: null,
    interviewStyle: "normal",
    isStreaming: false,
    pendingFile: null,
    interviewActive: false,
    isMobile: false,
    currentMobileView: 'data',

    init() {
        auth.init();
        this.randomizeMagi();
        this.detectMobile();
        this.bindUpload();
        this.bindTabs();
        this.bindChat();
        this.bindActions();
        this.bindMobileNav();
        window.addEventListener('resize', () => this.detectMobile());
    },

    detectMobile() {
        this.isMobile = window.innerWidth <= 768;
        if (this.isMobile) {
            this.switchMobileView(this.currentMobileView);
        } else {
            const pl = document.getElementById('uploadSection')?.closest('.panel-left');
            const pr = document.querySelector('.panel-right');
            if (pl) pl.classList.remove('mobile-hidden');
            if (pr) pr.classList.remove('mobile-hidden');
        }
    },

    bindMobileNav() {
        document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchMobileView(btn.dataset.view);
            });
        });

        const sysStatus = document.getElementById('systemStatus');
        if (sysStatus) {
            sysStatus.addEventListener('touchstart', (e) => {
                e.preventDefault();
                sysStatus.classList.toggle('touched');
            }, { passive: false });
            document.addEventListener('touchstart', (e) => {
                if (!sysStatus.contains(e.target)) {
                    sysStatus.classList.remove('touched');
                }
            });
        }
    },

    switchMobileView(view) {
        this.currentMobileView = view;
        const pl = document.querySelector('.panel-left');
        const pr = document.querySelector('.panel-right');

        if (view === 'data') {
            if (pl) pl.classList.remove('mobile-hidden');
            if (pr) pr.classList.add('mobile-hidden');
        } else {
            if (pl) pl.classList.add('mobile-hidden');
            if (pr) pr.classList.remove('mobile-hidden');
        }

        document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
    },

    randomizeMagi() {
        const magi = ['MELCHIOR-1', 'BALTHASAR-2', 'CASPER-3'];
        const pick = magi[Math.floor(Math.random() * magi.length)];
        document.getElementById('interviewerName').textContent = `MAGI AI · ${pick}`;
    },

    bindUpload() {
        const area = document.getElementById('uploadArea');
        const input = document.getElementById('fileInput');

        area.addEventListener('click', () => input.click());

        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('drag-over');
        });

        area.addEventListener('dragleave', () => {
            area.classList.remove('drag-over');
        });

        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) this.uploadFile(file);
        });

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.uploadFile(file);
        });
    },

    async uploadFile(file) {
        const validExts = ['.txt', '.pdf', '.docx'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!validExts.includes(ext)) {
            this.showToast('请上传 TXT、PDF 或 DOCX 格式的文件', 'error');
            return;
        }

        this.pendingFile = file;

        document.getElementById('uploadArea').style.display = 'none';
        document.getElementById('targetForm').style.display = 'block';
        this.validateTargetForm();

        ['targetPosition', 'targetCity', 'targetSalary'].forEach(id => {
            document.getElementById(id).addEventListener('input', () => this.validateTargetForm());
        });
    },

    validateTargetForm() {
        const position = document.getElementById('targetPosition').value.trim();
        const city = document.getElementById('targetCity').value.trim();
        const salary = document.getElementById('targetSalary').value.trim();
        document.getElementById('btnAnalyze').disabled = !(position && city && salary);
    },

    async analyzeResume() {
        const file = this.pendingFile;
        if (!file) return;

        const position = document.getElementById('targetPosition').value.trim();
        const salary = document.getElementById('targetSalary').value.trim();
        const city = document.getElementById('targetCity').value.trim();

        const progressEl = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        document.getElementById('targetForm').style.display = 'none';
        progressEl.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = 'UPLOADING...';

        const formData = new FormData();
        formData.append('file', file);
        if (position) formData.append('position', position);
        if (salary) formData.append('salary', salary);
        if (city) formData.append('city', city);

        try {
            progressFill.style.width = '30%';
            progressText.textContent = 'PARSING...';

            const res = await fetch('/api/upload', {
                method: 'POST',
                headers: auth.authHeaders(),
                body: formData
            });

            if (res.status === 401) {
                auth.logout();
                this.showToast('登录已过期，请重新登录', 'error');
                return;
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || '上传失败');
            }

            progressFill.style.width = '60%';
            progressText.textContent = 'ANALYZING...';

            const data = await res.json();
            this.resumeId = data.resume_id;

            progressFill.style.width = '90%';
            progressText.textContent = 'COMPLETE';

            setTimeout(() => {
                progressFill.style.width = '100%';
                this.showAnalysis(data.analysis);
                if (this.isMobile) this.switchMobileView('data');
                this.addSystemMessage(
                    `简历分析完成。请选择面试模式后点击 START SIMULATION 开始模拟面试。`
                );
            }, 500);

        } catch (err) {
            this.showToast(err.message, 'error');
            document.getElementById('uploadArea').style.display = '';
            progressEl.style.display = 'none';
        }
    },

    showAnalysis(analysis) {
        document.getElementById('uploadSection').style.display = 'none';
        document.getElementById('analysisSection').style.display = 'flex';

        const name = analysis.name || '未知';
        const title = analysis.title || analysis.current_role || '--';

        document.getElementById('candidateName').textContent = name;
        document.getElementById('candidateTitle').textContent = title;
        document.getElementById('candidateAvatar').textContent = name.charAt(0);

        const score = analysis.match_score || 0;
        document.getElementById('scoreValue').textContent = score + '%';
        const ring = document.getElementById('scoreRing');
        ring.style.background = `conic-gradient(var(--eva-green) ${score}%, rgba(57,255,20,0.08) ${score}%)`;
        hud.animateSyncBar(score);

        if (analysis.summary) {
            document.getElementById('summaryContent').innerHTML =
                analysis.summary.split('\n').map(p => p.trim()).filter(p => p).map(p => `<p>${p}</p>`).join('');
        }

        if (analysis.strengths && analysis.strengths.length) {
            document.getElementById('strengthsList').innerHTML =
                analysis.strengths.map(s => `<li>${s}</li>`).join('');
        }

        if (analysis.weaknesses && analysis.weaknesses.length) {
            document.getElementById('weaknessesList').innerHTML =
                analysis.weaknesses.map(w => `<li>${w}</li>`).join('');
        }

        if (analysis.suggestions && analysis.suggestions.length) {
            document.getElementById('suggestionsList').innerHTML =
                analysis.suggestions.map(s => `<li>${s}</li>`).join('');
        }

        const fit = analysis.fit_analysis || {};
        const posFit = fit.position_fit || 0;
        const salFit = fit.salary_fit || 0;

        document.getElementById('positionFitValue').textContent = posFit + '%';
        const posRing = document.getElementById('positionFitRing');
        posRing.style.background = `conic-gradient(var(--eva-green) ${posFit}%, rgba(57,255,20,0.08) ${posFit}%)`;

        document.getElementById('salaryFitValue').textContent = salFit + '%';
        const salRing = document.getElementById('salaryFitRing');
        salRing.style.background = `conic-gradient(var(--eva-amber) ${salFit}%, rgba(255,184,0,0.08) ${salFit}%)`;

        document.getElementById('positionReason').textContent = fit.position_reason || '未提供目标岗位信息，无法评估';
        document.getElementById('salaryReason').textContent = fit.salary_reason || '未提供目标薪资信息，无法评估';
        document.getElementById('careerAdvice').textContent = fit.career_advice || '--';

        if (fit.skill_gaps && fit.skill_gaps.length) {
            document.getElementById('skillGapsList').innerHTML =
                fit.skill_gaps.map(s => `<li>${s}</li>`).join('');
        } else {
            document.getElementById('skillGapsList').innerHTML = '<li class="no-gap">未发现明显技能缺口</li>';
        }
    },

    bindTabs() {
        document.querySelectorAll('.analysis-tabs .tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.analysis-tabs .tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });
    },

    bindChat() {
        const input = document.getElementById('chatInput');
        const btn = document.getElementById('btnSend');

        btn.addEventListener('click', () => this.sendMessage());

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    },

    bindActions() {
        document.getElementById('btnNewUpload').addEventListener('click', () => {
            this.resetAll();
        });

        document.getElementById('btnReupload').addEventListener('click', () => {
            this.pendingFile = null;
            document.getElementById('targetForm').style.display = 'none';
            document.getElementById('uploadArea').style.display = '';
            document.getElementById('fileInput').value = '';
            document.getElementById('targetPosition').value = '';
            document.getElementById('targetCity').value = '';
            document.getElementById('targetSalary').value = '';
        });

        document.getElementById('btnClearChat').addEventListener('click', () => {
            const messages = document.getElementById('chatMessages');
            messages.innerHTML = '';
            this.addSystemMessage('对话已清空。你可以继续向我提问。');
        });

        document.querySelectorAll('.style-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.interviewStyle = btn.dataset.style;
            });
        });

        document.getElementById('btnStartInterview').addEventListener('click', () => {
            this.startInterview();
        });

        document.getElementById('btnReinterview').addEventListener('click', () => {
            this.reinterview();
        });

        document.getElementById('btnAnalyze').addEventListener('click', () => {
            this.analyzeResume();
        });
    },

    enableChat() {
        document.getElementById('chatInput').disabled = false;
        document.getElementById('btnSend').disabled = false;
        document.getElementById('chatStatus').textContent = '面试进行中';
    },

    disableChat() {
        document.getElementById('chatInput').disabled = true;
        document.getElementById('btnSend').disabled = true;
    },

    addSystemMessage(text) {
        const messages = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = 'message system fade-in';
        div.innerHTML = `<div class="message-bubble">${this.formatText(text)}</div>`;
        messages.appendChild(div);
        this.scrollToBottom();
    },

    addUserMessage(text) {
        const messages = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = 'message user fade-in';
        div.innerHTML = `<div class="message-bubble">${this.formatText(text)}</div>`;
        messages.appendChild(div);
        this.scrollToBottom();
    },

    addStreamingMessage() {
        const messages = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = 'message system fade-in';
        div.id = 'streaming-msg';
        div.innerHTML = `<div class="message-bubble"><span class="typing-cursor"></span></div>`;
        messages.appendChild(div);
        this.scrollToBottom();
        return div.querySelector('.message-bubble');
    },

    updateStreamingMessage(bubble, text) {
        bubble.innerHTML = this.formatText(text) + '<span class="typing-cursor"></span>';
        this.scrollToBottom();
    },

    finalizeStreamingMessage(bubble, text) {
        bubble.innerHTML = this.formatText(text);
        this.scrollToBottom();
    },

    formatText(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
    },

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text || this.isStreaming || !this.resumeId || !this.interviewActive) return;

        input.value = '';
        input.style.height = 'auto';
        this.addUserMessage(text);

        this.isStreaming = true;
        this.disableChat();
        const badge1 = document.getElementById('deliberatingBadge');
        if (badge1) badge1.style.display = 'inline-block';

        const bubble = this.addStreamingMessage();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...auth.authHeaders()
                },
                body: JSON.stringify({
                    resume_id: this.resumeId,
                    message: text,
                    style: this.interviewStyle
                })
            });

            if (res.status === 401) {
                auth.logout();
                this.finalizeStreamingMessage(bubble, '登录已过期，请重新登录');
                return;
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || '请求失败');
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                fullText += parsed.content;
                                this.updateStreamingMessage(bubble, fullText);
                            }
                        } catch (e) {}
                    }
                }
            }

            let displayText = fullText;
            let interviewEnded = false;
            if (fullText.includes('[INTERVIEW_END]')) {
                displayText = fullText.replace(/\[INTERVIEW_END\]/g, '').trim();
                interviewEnded = true;
            }
            this.finalizeStreamingMessage(bubble, displayText);

            if (interviewEnded) {
                this.endInterview();
            }

        } catch (err) {
            this.finalizeStreamingMessage(bubble, '抱歉，发生了错误：' + err.message);
        } finally {
            this.isStreaming = false;
            const b2 = document.getElementById('deliberatingBadge');
            if (b2) b2.style.display = 'none';
            if (this.interviewActive) {
                this.enableChat();
                document.getElementById('chatInput').focus();
            }
        }
    },

    async startInterview() {
        if (!this.resumeId) return;

        this.isStreaming = true;
        this.interviewActive = true;
        this.disableChat();
        document.getElementById('btnStartInterview').disabled = true;
        const badge = document.getElementById('deliberatingBadge');
        if (badge) badge.style.display = 'inline-block';

        if (this.isMobile) this.switchMobileView('chat');

        const styleNames = { gentle: '温和鼓励', normal: '标准专业', tough: '压力刁难' };
        this.addSystemMessage(`面试模式已设定：${styleNames[this.interviewStyle] || '标准专业'}。面试即将开始...`);

        const bubble = this.addStreamingMessage();

        try {
            const res = await fetch('/api/start-interview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...auth.authHeaders()
                },
                body: JSON.stringify({ resume_id: this.resumeId, style: this.interviewStyle })
            });

            if (res.status === 401) {
                auth.logout();
                this.finalizeStreamingMessage(bubble, '登录已过期，请重新登录');
                return;
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.error || '启动面试失败');
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let fullText = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                fullText += parsed.content;
                                this.updateStreamingMessage(bubble, fullText);
                            }
                        } catch (e) {}
                    }
                }
            }

            let displayText = fullText;
            let interviewEnded = false;
            if (fullText.includes('[INTERVIEW_END]')) {
                displayText = fullText.replace(/\[INTERVIEW_END\]/g, '').trim();
                interviewEnded = true;
            }
            this.finalizeStreamingMessage(bubble, displayText);

            if (interviewEnded) {
                this.endInterview();
            }

        } catch (err) {
            this.finalizeStreamingMessage(bubble, '启动面试时出错：' + err.message);
        } finally {
            this.isStreaming = false;
            const b3 = document.getElementById('deliberatingBadge');
            if (b3) b3.style.display = 'none';
            if (this.interviewActive) {
                this.enableChat();
            }
        }
    },

    endInterview() {
        this.interviewActive = false;
        this.disableChat();
        const b4 = document.getElementById('deliberatingBadge');
        if (b4) b4.style.display = 'none';
        document.getElementById('chatStatus').textContent = '面试已结束 · MAGI审议中...';
        this.addSystemMessage('面试结束，正在提交MAGI审议系统进行三引擎表决...');
        this.requestVerdict();
    },

    async requestVerdict() {
        try {
            const res = await fetch('/api/verdict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...auth.authHeaders()
                },
                body: JSON.stringify({ resume_id: this.resumeId })
            });

            if (res.status === 401) {
                auth.logout();
                return;
            }

            const data = await res.json();
            if (!res.ok) {
                this.addSystemMessage('审议系统异常：' + (data.error || '未知错误'));
                return;
            }

            this.showVerdict(data.verdict);

        } catch (err) {
            this.addSystemMessage('审议请求失败：' + err.message);
        }
    },

    showVerdict(verdict) {
        const mv = document.getElementById('magiVerdict');
        const cm = document.getElementById('chatMessages');
        if (mv) mv.style.display = 'block';
        if (cm) cm.style.display = 'none';

        const engines = [
            { id: 'verdictMelchior', resultId: 'melchiorResult', reasonId: 'melchiorReason', key: 'melchior_1', delay: 800 },
            { id: 'verdictBalthasar', resultId: 'balthasarResult', reasonId: 'balthasarReason', key: 'balthasar_2', delay: 1600 },
            { id: 'verdictCasper', resultId: 'casperResult', reasonId: 'casperReason', key: 'casper_3', delay: 2400 }
        ];

        engines.forEach(engine => {
            const el = document.getElementById(engine.id);
            const resultEl = document.getElementById(engine.resultId);
            const reasonEl = document.getElementById(engine.reasonId);
            const data = verdict[engine.key] || { result: 'FAIL', reason: '审议异常' };

            setTimeout(() => {
                el.classList.add('revealed', data.result === 'PASS' ? 'pass' : 'fail');
                resultEl.textContent = data.result === 'PASS' ? 'PASS ✓' : 'FAIL ✗';
                reasonEl.textContent = data.reason || '';
            }, engine.delay);
        });

        const finalDelay = 3200;
        setTimeout(() => {
            const finalEl = document.getElementById('verdictFinal');
            const finalResultEl = document.getElementById('verdictFinalResult');
            const finalResult = verdict.final || 'FAIL';

            finalEl.classList.add('revealed', finalResult === 'PASS' ? 'pass' : 'fail');
            finalResultEl.textContent = finalResult === 'PASS' ? 'PASS - 适格者认定' : 'FAIL - 不予通过';

            document.getElementById('chatStatus').textContent = finalResult === 'PASS' ? '审议通过 · 适格者认定' : '审议未通过';
        }, finalDelay);
    },

    reinterview() {
        const mv2 = document.getElementById('magiVerdict');
        const cm2 = document.getElementById('chatMessages');
        if (mv2) mv2.style.display = 'none';
        if (cm2) { cm2.style.display = ''; cm2.innerHTML = ''; }
        document.getElementById('verdictMelchior').className = 'verdict-engine';
        document.getElementById('verdictBalthasar').className = 'verdict-engine';
        document.getElementById('verdictCasper').className = 'verdict-engine';
        document.getElementById('verdictFinal').className = 'verdict-final';
        document.getElementById('melchiorResult').textContent = '--';
        document.getElementById('balthasarResult').textContent = '--';
        document.getElementById('casperResult').textContent = '--';
        document.getElementById('melchiorReason').textContent = '';
        document.getElementById('balthasarReason').textContent = '';
        document.getElementById('casperReason').textContent = '';
        document.getElementById('verdictFinalResult').textContent = '--';

        this.interviewActive = false;
        document.getElementById('btnStartInterview').disabled = false;
        document.getElementById('chatStatus').textContent = '面试已结束，可重新开始';
        this.addSystemMessage('面试已重置。请选择面试模式后点击 START SIMULATION 重新开始。');
    },

    resetAll() {
        this.resumeId = null;
        this.isStreaming = false;
        this.pendingFile = null;
        this.interviewActive = false;

        document.getElementById('uploadSection').style.display = '';
        document.getElementById('uploadArea').style.display = '';
        document.getElementById('uploadProgress').style.display = 'none';
        document.getElementById('targetForm').style.display = 'none';
        document.getElementById('analysisSection').style.display = 'none';
        document.getElementById('fileInput').value = '';
        document.getElementById('targetPosition').value = '';
        document.getElementById('targetSalary').value = '';
        document.getElementById('targetCity').value = '';
        document.getElementById('btnStartInterview').disabled = false;
        const b5 = document.getElementById('deliberatingBadge');
        const mv3 = document.getElementById('magiVerdict');
        const cm3 = document.getElementById('chatMessages');
        if (b5) b5.style.display = 'none';
        if (mv3) mv3.style.display = 'none';
        if (cm3) cm3.style.display = '';

        if (cm3) cm3.innerHTML = '';
        this.addSystemMessage('👋 你好！我是 AI 面试官。请先上传简历，我将为你进行专业分析并模拟面试提问。');

        this.disableChat();
        document.getElementById('chatStatus').textContent = '等待简历上传...';
    },

    scrollToBottom() {
        const el = document.getElementById('chatMessages');
        el.scrollTop = el.scrollHeight;
    },

    showToast(message, type = 'info') {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            z-index: 9999;
            animation: fadeIn 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            color: #fff;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#4f46e5'};
        `;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => { bgEffect.init(); hud.init(); app.init(); checkRateLimit(); });

function checkRateLimit() {
    const now = Date.now();
    const key = 'marduk_rl';
    const blockKey = 'marduk_blocked_until';

    const blockedUntil = parseInt(localStorage.getItem(blockKey) || '0');
    if (now < blockedUntil) {
        window.location.replace('/firewall?from=' + encodeURIComponent(window.location.pathname));
        return;
    }

    let timestamps = JSON.parse(localStorage.getItem(key) || '[]');
    timestamps = timestamps.filter(t => now - t < 60000);
    timestamps.push(now);

    if (timestamps.length > 60) {
        localStorage.setItem(blockKey, String(now + 62000));
        localStorage.removeItem(key);
        window.location.replace('/firewall?from=' + encodeURIComponent(window.location.pathname));
        return;
    }

    localStorage.setItem(key, JSON.stringify(timestamps));
}
