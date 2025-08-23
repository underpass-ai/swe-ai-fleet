const s = (sel) => document.querySelector(sel);
const backlogEl = s('#backlog');
const chatEl = s('#chat');
const roleEl = s('#role');
const goalForm = s('#goal-form');
const chatForm = s('#chat-form');
const senderEl = s('#sender');
const messageEl = s('#message');

function addChat({ sender, role, text, timestamp }) {
  const row = document.createElement('div');
  row.className = 'chat-row';
  const when = new Date(timestamp || Date.now()).toLocaleTimeString();
  row.innerHTML = `<span class="meta">[${when}] ${role} (${sender})</span>: <span class="text">${text}</span>`;
  chatEl.appendChild(row);
  chatEl.scrollTop = chatEl.scrollHeight;
}

function renderBacklog(items) {
  backlogEl.innerHTML = '';
  items
    .sort((a, b) => a.created_at.localeCompare(b.created_at))
    .forEach((item) => {
      const li = document.createElement('li');
      li.className = 'card';
      li.innerHTML = `
        <div class="row between">
          <strong>${item.title}</strong>
          <span class="status ${item.status.replace(/\s+/g, '-').toLowerCase()}">${item.status}</span>
        </div>
        <div class="desc"><em>Epic:</em> ${item.epic || 'General'}</div>
        <div class="desc">${item.description || ''}</div>
        <details>
          <summary>Events (${item.events.length})</summary>
          <ul>${item.events.map((e) => `<li>${e}</li>`).join('')}</ul>
        </details>
      `;
      backlogEl.appendChild(li);
    });
}

async function getState() {
  const res = await fetch('/state');
  if (!res.ok) return;
  const data = await res.json();
  populateRoles(data.roles);
  renderBacklog(data.backlog || []);
  (data.messages || []).forEach(addChat);
}

function populateRoles(roles) {
  roleEl.innerHTML = '';
  roles.forEach((r) => {
    const opt = document.createElement('option');
    opt.value = r;
    opt.textContent = r;
    if (r === 'Product Owner') opt.selected = true;
    roleEl.appendChild(opt);
  });
}

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);

  ws.addEventListener('open', () => {
    // keep-alive pings by sending a noop text periodically
    setInterval(() => ws.readyState === 1 && ws.send('ping'), 15000);
  });

  ws.addEventListener('message', (ev) => {
    try {
      const { type, payload } = JSON.parse(ev.data);
      if (type === 'init') {
        populateRoles(payload.roles || []);
        renderBacklog(payload.backlog || []);
        (payload.messages || []).forEach(addChat);
      } else if (type === 'chat') {
        addChat(payload);
      } else if (type === 'backlog_update') {
        // merge item into list
        const items = Array.from(backlogEl.children).map((li) => li.item).filter(Boolean);
        // fallback: just refetch state for simplicity
        getState();
      }
    } catch (e) {
      console.warn('WS message parse failed', e);
    }
  });

  ws.addEventListener('close', () => {
    setTimeout(connectWS, 2000);
  });
}

// Forms

goalForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const title = s('#goal-title').value.trim();
  const description = s('#goal-desc').value.trim();
  const epic = s('#goal-epic').value.trim() || 'General';
  if (!title) return;
  await fetch('/goals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description, epic }),
  });
  s('#goal-title').value = '';
  s('#goal-desc').value = '';
  s('#goal-epic').value = '';
});

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const sender = senderEl.value.trim() || 'Product Owner';
  const role = roleEl.value || 'Product Owner';
  const text = messageEl.value.trim();
  if (!text) return;
  await fetch('/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sender, role, text }),
  });
  messageEl.value = '';
});

// Init
getState();
connectWS();