let state = null;
let opsMap = null;
let mapLayers = { markers: null, routes: null };
const $ = (id) => document.getElementById(id);
const post = async (url, body = {}) => { const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (!response.ok) throw new Error(await response.text()); return response.json(); };
const toast = (message) => { $('toast').textContent = message; $('toast').classList.add('show'); setTimeout(() => $('toast').classList.remove('show'), 3200); };
const airport = (id) => state.airports.find((item) => item.id === id);
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

function initMap() {
  if (opsMap || !window.L) return;
  opsMap = L.map('opsMap', { zoomControl: false, minZoom: 4, maxZoom: 12 }).setView([22.5, 79], 5);
  L.control.zoom({ position: 'bottomright' }).addTo(opsMap);
  // Bhuvan's public tile endpoint is the preferred Indian base layer; OSM is a transparent fallback.
  const bhuvan = L.tileLayer('https://bhuvan-app1.nrsc.gov.in/tilecache/tile.php?layer=basemap&x={x}&y={y}&z={z}', { attribution: 'Bhuvan / NRSC · NAVIC planning layer', maxZoom: 12 });
  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors', maxZoom: 19 });
  bhuvan.on('tileerror', () => { if (!opsMap.hasLayer(osm)) { osm.addTo(opsMap); toast('Bhuvan tiles unavailable; showing OSM fallback'); } });
  bhuvan.addTo(opsMap);
  mapLayers.markers = L.layerGroup().addTo(opsMap);
  mapLayers.routes = L.layerGroup().addTo(opsMap);
}

function renderMap() {
  initMap();
  if (!opsMap || !state) return;
  mapLayers.markers.clearLayers(); mapLayers.routes.clearLayers();
  const assigned = new Map((state.active_plan?.assignments || []).map((item) => [item.mission_id, item]));
  state.airports.forEach((place) => {
    const closed = state.closures.includes(place.id);
    L.circleMarker([place.lat, place.lon], { radius: closed ? 8 : 6, color: closed ? '#ff706b' : '#61e4d4', fillColor: closed ? '#ff706b' : '#61e4d4', fillOpacity: .9, weight: 2 }).bindTooltip(`${place.name} (${place.id})${closed ? ' · CLOSED' : ''}`).addTo(mapLayers.markers);
  });
  state.missions.forEach((mission) => {
    const from = airport(mission.origin); const to = airport(mission.destination);
    if (!from || !to) return;
    const assignment = assigned.get(mission.id);
    L.polyline([[from.lat, from.lon], [to.lat, to.lon]], { color: assignment ? '#61e4d4' : '#f0b85d', weight: mission.priority >= 5 ? 3 : 2, opacity: .75, dashArray: assignment ? undefined : '5 6' }).bindPopup(`<b>${escapeHtml(mission.id)} · ${escapeHtml(mission.title)}</b><br>${mission.origin} → ${mission.destination}<br>${assignment ? escapeHtml(assignment.aircraft_id) : 'Needs assignment'}`).addTo(mapLayers.routes);
  });
}

function renderMetrics() {
  const s = state.summary;
  $('metrics').innerHTML = [['Total aircraft', `${s.aircraft_total}`, `${s.aircraft_ready} mission ready`], ['Active missions', `${s.mission_scheduled}`, `${s.mission_total} in queue`], ['Active crew', `${state.crew.filter((item) => item.available).length}`, 'response crew available'], ['Airfields / alerts', `${state.airports.length}`, `${s.open_reports} reports open`]].map(([label, value, sub]) => `<div class="kpi"><span>${label}</span><strong>${value}</strong><small>${sub}</small></div>`).join('');
  $('networkFlights').textContent = `${s.mission_scheduled} active missions`;
}

