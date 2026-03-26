/* ============================================
   NETCRISIS — Health Dashboard Renderer
   Receives state from backend WebSocket.
   ============================================ */

export class DashboardRenderer {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.donutCircumference = 0;
    this.nodesInitialized = false;
  }

  init() {
    this._createDonut();
    this._bindEvents();
  }

  _createDonut() {
    const container = document.querySelector('.donut-container');
    const size = 140, r = 54;
    this.donutCircumference = 2 * Math.PI * r;
    container.innerHTML = `
      <svg class="donut-svg" viewBox="0 0 ${size} ${size}">
        <defs>
          <linearGradient id="donut-grad">
            <stop offset="0%" stop-color="#E056A0"/>
            <stop offset="100%" stop-color="#C0392B"/>
          </linearGradient>
        </defs>
        <circle class="donut-bg" cx="${size/2}" cy="${size/2}" r="${r}"/>
        <circle class="donut-fill" id="donut-fill"
          cx="${size/2}" cy="${size/2}" r="${r}"
          stroke="url(#donut-grad)"
          stroke-dasharray="${this.donutCircumference}"
          stroke-dashoffset="0"/>
        <text class="donut-center-text" id="donut-text" x="${size/2}" y="${size/2}">100</text>
      </svg>
      <div class="donut-label">OVERALL HEALTH</div>`;
  }

  initNodeCards(nodes) {
    if (this.nodesInitialized) return;
    this.nodesInitialized = true;
    const grid = document.querySelector('.node-cards-grid');
    grid.innerHTML = '';
    nodes.forEach(node => {
      const card = document.createElement('div');
      card.className = 'node-card';
      card.id = `card-${node.id}`;
      card.innerHTML = `
        <div class="node-card__header">
          <span class="node-card__name">${node.label}</span>
          <span class="node-card__ip">${node.ip}</span>
        </div>
        <div class="node-card__health-bar">
          <div class="node-card__health-fill" id="health-fill-${node.id}"
               style="width:${node.health}%;background:${this._hc(node.health)}"></div>
        </div>
        <div class="node-card__footer">
          <span class="node-card__type">${node.type}</span>
          <span class="status-badge status-badge--${node.status}" id="badge-${node.id}">
            ${node.status.replace('_', ' ')}
          </span>
        </div>`;
      grid.appendChild(card);
    });
  }

  _hc(h) { return h >= 80 ? '#00FF88' : h >= 50 ? '#FFB800' : '#FF3B3B'; }

  updateHealth(health) {
    const offset = this.donutCircumference * (1 - health / 100);
    const fill = document.getElementById('donut-fill');
    const text = document.getElementById('donut-text');
    if (fill) {
      fill.style.strokeDashoffset = offset;
      fill.style.stroke = health >= 80 ? '#00FF88' : health >= 50 ? '#FFB800' : '#FF3B3B';
    }
    if (text) text.textContent = Math.round(health);
  }

  updateNodes(nodes) {
    nodes.forEach(node => {
      const hf = document.getElementById(`health-fill-${node.id}`);
      if (hf) { hf.style.width = `${node.health}%`; hf.style.background = this._hc(node.health); }
      const badge = document.getElementById(`badge-${node.id}`);
      if (badge) { badge.className = `status-badge status-badge--${node.status}`; badge.textContent = node.status.replace('_', ' '); }
    });
  }

  updateAttackBanner(activeAttacks) {
    const banner = document.getElementById('attack-banner');
    if (!banner) return;
    if (activeAttacks && activeAttacks.length > 0) {
      const labels = { ddos: 'DDoS', bgp_hijack: 'BGP Hijack', mitm: 'MITM', port_scan: 'Port Scan' };
      const msgs = activeAttacks.map(a => `${labels[a.type] || a.type} on ${a.target}`);
      banner.classList.add('attack-banner--active');
      banner.querySelector('.attack-banner__text').textContent = `ACTIVE: ${msgs.join(' | ')}`;
    } else {
      banner.classList.remove('attack-banner--active');
    }
  }

  _bindEvents() {
    this.eventBus.on('state-update', data => {
      this.initNodeCards(data.nodes);
      this.updateHealth(data.health);
      this.updateNodes(data.nodes);
      this.updateAttackBanner(data.active_attacks);
    });
    this.eventBus.on('simulation-reset', () => {
      this.updateHealth(100);
      const banner = document.getElementById('attack-banner');
      if (banner) banner.classList.remove('attack-banner--active');
    });
  }
}
