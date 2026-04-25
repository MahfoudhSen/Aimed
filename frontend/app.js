const API = 'http://localhost:8000';

// ── Chat state ────────────────────────────────────────────────
let chatHistory = [];
let chatBusy = false;

// ── Chat panel ────────────────────────────────────────────────
function openChat() {
  document.getElementById('chat-panel').classList.add('open');
  document.getElementById('chat-input').focus();
}

function closeChat() {
  document.getElementById('chat-panel').classList.remove('open');
}

function chatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

function sendSuggestion(text) {
  document.getElementById('chat-suggestions').style.display = 'none';
  document.getElementById('chat-input').value = text;
  sendChat();
}

async function sendChat() {
  if (chatBusy) return;
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  chatBusy = true;
  document.getElementById('chat-send-btn').disabled = true;
  document.getElementById('chat-suggestions').style.display = 'none';

  appendMessage('user', text);
  chatHistory.push({ role: 'user', content: text });

  const typingId = appendTyping();

  try {
    const response = await fetch(`${API}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: chatHistory }),
    });

    removeTyping(typingId);

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let botText = '';
    let botBubble = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = JSON.parse(line.slice(6));

        if (data.type === 'text') {
          if (!botBubble) botBubble = appendMessage('bot', '');
          botText += data.content;
          botBubble.innerHTML = formatMessage(botText);
          scrollChat();
        } else if (data.type === 'tool_call') {
          appendToolNotice(data.name);
        } else if (data.type === 'done') {
          break;
        }
      }
    }

    if (botText) {
      chatHistory.push({ role: 'assistant', content: botText });
    }

  } catch (err) {
    removeTyping(typingId);
    appendMessage('bot', `Sorry, something went wrong: ${err.message}. Make sure the backend is running.`);
  }

  chatBusy = false;
  document.getElementById('chat-send-btn').disabled = false;
  input.focus();
}

function appendMessage(role, text) {
  const container = document.getElementById('chat-messages');
  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-message ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.innerHTML = formatMessage(text);
  msgDiv.appendChild(bubble);
  container.appendChild(msgDiv);
  scrollChat();
  return bubble;
}

function appendTyping() {
  const container = document.getElementById('chat-messages');
  const id = 'typing-' + Date.now();
  const msgDiv = document.createElement('div');
  msgDiv.className = 'chat-message bot typing';
  msgDiv.id = id;
  msgDiv.innerHTML = `<div class="message-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  container.appendChild(msgDiv);
  scrollChat();
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendToolNotice(toolName) {
  const container = document.getElementById('chat-messages');
  const notice = document.createElement('div');
  notice.className = 'tool-notice';
  const labels = {
    search_listings: '🔍 Searching listings...',
    calculate_affordability: '📊 Calculating affordability...',
  };
  notice.textContent = labels[toolName] || `⚙️ Running ${toolName}...`;
  container.appendChild(notice);
  scrollChat();
}

function scrollChat() {
  const container = document.getElementById('chat-messages');
  container.scrollTop = container.scrollHeight;
}

function formatMessage(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>');
}

// ── Hero search ───────────────────────────────────────────────
function heroSearch() {
  const val = document.getElementById('hero-search-input').value.trim();
  if (!val) return;
  document.getElementById('search-query').value = val;
  document.getElementById('search').scrollIntoView({ behavior: 'smooth' });
  doSearch();
}

function quickSearch(query) {
  document.getElementById('hero-search-input').value = query;
  heroSearch();
}

document.addEventListener('keydown', (e) => {
  const heroInput = document.getElementById('hero-search-input');
  if (document.activeElement === heroInput && e.key === 'Enter') heroSearch();
});

// ── Listing search ────────────────────────────────────────────
async function doSearch() {
  const q = document.getElementById('search-query').value.trim();
  if (!q) return;
  const budget = document.getElementById('search-budget').value;
  const location = document.getElementById('search-location').value;

  const resultsEl = document.getElementById('search-results');
  const emptyEl = document.getElementById('search-empty');

  resultsEl.innerHTML = '<div class="loading"><div class="spinner"></div> Searching listings...</div>';
  resultsEl.classList.remove('hidden');
  emptyEl.classList.add('hidden');

  try {
    const params = new URLSearchParams({ q, location });
    if (budget) params.append('budget', budget);
    const res = await fetch(`${API}/api/search?${params}`);
    const data = await res.json();

    if (!data.results || data.results.length === 0) {
      resultsEl.innerHTML = '<p style="color:var(--text-muted);padding:24px 0">No results found. Try a different search.</p>';
      return;
    }

    resultsEl.innerHTML = data.results.map(r => `
      <div class="result-card">
        <h3><a href="${escHtml(r.url)}" target="_blank" rel="noopener">${escHtml(r.title) || 'Listing'}</a></h3>
        <p class="result-snippet">${escHtml(r.snippet)}</p>
        ${r.url ? `<div class="result-source">${new URL(r.url).hostname}</div>` : ''}
      </div>
    `).join('');

  } catch (err) {
    resultsEl.innerHTML = `<p style="color:var(--danger)">Error: ${escHtml(err.message)}</p>`;
  }
}

// ── Scam checker ──────────────────────────────────────────────
async function checkScam() {
  const text = document.getElementById('scam-text').value.trim();
  if (!text) { alert('Please paste a listing to analyze.'); return; }

  const resultEl = document.getElementById('scam-result');
  resultEl.classList.remove('hidden');
  resultEl.innerHTML = '<div class="loading"><div class="spinner"></div> Analyzing listing...</div>';

  try {
    const res = await fetch(`${API}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ listing_text: text }),
    });
    const data = await res.json();

    const level = (data.risk_level || 'unknown').toLowerCase();
    const score = data.risk_score ?? 0;
    const flags = data.red_flags || [];

    resultEl.innerHTML = `
      <div class="scam-card risk-${level}">
        <span class="risk-badge ${level}">
          ${{ low: '✅ Low Risk', medium: '⚠️ Medium Risk', high: '🚨 High Risk' }[level] || '❓ Unknown Risk'}
        </span>
        <div class="risk-score ${level}">${score}/100</div>
        <p style="color:var(--text-muted);font-size:.8rem;margin-bottom:12px">Risk Score</p>
        ${flags.length ? `
          <div class="red-flags">
            <h4>Red Flags Found (${flags.length})</h4>
            ${flags.map(f => `<div class="flag-item">${escHtml(f)}</div>`).join('')}
          </div>` : ''}
        <p class="scam-explanation">${escHtml(data.explanation || '')}</p>
        ${data.recommendation ? `<div class="recommendation">💡 ${escHtml(data.recommendation)}</div>` : ''}
      </div>`;
  } catch (err) {
    resultEl.innerHTML = `<p style="color:var(--danger)">Error: ${escHtml(err.message)}</p>`;
  }
}

// ── Affordability calculator ──────────────────────────────────
function calcAffordability() {
  const rent = parseFloat(document.getElementById('calc-rent').value);
  const income = parseFloat(document.getElementById('calc-income').value);
  const resultEl = document.getElementById('calc-result');

  if (!rent || !income || rent <= 0 || income <= 0) {
    alert('Please enter valid rent and income amounts.');
    return;
  }

  const ratio = rent / income;
  const percent = (ratio * 100).toFixed(1);
  const affordable = ratio <= 0.30;
  const maxRent = Math.round(income * 0.30);
  const cls = affordable ? 'affordable' : 'over-budget';

  resultEl.classList.remove('hidden');
  resultEl.innerHTML = `
    <div class="calc-card ${cls}">
      <div class="calc-verdict ${cls}">${affordable ? '✅ Affordable' : '❌ Over Budget'}</div>
      <div class="calc-percent ${cls}">${percent}%</div>
      <p style="color:var(--text-muted);font-size:.8rem;margin-bottom:16px">of income spent on rent</p>
      <div class="calc-details">
        <div class="calc-row"><span>Monthly Rent</span><span>$${rent.toLocaleString()}</span></div>
        <div class="calc-row"><span>Monthly Income</span><span>$${income.toLocaleString()}</span></div>
        <div class="calc-row"><span>Max Affordable (30% rule)</span><span>$${maxRent.toLocaleString()}</span></div>
        ${!affordable ? `<div class="calc-row"><span>Over Budget By</span><span style="color:var(--danger)">$${(rent - maxRent).toLocaleString()}/mo</span></div>` : ''}
      </div>
      <div class="calc-message ${cls}">
        ${affordable
          ? `This rent is within the recommended 30% threshold. You have $${(income - rent).toLocaleString()}/mo remaining after rent.`
          : `This rent exceeds the 30% rule by $${(rent - maxRent).toLocaleString()}/mo. Consider looking for listings under $${maxRent.toLocaleString()}/mo.`}
      </div>
    </div>`;
}

// ── Util ──────────────────────────────────────────────────────
function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