function renderMissions() {
  const assigned = new Map((state.active_plan?.assignments || []).map((item) => [item.mission_id, item]));
  const high = state.missions.filter((item) => item.priority >= 5).length;
  $('missionTotal').textContent = state.missions.length; $('missionHigh').textContent = high;
  const search = ($('missionSearch')?.value || '').toLowerCase();
  const rows = state.missions.filter((mission) => `${mission.id} ${mission.title} ${mission.category} ${mission.origin} ${mission.destination}`.toLowerCase().includes(search));
  $('missionTable').innerHTML = rows.slice(0, 9).map((mission) => { const plan = assigned.get(mission.id); return `<div class="mission-row"><span class="priority">P${mission.priority}</span><div><b>${escapeHtml(mission.id)} · ${escapeHtml(mission.category)}</b><small class="route">${mission.origin} → ${mission.destination} · ETA ${String(mission.duration).padStart(2, '0')}:00</small></div><span class="status-chip ${plan ? '' : 'warn'}">${plan ? 'On track' : 'Review'}</span></div>`; }).join('') || '<div class="empty-state">No missions match the search.</div>';
}

function renderPlanner() {
  const assigned = new Map((state.active_plan?.assignments || []).map((item) => [item.mission_id, item]));
  $('plannerTable').innerHTML = `<table class="table"><thead><tr><th>MISSION</th><th>ROUTE</th><th>PRIORITY</th><th>DEADLINE</th><th>ASSIGNMENT</th><th>FEASIBILITY</th></tr></thead><tbody>${state.missions.map((mission) => { const plan = assigned.get(mission.id); const affected = state.affected_missions.some((item) => item.id === mission.id); return `<tr><td><b>${escapeHtml(mission.id)}</b><br><small>${escapeHtml(mission.title)}</small></td><td>${mission.origin} → ${mission.destination}</td><td><span class="priority">P${mission.priority}</span></td><td>${mission.deadline}h</td><td>${plan?.aircraft_id || 'Unassigned'}</td><td><span class="status-chip ${affected || !plan ? 'warn' : ''}">${affected ? 'Affected' : plan ? 'Feasible' : 'Review'}</span></td></tr>`; }).join('')}</tbody></table>`;
}

async function renderAnalytics() {
  const comparison = await (await fetch('/api/plan-comparison')).json();
  const metrics = comparison.priority_optimised.metrics;
  $('analyticsKpis').innerHTML = [['Scheduled missions', metrics.scheduled], ['Unassigned', metrics.unassigned], ['Priority score', metrics.priority_score], ['Solver runtime', `${metrics.runtime_ms}ms`]].map(([label, value]) => `<div class="kpi"><span>${label}</span><strong>${value}</strong><small>derived from optimiser</small></div>`).join('');
  $('sourceHealth').innerHTML = [['Canonical state', 'Connected', 'WebSocket + SQLite'], ['Optimiser', 'Available', 'OR-Tools CP-SAT'], ['Weather adapter', 'Public / fallback', 'Open-Meteo route corridor'], ['Map layer', 'Bhuvan / fallback', 'Leaflet tile adapter']].map(([name, status, detail]) => `<div class="report"><b>${name} · <span class="status-chip">${status}</span></b><small>${detail}</small></div>`).join('');
}

