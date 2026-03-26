/* ============================================
   NETCRISIS — D3.js Topology Graph Renderer
   Receives all state from backend WebSocket.
   ============================================ */

export class TopologyRenderer {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.svg = null;
    this.simulation = null;
    this.linkElements = null;
    this.nodeElements = null;
    this.tooltip = null;
    this.width = 0;
    this.height = 0;
    this.packetLayer = null;
    this.nodes = [];
    this.links = [];
    this.initialized = false;
    this.interactionMode = null;
    this.selectedNode = null;
  }

  init() {
    const container = document.getElementById('topology-container');
    this.tooltip = document.getElementById('topology-tooltip');
    const rect = container.getBoundingClientRect();
    this.width = rect.width;
    this.height = rect.height;

    this.svg = d3.select('#topology-svg')
      .attr('viewBox', `0 0 ${this.width} ${this.height}`)
      .attr('preserveAspectRatio', 'xMidYMid meet');

    const defs = this.svg.append('defs');
    const bgGrad = defs.append('radialGradient')
      .attr('id', 'bg-glow').attr('cx', '50%').attr('cy', '50%').attr('r', '50%');
    bgGrad.append('stop').attr('offset', '0%').attr('stop-color', '#2D1219').attr('stop-opacity', 0.3);
    bgGrad.append('stop').attr('offset', '100%').attr('stop-color', '#1A0A0F').attr('stop-opacity', 0);

    this.svg.append('circle')
      .attr('cx', this.width / 2).attr('cy', this.height / 2)
      .attr('r', Math.min(this.width, this.height) * 0.4)
      .attr('fill', 'url(#bg-glow)');

    this.linkLayer = this.svg.append('g').attr('class', 'links');
    this.packetLayer = this.svg.append('g').attr('class', 'packets');
    this.nodeLayer = this.svg.append('g').attr('class', 'nodes');

    this._bindResize();
    this._bindEvents();
  }

  /* ------ Called once with first backend state ------ */
  initGraph(stateNodes, stateLinks) {
    if (this.initialized) return;
    this.initialized = true;

    const cx = this.width / 2, cy = this.height / 2;
    const layout = {
      CR1: { x: cx - 80, y: cy - 60 }, CR2: { x: cx + 80, y: cy - 60 },
      CR3: { x: cx, y: cy + 60 },
      ER1: { x: cx - 200, y: cy - 140 }, ER2: { x: cx + 200, y: cy - 140 },
      ER3: { x: cx - 200, y: cy + 140 }, ER4: { x: cx + 200, y: cy + 140 },
      H1: { x: cx - 300, y: cy - 200 }, H2: { x: cx - 280, y: cy - 80 },
      H3: { x: cx + 280, y: cy - 200 }, H4: { x: cx + 300, y: cy - 80 },
      H5: { x: cx - 300, y: cy + 200 }, H6: { x: cx + 300, y: cy + 200 },
      DNS: { x: cx - 120, y: cy + 220 }, WEB: { x: cx + 120, y: cy - 220 },
      DB: { x: cx + 120, y: cy + 220 },
    };

    this.nodes = stateNodes.map(n => {
      const pos = layout[n.id] || { x: cx + (Math.random() - 0.5) * 200, y: cy + (Math.random() - 0.5) * 200 };
      return { ...n, x: pos.x, y: pos.y };
    });

    this.links = stateLinks.map(l => ({
      ...l,
      source: l.source,
      target: l.target,
    }));

    this._createSimulation();
    this._createLinks();
    this._createNodes();
  }

  /* ------ Called every tick with backend state ------ */
  updateFromState(stateNodes, stateLinks) {
    if (!this.initialized) {
      this.initGraph(stateNodes, stateLinks);
      return;
    }
    // Update node attributes without touching x/y
    stateNodes.forEach(sn => {
      const n = this.nodes.find(nd => nd.id === sn.id);
      if (n) {
        n.health = sn.health;
        n.status = sn.status;
        n.services = sn.services;
        n.acl = sn.acl;
      }
    });
    // Update link attributes
    stateLinks.forEach(sl => {
      const l = this.links.find(lk => lk.id === sl.id);
      if (l) {
        l.utilization = sl.utilization;
        l.status = sl.status;
        l.bandwidth = sl.bandwidth;
      }
    });
    this._updateVisuals();
  }

  /* ------ D3 Force Simulation (local layout only) ------ */
  _createSimulation() {
    const self = this;
    this.simulation = d3.forceSimulation(this.nodes)
      .force('link', d3.forceLink(this.links).id(d => d.id)
        .distance(d => {
          const s = typeof d.source === 'object' ? d.source : this.nodes.find(n => n.id === d.source);
          const t = typeof d.target === 'object' ? d.target : this.nodes.find(n => n.id === d.target);
          if (s && t && s.type === 'core' && t.type === 'core') return 100;
          if (s && t && (s.type === 'host' || t.type === 'host')) return 120;
          return 140;
        }).strength(0.5))
      .force('charge', d3.forceManyBody().strength(d => {
        if (d.type === 'core') return -400;
        if (d.type === 'edge') return -300;
        return -200;
      }))
      .force('center', d3.forceCenter(this.width / 2, this.height / 2).strength(0.05))
      .force('collision', d3.forceCollide().radius(d => this._getRadius(d) + 20))
      .force('x', d3.forceX(this.width / 2).strength(0.02))
      .force('y', d3.forceY(this.height / 2).strength(0.02))
      .alpha(0.8).alphaDecay(0.02)
      .on('tick', () => this._onTick());
  }

  _getRadius(d) {
    switch (d.type) {
      case 'core': return 28; case 'edge': return 20;
      case 'server': return 18; case 'host': return 14; default: return 14;
    }
  }
  _getStrokeWidth(d) {
    switch (d.type) {
      case 'core': return 3; case 'edge': return 2;
      case 'server': return 2; case 'host': return 1.5; default: return 1.5;
    }
  }
  _getLinkClass(d) {
    if (d.status === 'severed') return 'severed';
    if (d.utilization > 70) return 'high';
    if (d.utilization > 40) return 'medium';
    return 'normal';
  }

  _createLinks() {
    this.linkElements = this.linkLayer.selectAll('.link')
      .data(this.links).enter().append('line')
      .attr('class', d => `link link--${this._getLinkClass(d)}`)
      .attr('data-id', d => d.id);
  }

  _createNodes() {
    const self = this;
    this.nodeElements = this.nodeLayer.selectAll('.node')
      .data(this.nodes).enter().append('g')
      .attr('class', d => `node node--${d.status}`)
      .attr('data-id', d => d.id)
      .call(d3.drag()
        .on('start', (e, d) => { if (!e.active) self.simulation.alphaTarget(0.1).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) self.simulation.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .on('mouseenter', function (e, d) { self._showTooltip(e, d); })
      .on('mouseleave', () => this._hideTooltip())
      .on('click', (e, d) => this._onNodeClick(e, d));

    this.nodeElements.each(function (d) {
      const el = d3.select(this);
      const r = self._getRadius(d), sw = self._getStrokeWidth(d);
      if (d.type === 'server') {
        const s = r * 1.2;
        el.append('polygon').attr('class', 'node-shape')
          .attr('points', `0,${-s} ${s},0 0,${s} ${-s},0`).attr('stroke-width', sw);
      } else {
        el.append('circle').attr('class', 'node-shape').attr('r', r).attr('stroke-width', sw);
      }
    });
    this.nodeElements.append('text').attr('class', 'node-label')
      .attr('y', d => this._getRadius(d) + 16).text(d => d.label);
  }

  _onTick() {
    const pad = 40;
    this.nodes.forEach(d => {
      d.x = Math.max(pad, Math.min(this.width - pad, d.x));
      d.y = Math.max(pad, Math.min(this.height - pad, d.y));
    });
    this.linkElements.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    this.nodeElements.attr('transform', d => `translate(${d.x},${d.y})`);
  }

  _updateVisuals() {
    this.nodeElements.attr('class', d => `node node--${d.status}`);
    this.linkElements.attr('class', d => `link link--${this._getLinkClass(d)}`);
  }

  _showTooltip(event, d) {
    const container = document.getElementById('topology-container');
    const rect = container.getBoundingClientRect();
    const hc = d.health >= 80 ? '#00FF88' : d.health >= 50 ? '#FFB800' : '#FF3B3B';
    this.tooltip.innerHTML = `
      <div class="tooltip-header">
        <span class="tooltip-name">${d.label}</span><span class="tooltip-ip">${d.ip}</span>
      </div>
      <div class="tooltip-row"><span class="tooltip-row__label">TYPE</span><span class="tooltip-row__value">${d.type.toUpperCase()}</span></div>
      <div class="tooltip-row"><span class="tooltip-row__label">HEALTH</span><span class="tooltip-row__value" style="color:${hc}">${Math.round(d.health)}%</span></div>
      <div class="tooltip-row"><span class="tooltip-row__label">STATUS</span><span class="tooltip-row__value">${d.status.toUpperCase().replace('_', ' ')}</span></div>
      ${d.services.length ? `<div class="tooltip-row"><span class="tooltip-row__label">SERVICES</span><span class="tooltip-row__value">${d.services.join(', ')}</span></div>` : ''}
      <div class="tooltip-health-bar"><div class="tooltip-health-bar__fill" style="width:${d.health}%;background:${hc}"></div></div>`;
    let left = event.clientX - rect.left + 16, top = event.clientY - rect.top - 10;
    if (left + 220 > rect.width) left = event.clientX - rect.left - 220;
    if (top + 180 > rect.height) top = event.clientY - rect.top - 180;
    this.tooltip.style.left = `${left}px`;
    this.tooltip.style.top = `${top}px`;
    this.tooltip.classList.add('topology-tooltip--visible');
  }
  _hideTooltip() { this.tooltip.classList.remove('topology-tooltip--visible'); }

  _onNodeClick(event, d) {
    if (this.interactionMode === 'cut_link' || this.interactionMode === 'restore_link') {
      if (!this.selectedNode) {
        this.selectedNode = d.id;
        d3.select(event.currentTarget).select('.node-shape').attr('stroke', '#FFFFFF').attr('stroke-width', 4);
      } else {
        const a = this.selectedNode, b = d.id;
        const endpoint = this.interactionMode === 'cut_link' ? '/control/cut-link' : '/control/restore-link';
        fetch(`http://localhost:8000${endpoint}`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source: a, target: b }),
        }).catch(err => console.error(err));
        this.selectedNode = null;
        this.interactionMode = null;
        this.eventBus.emit('interaction-mode-change', null);
      }
    }
  }

  setInteractionMode(mode) {
    this.interactionMode = mode;
    this.selectedNode = null;
    if (this.nodeElements) {
      this.nodeElements.selectAll('.node-shape').attr('stroke-width', d => this._getStrokeWidth(d));
    }
  }

  animatePacket(path, type) {
    if (!path || path.length < 2 || !this.initialized) return;
    const positions = path.map(id => {
      const node = this.nodes.find(n => n.id === id);
      return node ? { x: node.x, y: node.y } : null;
    }).filter(Boolean);
    if (positions.length < 2) return;
    const r = type === 'malicious' ? 5 : 4;
    const color = type === 'malicious' ? '#FF3B3B' : '#00D4FF';
    const opacity = type === 'malicious' ? 0.8 : 0.6;
    const packet = this.packetLayer.append('circle')
      .attr('class', `packet packet--${type}`).attr('r', r)
      .attr('fill', color).attr('opacity', opacity)
      .attr('cx', positions[0].x).attr('cy', positions[0].y);
    let i = 0;
    const hop = () => {
      i++;
      if (i >= positions.length) { packet.remove(); return; }
      packet.transition().duration(500).ease(d3.easeQuadInOut)
        .attr('cx', positions[i].x).attr('cy', positions[i].y).on('end', hop);
    };
    hop();
  }

  _bindResize() {
    window.addEventListener('resize', () => {
      const container = document.getElementById('topology-container');
      const rect = container.getBoundingClientRect();
      this.width = rect.width; this.height = rect.height;
      this.svg.attr('viewBox', `0 0 ${this.width} ${this.height}`);
      if (this.simulation) {
        this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
        this.simulation.alpha(0.3).restart();
      }
    });
  }

  _bindEvents() {
    this.eventBus.on('packet', data => this.animatePacket(data.path, data.type));
    this.eventBus.on('state-update', data => this.updateFromState(data.nodes, data.links));
    this.eventBus.on('simulation-reset', () => {
      if (this.packetLayer) this.packetLayer.selectAll('.packet').remove();
    });
  }
}
