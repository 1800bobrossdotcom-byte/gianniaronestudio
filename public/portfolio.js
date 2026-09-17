/* Gianni Arone — shared portfolio behaviour: nav, video cards, Vimeo modal */
(function () {
  'use strict';

  // ── Nav ──
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.querySelector('.nav ul');
  if (toggle && menu) {
    toggle.addEventListener('click', function () { menu.classList.toggle('open'); });
    menu.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { menu.classList.remove('open'); }); });
  }

  // ── Helpers ──
  function fmtDur(s) {
    s = Math.round(s || 0);
    var m = Math.floor(s / 60), r = s % 60;
    return m + ':' + (r < 10 ? '0' : '') + r;
  }
  function esc(str) {
    return String(str == null ? '' : str).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  var CAT_LABEL = { reels: 'Reel', spots: 'Spot', entertainment: 'Entertainment', music: 'Music video', art: 'Art' };

  function playerUrl(id, autoplay) {
    return 'https://player.vimeo.com/video/' + id + '?title=0&byline=0&portrait=0&dnt=1' + (autoplay ? '&autoplay=1' : '');
  }

  // ── Data ──
  var cache = null;
  function loadVideos() {
    if (cache) return Promise.resolve(cache);
    return fetch('/videos.json').then(function (r) {
      if (!r.ok) throw new Error('videos.json ' + r.status);
      return r.json();
    }).then(function (d) { cache = d; return d; });
  }

  // ── Cards ──
  function card(v) {
    var year = (v.date || '').slice(0, 4);
    var thumb = v.thumb || v.remoteThumb;
    var a = document.createElement('a');
    a.className = 'card';
    a.dataset.id = v.id;
    a.dataset.category = v.category;
    a.href = v.url;
    if (v.embeddable) {
      a.dataset.embed = '1';
    } else {
      a.target = '_blank';
      a.rel = 'noopener';
    }
    a.innerHTML =
      '<div class="thumb">' +
        '<img loading="lazy" decoding="async" src="' + esc(thumb) + '" alt="" ' +
          (v.remoteThumb && v.thumb ? 'onerror="this.onerror=null;this.src=\'' + esc(v.remoteThumb) + '\'"' : '') + '>' +
        '<span class="dur">' + fmtDur(v.duration) + '</span>' +
        (v.embeddable ? '' : '<span class="ext">vimeo ↗</span>') +
      '</div>' +
      '<div class="title">' + esc(v.title) + '</div>' +
      '<div class="sub">' + esc(CAT_LABEL[v.category] || v.category) + (year ? ' · ' + year : '') + '</div>' +
      (v.description ? '<div class="desc">' + esc(v.description.split('\n')[0]) + '</div>' : '');
    a.addEventListener('click', function (e) {
      if (!v.embeddable) return; // let the link open Vimeo
      e.preventDefault();
      openModal(v);
    });
    return a;
  }

  // ── Modal ──
  var modal, frame, mtitle;
  function ensureModal() {
    if (modal) return;
    modal = document.createElement('div');
    modal.className = 'modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.innerHTML = '<button class="close" aria-label="Close">&times;</button><div class="frame"></div><div class="m-title"></div>';
    document.body.appendChild(modal);
    frame = modal.querySelector('.frame');
    mtitle = modal.querySelector('.m-title');
    modal.querySelector('.close').addEventListener('click', closeModal);
    modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });
  }
  function openModal(v) {
    ensureModal();
    frame.innerHTML = '<iframe src="' + playerUrl(v.id, true) + '" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="' + esc(v.title) + '"></iframe>';
    mtitle.innerHTML = esc(v.title) + '<a href="' + esc(v.url) + '" target="_blank" rel="noopener">open on vimeo ↗</a>';
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    frame.innerHTML = '';
    document.body.style.overflow = '';
  }

  // ── Inline hero player (click-to-play poster) ──
  function bindPlayers() {
    document.querySelectorAll('.player[data-vimeo]').forEach(function (p) {
      p.addEventListener('click', function () {
        var id = p.dataset.vimeo;
        p.innerHTML = '<iframe src="' + playerUrl(id, true) + '" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="Video"></iframe>';
      }, { once: true });
    });
  }

  // ── Public ──
  window.GA = {
    loadVideos: loadVideos,
    card: card,
    fmtDur: fmtDur,
    esc: esc,
    openModal: openModal,
    CAT_LABEL: CAT_LABEL
  };
  bindPlayers();
})();