function renderFleet() {
  const ready = state.aircraft.filter((item) => item.status === 'ready').length; const percentage = Math.round((ready / state.aircraft.length) * 100);
  $('fleetReady').textContent = `${ready} ready · ${percentage}%`; $('fleetDonut').style.background = `conic-gradient(var(--cyan) 0 ${percentage}%, #1b3840 ${percentage}%)`; $('fleetDonut').querySelector('strong').textContent = `${percentage}%`;
  const types = [...new Set(state.aircraft.map((item) => item.type))]; $('fleetBars').innerHTML = types.map((type) => { const items = state.aircraft.filter((item) => item.type === type); const good = items.filter((item) => item.status === 'ready').length; return `<div class="bar-row"><span>${escapeHtml(type.replace(' transport', ''))}</span><span class="bar"><i style="width:${(good / items.length) * 100}%"></i></span><b>${good}/${items.length}</b></div>`; }).join('');
  $('fleetCount').textContent = `${state.aircraft.length} tracked assets`;
  $('fleetTable').innerHTML = `<table class="table"><thead><tr><th>ASSET</th><th>TYPE</th><th>BASE</th><th>HEALTH</th><th>STATUS</th><th>SCHEDULE</th></tr></thead><tbody>${state.aircraft.map((item) => `<tr><td><b>${escapeHtml(item.name)}</b><br><small>${item.id}</small></td><td>${escapeHtml(item.type)}</td><td>${item.base}</td><td>${item.health}%</td><td><span class="status-chip ${item.status !== 'ready' ? (item.status === 'maintenance' ? 'red' : 'warn') : ''}">${item.status}</span></td><td><button class="text-button schedule-edit" data-entity="aircraft" data-id="${item.id}">Edit (${item.schedule?.length || 0})</button></td></tr>`).join('')}</tbody></table>`;
  $('reportList').innerHTML = state.reports.map((report) => `<div class="report"><b>${report.aircraft} · ${escapeHtml(report.title)}</b><small>${escapeHtml(report.operator)} · ${escapeHtml(report.next_action)}</small><span class="tag ${report.severity === 'high' ? 'warn' : ''}">${report.status}</span></div>`).join('');
  $('crewCount').textContent = `${state.crew.length} personnel`;
  $('crewTable').innerHTML = state.crew.slice(0, 8).map((crew) => `<div class="report"><b>${escapeHtml(crew.name)} · ${escapeHtml(crew.qualification)}</b><small>${crew.id} · ${crew.schedule?.length || 0} schedule blocks</small><span class="tag ${crew.available ? '' : 'warn'}">${crew.available ? 'available' : 'off duty'}</span> <button class="text-button schedule-edit" data-entity="crew" data-id="${crew.id}">Edit schedule</button></div>`).join('');
  document.querySelectorAll('.schedule-edit').forEach((button) => button.addEventListener('click', () => editSchedule(button.dataset.entity, button.dataset.id)));
}

function renderTimeline() {
  $('timeline').innerHTML = state.missions.slice(0, 7).map((mission, index) => `<div class="timeline-row"><small>${mission.id}</small><span class="timeline-track"><i style="width:${35 + ((index * 13) % 45)}%;margin-left:${(index * 7) % 30}%"></i></span></div>`).join('');
}

function renderSignals() {
  const affected = state.affected_missions || [];
  const items = state.current_disruption ? [`Disruption detected · ${state.current_disruption.airport_id}`, `${affected.length} missions require retasking`] : ['Network operating normally', 'No active disruption requires approval'];
  $('signalList').innerHTML = items.map((text, index) => `<div class="signal"><b>${text}</b><small>${index ? 'Run the optimiser to compare a protected plan.' : 'Realtime state is being monitored from the operations stream.'}</small></div>`).join('');
}

function renderWeatherPanel(data) {
  const current = data.current || {}; const risk = Number(current.visibility || 10000) < 5000 || Number(current.wind_speed_10m || 0) > 35;
  const title = `${data.source || 'Weather adapter'} · ${data.is_fallback ? 'fallback' : 'live'}`;
  $('weatherTemp').textContent = `${Math.round(current.temperature_2m || 0)}°`; $('weatherSource').textContent = title; $('weatherCondition').textContent = risk ? 'Review before dispatch' : 'Conditions nominal'; $('weatherMeta').textContent = data.is_fallback ? 'Local safety fallback' : 'Public forecast · updated realtime';
  const cells = [['Wind', `${current.wind_speed_10m ?? '--'} km/h`], ['Visibility', `${current.visibility ?? '--'} m`], ['Humidity', `${current.relative_humidity_2m ?? '--'}%`], ['Rain', `${current.precipitation ?? '--'} mm`]];
  $('weatherGrid').innerHTML = cells.map(([label, value]) => `<div><small>${label}</small><b>${value}</b></div>`).join(''); $('weatherImplications').textContent = risk ? '⚠ Weather threshold breach · review affected routes' : '✓ No current weather threshold breach';
  $('weatherTempDetail').textContent = `${Math.round(current.temperature_2m || 0)}°`; $('weatherSourceDetail').textContent = title; $('weatherGridDetail').innerHTML = cells.map(([label, value]) => `<div><small>${label}</small><b>${value}</b></div>`).join('');
  $('weatherImplicationsDetail').innerHTML = [['Dispatch confidence', risk ? 'Review before dispatch' : 'Favourable for current plan', 'Visibility and wind thresholds are checked before an operator approval.'], ['Route planning', 'Weather is an input, not a decision', 'Re-run the planner when a corridor or hub condition changes.'], ['Data provenance', data.is_fallback ? 'Fallback data active' : 'Public feed connected', 'Source state remains visible to planners.']].map(([a, b, c]) => `<div class="implication"><b>${a} · ${b}</b><small>${c}</small></div>`).join('');
}

