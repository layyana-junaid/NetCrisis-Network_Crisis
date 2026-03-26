/* ============================================
   NETCRISIS — Main Application Entry
   WebSocket client connecting to Python backend.
   ============================================ */

import { EventBus } from './network.js';
import { TopologyRenderer } from './topology.js';
import { DashboardRenderer } from './dashboard.js';
import { LogPanel } from './logs.js';
import { ControlPanel } from './controls.js';

const WS_URL = 'ws://localhost:8000/ws';
const API = 'http://localhost:8000';

class NetCrisisApp {
  constructor() {
    this.eventBus = new EventBus();
    this.topology = new TopologyRenderer(this.eventBus);
    this.dashboard = new DashboardRenderer(this.eventBus);
    this.logPanel = new LogPanel(this.eventBus);
    this.controls = null;
    this.ws = null;
    this.reconnectTimer = null;
  }

  init() {
    this.topology.init();
    this.dashboard.init();
    this.logPanel.init();
    this.controls = new ControlPanel(this.topology, this.eventBus);
    this.controls.init();
    this._bindTopBar();
    this._connectWebSocket();

    // Auto-start simulation after connection
    setTimeout(() => {
      fetch(`${API}/control/start`, { method: 'POST' }).catch(() => {});
    }, 2000);
  }

  /* ---- WebSocket Connection ---- */
  _connectWebSocket() {
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => {
      console.log('[NETCRISIS] WebSocket connected');
      if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this._handleMessage(data);
      } catch (e) {
        console.error('[NETCRISIS] Parse error:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[NETCRISIS] WebSocket disconnected, reconnecting...');
      this.reconnectTimer = setTimeout(() => this._connectWebSocket(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error('[NETCRISIS] WebSocket error:', err);
    };
  }

  /* ---- Handle incoming backend messages ---- */
  _handleMessage(data) {
    // Update topology and dashboard
    this.eventBus.emit('state-update', data);

    // Update top bar
    this._updateTopBar(data);

    // Process new log entries
    if (data.logs && data.logs.length) {
      data.logs.forEach(log => this.eventBus.emit('log', log));
    }

    // Animate packets
    if (data.packets && data.packets.length) {
      data.packets.forEach(pkt => this.eventBus.emit('packet', pkt));
    }
  }

  /* ---- Top Bar Updates ---- */
  _bindTopBar() {
    // Initial state
    this.scoreEl = document.getElementById('health-score');
    this.tickEl = document.getElementById('tick-counter');
    this.badgeEl = document.getElementById('status-badge');
    this.dotEl = document.getElementById('status-dot');
  }

  _updateTopBar(data) {
    if (this.scoreEl) {
      this.scoreEl.textContent = data.health;
      this.scoreEl.className = 'topbar-health__score';
      if (data.health >= 80) this.scoreEl.classList.add('topbar-health__score--healthy');
      else if (data.health >= 50) this.scoreEl.classList.add('topbar-health__score--warning');
      else this.scoreEl.classList.add('topbar-health__score--critical');
    }
    if (this.tickEl) {
      this.tickEl.textContent = `TICK ${String(data.tick).padStart(3, '0')}`;
    }
    if (this.badgeEl) {
      this.badgeEl.className = `topbar-status__badge topbar-status__badge--${data.state}`;
      this.badgeEl.textContent = data.state.toUpperCase();
    }
    if (this.dotEl) {
      this.dotEl.className = 'topbar-logo__dot';
      if (data.state === 'running' || data.state === 'crisis') {
        this.dotEl.classList.add('topbar-logo__dot--active');
      }
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const app = new NetCrisisApp();
  app.init();
  window.__netcrisis = app;
});
