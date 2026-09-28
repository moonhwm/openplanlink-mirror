/* Ouya Atlas — 交互与动效，零依赖 */
(function () {
  'use strict';

  var PALETTE = {
    crimson: ['#f7ecec', '#e8d4d4', '#8c2f2f', '#b8553f'],
    indigo:  ['#eef0f8', '#d9deee', '#2f3a8c', '#3f52b8'],
    amber:   ['#f9f2e4', '#ecdcbe', '#8c6a2f', '#b8893f'],
    jade:    ['#eaf4ee', '#d5e8dc', '#2f6b47', '#3f8a5c'],
    violet:  ['#f4ecf8', '#e4d6ee', '#6b2f8c', '#8a3fb8'],
    steel:   ['#edf2f3', '#dae3e5', '#3d5a63', '#5c7f8a'],
    ivory:   ['#f7f4ec', '#e8e1d3', '#6b6257', '#96886f'],
    rose:    ['#fbeef2', '#f0dae2', '#8c3f5d', '#b85f7f']
  };

  /* ── 封面：程序化 SVG（每主题一种纹样）── */
  function cover(theme, label) {
    var p = PALETTE[theme] || PALETTE.ivory;
    var bg1 = p[0], bg2 = p[1], ink = p[2], foil = p[3];
    var g = '';
    switch (theme) {
      case 'crimson':
        for (var i = 0; i < 7; i++) g += '<circle cx="50" cy="76" r="' + (12 + i * 9) + '" fill="none" stroke="' + foil + '" stroke-width="1" opacity="' + (0.55 - i * 0.06) + '"/>';
        break;
      case 'indigo':
        for (var j = 0; j < 9; j++) g += '<rect x="' + (6 + j * 11) + '" y="' + (18 + (j % 3) * 14) + '" width="5" height="' + (60 - j * 4) + '" fill="' + foil + '" opacity="' + (0.4 + j * 0.05) + '"/>';
        break;
      case 'amber':
        for (var k = 0; k < 6; k++) g += '<path d="M0 ' + (40 + k * 16) + ' Q 50 ' + (20 + k * 16) + ' 100 ' + (46 + k * 16) + '" stroke="' + foil + '" fill="none" stroke-width="1.2" opacity="0.5"/>';
        break;
      case 'jade':
        for (var m = 0; m < 5; m++) g += '<polygon points="50,' + (24 + m * 4) + ' ' + (86 - m * 6) + ',' + (84 + m * 3) + ' ' + (14 + m * 6) + ',' + (84 + m * 3) + '" fill="none" stroke="' + foil + '" opacity="' + (0.5 - m * 0.07) + '"/>';
        break;
      case 'violet':
        for (var n = 0; n < 24; n++) g += '<line x1="' + (n * 9) + '" y1="10" x2="' + (100 - n * 4) + '" y2="140" stroke="' + foil + '" stroke-width="0.6" opacity="0.32"/>';
        break;
      case 'steel':
        for (var o = 0; o < 8; o++) g += '<rect x="10" y="' + (14 + o * 15) + '" width="' + (80 - o * 7) + '" height="6" fill="' + foil + '" opacity="' + (0.45 - o * 0.04) + '"/>';
        break;
      case 'rose':
        for (var q = 0; q < 4; q++) g += '<ellipse cx="50" cy="76" rx="' + (14 + q * 12) + '" ry="' + (30 + q * 8) + '" fill="none" stroke="' + foil + '" opacity="' + (0.45 - q * 0.08) + '"/>';
        break;
      default:
        for (var r = 0; r < 10; r++) g += '<circle cx="' + (8 + r * 10) + '" cy="30" r="3" fill="' + foil + '" opacity="0.4"/><circle cx="' + (14 + r * 10) + '" cy="118" r="2" fill="' + foil + '" opacity="0.3"/>';
    }
    return '<svg viewBox="0 0 100 150" preserveAspectRatio="none">' +
      '<defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0" stop-color="' + bg1 + '"/><stop offset="1" stop-color="' + bg2 + '"/>' +
      '</linearGradient></defs>' +
      '<rect width="100" height="150" fill="url(#lg)"/>' + g +
      '<rect x="6" y="6" width="88" height="138" fill="none" stroke="' + foil + '" opacity="0.5"/>' +
      '<text x="50" y="146" text-anchor="middle" font-size="7" fill="' + ink + '" opacity="0.65" font-family="serif">' + esc(label.slice(0, 12)) + '</text>' +
      '</svg>';
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(n) { return (n || 0).toLocaleString('zh-CN'); }

  var state = { data: null, open: null, view: 'shelf', q: '' };

  /* ── 载入数据：优先内嵌，失败回退 fetch ── */
  function load(cb) {
    if (window.__SHELF__) return cb(window.__SHELF__);
    fetch('data/shelf.json').then(function (r) { return r.json(); })
      .then(cb).catch(function () { cb(makeFallback()); });
  }
  function makeFallback() {
    return {
      schema: 1, owner: '(未载入)', updated_at: '—', sources: [], bundles: [
        { bundle_id: '_x', title: '数据未载入', theme: 'ivory', count: 0, items: [], abstract: '请在本目录运行 serve.py 后用 http 打开，或执行 python sync/fetch.py 拉取明细。', source_id: '', tags: [], pending: true }
      ]
    };
  }

  /* ── 浮尘 ── */
  function dust(host) {
    if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var h = '';
    for (var i = 0; i < 34; i++) {
      var dur = 16 + Math.random() * 22, delay = Math.random() * 20;
      h += '<i style="left:' + (Math.random() * 100).toFixed(2) + '%;--dx:' + ((Math.random() * 90 - 45) | 0) + 'px;' +
        'animation-duration:' + dur.toFixed(1) + 's;animation-delay:' + delay.toFixed(1) + 's;' +
        'opacity:' + (0.25 + Math.random() * 0.5).toFixed(2) + '"></i>';
    }
    host.innerHTML = h;
  }

  /* ── 渲染 ── */
  function render() {
    var d = state.data;
    document.getElementById('ownerLine').textContent = d.owner || '—';
    document.getElementById('mBundle').textContent = fmt(d.bundles.length);
    var items = d.bundles.reduce(function (a, b) { return a + (b.items ? b.items.length : 0); }, 0);
    document.getElementById('mItem').textContent = fmt(items);
    document.getElementById('mTime').textContent = d.updated_at || '—';

    var unit = document.getElementById('shelfUnit');
    unit.innerHTML = '';
    var q = state.q.trim().toLowerCase();
    var shown = 0;

    d.bundles.forEach(function (b, idx) {
      var hay = (b.title + ' ' + (b.abstract || '') + ' ' + (b.tags || []).join(' ')).toLowerCase();
      if (q && hay.indexOf(q) === -1) return;
      shown++;

      var el = document.createElement('div');
      el.className = 'spine' + (b.pending && !b.items.length ? ' is-pending' : '');
      el.id = 'bundle-' + b.bundle_id;              // ← 锚点：支持 #node / #<bundle_id>
      el.style.setProperty('--d', (idx * 55) + 'ms');
      el.innerHTML =
        '<span class="tagdot"></span>' +
        '<span class="st">' + esc(b.title) + '</span>' +
        '<span class="sn">' + fmt(b.count || b.items.length || 0) + '</span>';

      var rows = document.createElement('div');
      rows.className = 'rows';
      var inner = document.createElement('div');
      if (b.items && b.items.length) {
        var li = b.items.map(function (it) {
          // note 是采集器附带的交接上下文（来源去向 / md5）；为空则不渲染，兼容既有数据源
          var noteHtml = it.note ? '<span class="note">' + esc(it.note) + '</span>' : '';
          return '<li><a href="' + esc(it.url || '#') + '" target="_blank" rel="noopener">' + esc(it.title) + '</a>' +
            '<span class="dur">' + esc(it.duration || '') + ' ' + esc(it.date || '') + '</span>' + noteHtml + '</li>';
        }).join('');
        inner.innerHTML = '<ul>' + li + '</ul>';
      } else {
        inner.innerHTML = '<div class="empty">' + (b.count ? ('该分区共 ' + fmt(b.count) + ' 条，明细待同步（本机运行 python sync/fetch.py 补齐）') : '公开页未给出计数，明细待同步') + '</div>';
      }
      rows.appendChild(inner);

      var wrap = document.createDocumentFragment();
      wrap.appendChild(el);
      wrap.appendChild(rows);

      el.addEventListener('click', function () {
        var wasOpen = rows.classList.contains('open');
        // 同册再点 = 折叠；切换 = 关旧的开新的
        Array.prototype.forEach.call(unit.querySelectorAll('.rows.open'), function (r) { r.classList.remove('open'); });
        Array.prototype.forEach.call(unit.querySelectorAll('.spine.is-open'), function (s) { s.classList.remove('is-open'); });
        if (!wasOpen || state.open !== b.bundle_id) {
          rows.classList.add('open');
          el.classList.add('is-open');
          state.open = b.bundle_id;
        } else {
          state.open = null;
        }
        openBook(b);
      });

      unit.appendChild(wrap);
    });

    if (!shown) unit.innerHTML = '<div class="rows open"><div><div class="empty">没有匹配「' + esc(state.q) + '」的书脊。</div></div></div>';

    // ETL
    var l0 = d.bundles.filter(function (b) { return b.pending && !b.items.length; }).length;
    var l1 = d.bundles.filter(function (b) { return b.items && b.items.length && b.open !== false; }).length;
    var l2 = d.bundles.filter(function (b) { return b.items && b.items.length >= 20; }).length;
    var tot = Math.max(1, d.bundles.length);
    setBar(0, l0 / tot, l0 + ' 单元');
    setBar(1, l1 / tot, l1 + ' 单元');
    setBar(2, l2 / tot, l2 + ' 单元');
    document.getElementById('etlNote').textContent =
      (d.sources && d.sources[0] && d.sources[0].note) || ('共 ' + d.bundles.length + ' 个归档单元');
  }

  function setBar(i, ratio, label) {
    var line = document.querySelectorAll('.etl-line')[i];
    if (!line) return;
    var bar = line.querySelector('i');
    bar.style.setProperty('--w', Math.round(ratio * 100) + '%');
    line.querySelector('b').textContent = label;
  }

  function openBook(b) {
    var deck = document.getElementById('deck');
    var src = (state.data.sources || []).filter(function (s) { return s.id === b.source_id; })[0];
    var items = (b.items || []).slice(0, 40).map(function (it) {
      return '<li><a href="' + esc(it.url || '#') + '" target="_blank" rel="noopener">' + esc(it.title) + '</a></li>';
    }).join('');
    deck.innerHTML =
      '<div class="deck-card">' +
      '<div class="deck-cover">' + cover(b.theme, b.title) + '</div>' +
      '<h2>' + esc(b.title) + '</h2>' +
      '<div class="src">' + esc((src && src.label) || b.source_id || '本地归档') + '</div>' +
      '<p class="abs">' + esc(b.abstract || '（暂无摘要）') + '</p>' +
      '<dl>' +
      '<dt>计数</dt><dd>' + fmt(b.count || b.items.length || 0) + '</dd>' +
      '<dt>明细</dt><dd>' + fmt((b.items || []).length) + '</dd>' +
      '<dt>标签</dt><dd>' + esc((b.tags || []).join(' / ') || '—') + '</dd>' +
      '</dl>' +
      (items ? '<ul class="items">' + items + '</ul>'
             : '<div class="rows open"><div><div class="empty">明细待同步</div></div></div>') +
      '</div>';
  }

  /* ── 绑定 ── */
  document.addEventListener('DOMContentLoaded', function () {
    dust(document.getElementById('dust'));
    load(function (d) { state.data = d; render(); });

    document.getElementById('viewSeg').addEventListener('click', function (e) {
      var btn = e.target.closest('.seg-btn'); if (!btn) return;
      Array.prototype.forEach.call(this.querySelectorAll('.seg-btn'), function (b) { b.classList.remove('is-on'); });
      btn.classList.add('is-on');
      state.view = btn.dataset.view;
      document.getElementById('library').classList.toggle('list-mode', state.view === 'list');
    });

    var timer;
    document.getElementById('q').addEventListener('input', function () {
      clearTimeout(timer);
      var v = this.value;
      timer = setTimeout(function () { state.q = v; render(); }, 180);
    });

    document.getElementById('expandAll').addEventListener('click', function () {
      Array.prototype.forEach.call(document.querySelectorAll('.rows'), function (r) { r.classList.add('open'); });
    });
    document.getElementById('collapseAll').addEventListener('click', function () {
      Array.prototype.forEach.call(document.querySelectorAll('.rows'), function (r) { r.classList.remove('open'); });
      Array.prototype.forEach.call(document.querySelectorAll('.spine.is-open'), function (s) { s.classList.remove('is-open'); });
    });

    /* ── 深链：#node / #<bundle_id> → 定位并展开对应书脊 ──
       #node 特指 A2A 交接链路（bundle_id = a2a-node），见 sync/sync_a2a.py */
    function focusHash() {
      var h = (location.hash || '').replace(/^#/, '').trim();
      if (!h) return;
      var bid = (h === 'node') ? 'a2a-node' : h;
      var el = document.getElementById('bundle-' + bid);
      if (!el) return;
      var rows = el.querySelector('.rows');
      if (rows) rows.classList.add('open');
      el.classList.add('is-open');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    focusHash();
    window.addEventListener('hashchange', focusHash);
  });
})();