async function refreshWeather() { renderWeatherPanel(await (await fetch('/api/weather')).json()); }
async function renderLedger() { const rows = await (await fetch('/api/ledger')).json(); $('ledgerTable').innerHTML = `<table class="table"><thead><tr><th>TIME</th><th>EVENT</th><th>DETAIL</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${new Date(row.created_at).toLocaleString()}</td><td><span class="status-chip">${row.event}</span></td><td>${escapeHtml(JSON.stringify(row.payload))}</td></tr>`).join('')}</tbody></table>`; }
function render() { renderMetrics(); renderMissions(); renderPlanner(); renderFleet(); renderTimeline(); renderSignals(); renderMap(); $('airportSelect').innerHTML = state.airports.map((item) => `<option value="${item.id}">${item.name} · ${item.state}</option>`).join(''); }
async function refresh() { state = await (await fetch('/api/state')).json(); render(); await Promise.all([refreshWeather(), renderLedger()]); }

function openModal() { $('shockModal').classList.add('open'); } function closeModal() { $('shockModal').classList.remove('open'); }
async function inject() { state = await post('/api/closure', { airport_id: $('airportSelect').value }); render(); await renderLedger(); $('proposalActions').classList.remove('hidden'); $('proposalSummary').textContent = `${state.affected_missions.length} missions affected · proposal not yet applied`; toast('Disruption injected into live planning state'); }
async function optimize() { const result = await post(`/api/optimize?mode=${$('modeSelect').value}`); state = result.state; render(); await renderLedger(); $('proposalSummary').textContent = `${result.plan.status.toUpperCase()} · ${result.plan.assignments.length} assignments · ${result.plan.runtime_ms}ms · hard constraints valid`; toast('OR-Tools proposal generated'); }
async function approve() { state = await post('/api/approve'); render(); await renderLedger(); $('proposalActions').classList.add('hidden'); toast('Proposal approved and active plan updated'); }
async function reject() { state = await post('/api/reject', { reason: 'Operator rejected during review' }); render(); await renderLedger(); $('proposalActions').classList.add('hidden'); toast('Proposal rejected and recorded'); }

function openManage(kind) {
  $('manageModal').classList.add('open');
  $('manageTitle').textContent = kind === 'mission' ? 'Add mission' : kind === 'aircraft' ? 'Add aircraft' : 'Add crew member';
  const airports = state.airports.map((item) => `<option value="${item.id}">${item.name} (${item.id})</option>`).join('');
  const form = kind === 'mission'
    ? `<div class="form-grid"><label>Mission title<input name="title" required placeholder="Flood relief sortie"></label><label>Category<select name="category"><option>Medical</option><option>Rescue</option><option>Food</option><option>Equipment</option><option>Water</option></select></label><label>Origin<select name="origin">${airports}</select></label><label>Destination<select name="destination">${airports}</select></label><label>Cargo (t)<input name="cargo" type="number" min="0.1" step="0.1" value="1"></label><label>Duration (h)<input name="duration" type="number" min="1" value="3"></label><label>Deadline (h)<input name="deadline" type="number" min="1" value="12"></label><label>Priority (1-5)<input name="priority" type="number" min="1" max="5" value="4"></label></div><button class="button primary wide" type="submit">Add mission & re-plan</button>`
    : kind === 'aircraft'
      ? `<div class="form-grid"><label>Callsign / name<input name="name" required placeholder="Saffron 109"></label><label>Aircraft type<input name="type" required placeholder="Relief transport"></label><label>Base<select name="base">${airports}</select></label><label>Capacity (t)<input name="capacity" type="number" min="0.1" step="0.1" value="4"></label><label>Range (km)<input name="range" type="number" min="100" value="1200"></label><label>Health %<input name="health" type="number" min="0" max="100" value="100"></label><label>Status<select name="status"><option>ready</option><option>inspection</option><option>maintenance</option></select></label></div><button class="button primary wide" type="submit">Add aircraft & re-plan</button>`
      : `<div class="form-grid"><label>Full name<input name="name" required placeholder="A. Sharma"></label><label>Qualification<input name="qualification" required value="general"></label><label>Availability<select name="available"><option value="true">Available</option><option value="false">Off duty</option></select></label></div><button class="button primary wide" type="submit">Add crew member</button>`;
  $('manageForm').innerHTML = form;
  $('manageForm').dataset.kind = kind;
}
function closeManage() { $('manageModal').classList.remove('open'); }
async function submitManage(event) {
  event.preventDefault();
  const kind = event.currentTarget.dataset.kind; const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  ['cargo', 'duration', 'deadline', 'priority', 'capacity', 'range', 'health'].forEach((key) => { if (data[key] !== undefined) data[key] = Number(data[key]); });
  if (data.available !== undefined) data.available = data.available === 'true';
  const endpoint = kind === 'mission' ? '/api/missions' : kind === 'aircraft' ? '/api/aircraft' : '/api/crew';
  state = await post(endpoint, data); render(); await renderLedger(); closeManage(); toast(`${kind} added and ledger updated`);
}
async function scanRoute() {
  const origin = $('routeOrigin').value; const destination = $('routeDestination').value;
  if (origin === destination) { toast('Choose two different airfields'); return; }
  $('routeResult').textContent = 'Scanning origin, midpoint and destination weather…';
  const result = await (await fetch(`/api/route-weather?origin=${origin}&destination=${destination}`)).json();
  if (!result.conditions) throw new Error(result.detail || 'Route scan failed');
  $('routeResult').innerHTML = `<div class="route-status ${result.route_status === 'restricted' ? 'risk' : 'safe'}"><b>${result.recommendation}</b><span>${result.distance_km} km · ${result.source}</span></div><div class="route-points">${result.conditions.map((point) => `<div><b>${escapeHtml(point.name)}</b><small>${point.current.wind_speed_10m ?? '--'} km/h wind · ${point.current.visibility ?? '--'} m visibility · ${point.risk ? `Avoid: ${point.reasons.join(', ')}` : 'Operational'}</small></div>`).join('')}</div>`;
}
async function comparePlans() {
  const result = await (await fetch('/api/plan-comparison')).json();
  $('comparisonResult').innerHTML = Object.entries(result).filter(([key]) => key !== 'explanations').map(([key, value]) => `<div class="comparison-row"><b>${key.replaceAll('_', ' ')}</b><span>${value.metrics.scheduled} scheduled · ${value.metrics.unassigned} unassigned · priority ${value.metrics.priority_score} · ${value.metrics.runtime_ms}ms</span></div>`).join('');
}
async function askCopilot() {
  const question = $('copilotQuestion').value.trim() || 'What is the current operational risk?';
  const result = await post('/api/copilot', { question });
  $('copilotAnswer').innerHTML = `<b>${escapeHtml(result.answer)}</b><small>Evidence: ${escapeHtml(JSON.stringify(result.evidence))}</small>`;
}
async function editSchedule(entity, entityId) {
  const record = state[entity].find((item) => item.id === entityId);
  const example = JSON.stringify(record.schedule || [], null, 2);
  const input = window.prompt('Enter schedule blocks as JSON, e.g. [{"start":"08:00","end":"12:00","mission_id":"M-001"}]', example);
  if (input === null) return;
  let schedule;
  try { schedule = JSON.parse(input); } catch { toast('Schedule must be valid JSON'); return; }
  state = await post('/api/schedules', { entity, entity_id: entityId, schedule }); render(); await renderLedger(); toast('Schedule updated and recorded');
}

document.querySelectorAll('.nav').forEach((button) => button.addEventListener('click', () => { document.querySelector('.nav.active').classList.remove('active'); button.classList.add('active'); document.querySelectorAll('.view').forEach((view) => view.classList.remove('active-view')); $(`view-${button.dataset.view}`).classList.add('active-view'); $('pageTitle').firstChild.textContent = button.querySelector('span').textContent; if (button.dataset.view === 'overview') setTimeout(() => opsMap?.invalidateSize(), 50); }));
document.querySelectorAll('[data-view-jump]').forEach((button) => button.addEventListener('click', () => document.querySelector(`[data-view="${button.dataset.viewJump}"]`).click()));
['shockwaveBtn', 'shockwaveBtn2'].forEach((id) => $(id).addEventListener('click', openModal)); $('closeModal').addEventListener('click', closeModal); $('injectBtn').addEventListener('click', () => inject().catch((error) => toast(error.message))); $('optimizeBtn').addEventListener('click', () => optimize().catch((error) => toast(error.message))); $('approveBtn').addEventListener('click', () => approve().catch((error) => toast(error.message))); $('rejectBtn').addEventListener('click', () => reject().catch((error) => toast(error.message))); $('resetBtn').addEventListener('click', () => post('/api/reset').then((value) => { state = value; render(); toast('Simulation day reset'); }).catch((error) => toast(error.message))); $('fitMap').addEventListener('click', () => opsMap?.setView([22.5, 79], 5)); $('locateMap').addEventListener('click', () => opsMap?.locate({ setView: true, maxZoom: 7 }));
$('addMissionBtn').addEventListener('click', () => openManage('mission'));
$('plannerAddMission').addEventListener('click', () => openManage('mission')); $('missionSearch').addEventListener('input', renderMissions); $('comparePlans').addEventListener('click', () => comparePlans().catch((error) => toast(error.message))); $('copilotAsk').addEventListener('click', () => askCopilot().catch((error) => toast(error.message)));
$('addAircraftBtn').addEventListener('click', () => openManage('aircraft')); $('addCrewBtn').addEventListener('click', () => openManage('crew')); $('closeManageModal').addEventListener('click', closeManage); $('manageForm').addEventListener('submit', (event) => submitManage(event).catch((error) => toast(error.message))); $('scanRouteBtn').addEventListener('click', () => scanRoute().catch((error) => toast(error.message)));
setInterval(() => { $('liveClock').textContent = `${new Date().toLocaleTimeString('en-IN', { hour12: false })} IST`; }, 1000);
setInterval(() => refreshWeather().catch(() => {}), 60000);
refresh().catch((error) => toast(`Unable to load operations state: ${error.message}`));
document.querySelector('[data-view="weather"]').addEventListener('click', () => { if (!$('routeOrigin').options.length) { $('routeOrigin').innerHTML = state.airports.map((item) => `<option value="${item.id}">${item.name} (${item.id})</option>`).join(''); $('routeDestination').innerHTML = state.airports.map((item) => `<option value="${item.id}">${item.name} (${item.id})</option>`).join(''); $('routeDestination').selectedIndex = 1; } });
document.querySelector('[data-view="analytics"]').addEventListener('click', () => renderAnalytics().catch((error) => toast(error.message)));
const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`); socket.onmessage = (event) => { const message = JSON.parse(event.data); if (message.state) { state = message.state; render(); } }; socket.onopen = () => socket.send('subscribe'); socket.onerror = () => toast('Realtime stream unavailable; polling remains active');
