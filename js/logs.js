/* ============================================
   NETCRISIS — Log Panel Controller
   Receives log entries from backend WebSocket.
   ============================================ */

export class LogPanel {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.logs = { attack: [], defense: [], monitor: [] };
    this.activeTab = 'attack';
    this.maxEntries = 200;
  }

  init() {
    document.querySelectorAll('.logs-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.activeTab = tab.dataset.tab;
        document.querySelectorAll('.logs-tab').forEach(t =>
          t.classList.toggle('logs-tab--active', t.dataset.tab === this.activeTab));
        this._renderAll();
      });
    });
    this._bindEvents();
  }

  addEntry(data) {
    const type = data.type;
    if (!this.logs[type]) return;
    this.logs[type].push({ tick: data.tick, message: data.message, detail: data.detail || '' });
    if (this.logs[type].length > this.maxEntries)
      this.logs[type] = this.logs[type].slice(-this.maxEntries);
    if (this.activeTab === type) this._appendOne(data, type);
  }

  _appendOne(entry, type) {
    const list = document.querySelector('.logs-list');
    if (!list) return;
    const el = document.createElement('div');
    el.className = `log-entry log-entry--${type}`;
    el.innerHTML = `
      <span class="log-entry__tick">[${String(entry.tick).padStart(3, '0')}]</span>
      <div class="log-entry__content">${entry.message}
        ${entry.detail ? `<span class="log-entry__detail">${entry.detail}</span>` : ''}
      </div>`;
    list.appendChild(el);
    requestAnimationFrame(() => { list.scrollTop = list.scrollHeight; });
  }

  _renderAll() {
    const list = document.querySelector('.logs-list');
    if (!list) return;
    list.innerHTML = '';
    (this.logs[this.activeTab] || []).forEach(e => this._appendOne(e, this.activeTab));
  }

  clear() {
    this.logs = { attack: [], defense: [], monitor: [] };
    this._renderAll();
  }

  _bindEvents() {
    this.eventBus.on('log', data => this.addEntry(data));
    this.eventBus.on('simulation-reset', () => this.clear());
  }
}
