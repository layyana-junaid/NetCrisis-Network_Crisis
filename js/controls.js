/* ============================================
   NETCRISIS — Control Panel Controller
   All actions call FastAPI REST endpoints.
   ============================================ */

const API = 'http://localhost:8000';

export class ControlPanel {
  constructor(topologyRenderer, eventBus) {
    this.topology = topologyRenderer;
    this.eventBus = eventBus;
    this.openDropdown = null;
    this.cachedNodes = [];
  }

  init() {
    this._bindAttackButtons();
    this._bindNetworkButtons();
    this._bindResetButton();
    this._bindSpeedToggle();
    this._bindStartPause();
    document.addEventListener('click', () => this._closeDropdown());
    this.eventBus.on('state-update', data => { this.cachedNodes = data.nodes || []; });
  }

  /* ---- Attack buttons → REST POST /control/attack ---- */
  _bindAttackButtons() {
    const attacks = [
      { btn: 'btn-ddos', type: 'ddos' },
      { btn: 'btn-bgp', type: 'bgp_hijack' },
      { btn: 'btn-mitm', type: 'mitm' },
      { btn: 'btn-scan', type: 'port_scan' },
    ];
    attacks.forEach(({ btn, type }) => {
      const el = document.getElementById(btn);
      if (!el) return;
      el.addEventListener('click', e => {
        e.stopPropagation();
        this._showDropdown(el, type);
      });
    });
  }

  _showDropdown(button, attackType) {
    this._closeDropdown();
    const targets = this.cachedNodes.filter(n => n.status !== 'isolated' && n.status !== 'compromised');
    if (!targets.length) return;
    const dd = document.createElement('div');
    dd.className = 'target-dropdown'; dd.id = 'active-dropdown';
    targets.forEach(node => {
      const item = document.createElement('button');
      item.className = 'target-dropdown__item';
      item.textContent = `${node.label} (${node.ip})`;
      item.addEventListener('click', e => {
        e.stopPropagation();
        fetch(`${API}/control/attack`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: attackType, target: node.id }),
        }).catch(err => console.error(err));
        this._closeDropdown();
      });
      dd.appendChild(item);
    });
    button.style.position = 'relative';
    button.appendChild(dd);
    this.openDropdown = dd;
  }

  _closeDropdown() {
    const el = document.getElementById('active-dropdown');
    if (el) el.remove();
    this.openDropdown = null;
  }

  /* ---- Network controls → topology interactionMode ---- */
  _bindNetworkButtons() {
    const cutBtn = document.getElementById('btn-cut-link');
    const restBtn = document.getElementById('btn-restore-link');
    if (cutBtn) cutBtn.addEventListener('click', () => {
      this.topology.setInteractionMode('cut_link');
    });
    if (restBtn) restBtn.addEventListener('click', () => {
      this.topology.setInteractionMode('restore_link');
    });
  }

  /* ---- Reset → REST POST /control/reset ---- */
  _bindResetButton() {
    const btn = document.getElementById('btn-reset');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const overlay = document.createElement('div');
      overlay.className = 'confirm-overlay';
      overlay.innerHTML = `
        <div class="confirm-dialog">
          <div class="confirm-dialog__title">RESET SIMULATION</div>
          <div class="confirm-dialog__text">Stop all attacks, restore all nodes, reset tick counter.</div>
          <div class="confirm-dialog__actions">
            <button class="confirm-dialog__btn confirm-dialog__btn--cancel" id="confirm-cancel">CANCEL</button>
            <button class="confirm-dialog__btn confirm-dialog__btn--confirm" id="confirm-ok">RESET</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      document.getElementById('confirm-cancel').addEventListener('click', () => overlay.remove());
      document.getElementById('confirm-ok').addEventListener('click', () => {
        fetch(`${API}/control/reset`, { method: 'POST' }).catch(console.error);
        this.eventBus.emit('simulation-reset');
        overlay.remove();
      });
      overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
    });
  }

  /* ---- Speed toggle → REST POST /control/speed ---- */
  _bindSpeedToggle() {
    document.querySelectorAll('.speed-toggle__btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const speed = parseFloat(btn.dataset.speed);
        fetch(`${API}/control/speed?speed=${speed}`, { method: 'POST' }).catch(console.error);
        document.querySelectorAll('.speed-toggle__btn').forEach(b =>
          b.classList.toggle('speed-toggle__btn--active', b === btn));
      });
    });
  }

  /* ---- Space bar → start/pause ---- */
  _bindStartPause() {
    document.addEventListener('keydown', e => {
      if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        // Toggle via REST
        fetch(`${API}/health`).then(r => r.json()).then(data => {
          const endpoint = data.state === 'running' || data.state === 'crisis' ? 'pause' : 'start';
          fetch(`${API}/control/${endpoint}`, { method: 'POST' }).catch(console.error);
        }).catch(console.error);
      }
    });
  }
}
