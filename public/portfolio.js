/* Gianni Arone — shared behaviour: nav, reveal, video modal, site micropages, art lightbox, lazy loops */
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
  function fmtDur(s) { s = Math.round(s || 0); var m = Math.floor(s / 60), r = s % 60; return m + ':' + (r < 10 ? '0' : '') + r; }
  function esc(str) { return String(str == null ? '' : str).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function el(html) { var t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; }
  function getJSON(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }); }
  var CAT_LABEL = { reels: 'Reel', spots: 'Spot', entertainment: 'Entertainment', music: 'Music video', art: 'Art' };
  function playerUrl(id, autoplay) { return 'https://player.vimeo.com/video/' + id + '?title=0&byline=0&portrait=0&dnt=1' + (autoplay ? '&autoplay=1' : ''); }
  function lockScroll(on) { document.documentElement.style.overflow = on ? 'hidden' : ''; }

  // ── Reveal on scroll ──
  var revealIO = ('IntersectionObserver' in window) ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); revealIO.unobserve(e.target); } });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 }) : null;
  function observeReveals(root) {
    (root || document).querySelectorAll('.reveal:not(.in)').forEach(function (n) { revealIO ? revealIO.observe(n) : n.classList.add('in'); });
  }

  // ── Lazy media (videos/images with data-src) ──
  // Loads a clip the first time it comes near the viewport and plays it while at least a
  // quarter of it is visible. Play/pause only fire on a real state change, so nothing churns.
  var lazyIO = ('IntersectionObserver' in window) ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var n = e.target;
      if (e.isIntersecting) {
        if (n.dataset.src && !n.src) {
          n.src = n.dataset.src;
          if (n.tagName === 'VIDEO') { n.addEventListener('error', function () { videoFailed(n); }); n.load(); }
        }
        if (n.tagName === 'VIDEO' && n.paused) { var p = n.play(); if (p && p.catch) p.catch(function () {}); }
      } else if (n.tagName === 'VIDEO' && !n.paused && !n.closest('.marquee')) { n.pause(); }
    });
  }, { rootMargin: '200px 0px', threshold: 0.25 }) : null;
  function observeLazy(root) {
    (root || document).querySelectorAll('video[data-src], img[data-src]').forEach(function (n) {
      if (lazyIO) lazyIO.observe(n); else { n.src = n.dataset.src; }
    });
  }
  // A looping clip. MP4 first (smallest, plays everywhere that matters), WebM as a
  // fallback for browsers built without H.264, and finally a still/animated image if
  // neither decodes. `alt` is an image URL used for that last fallback.
  function loopHTML(src, poster, cls, alt) {
    var webm = /\.mp4$/.test(src) && src.indexOf('giphy.com') < 0 ? src.replace(/\.mp4$/, '.webm') : null;
    return '<video class="' + (cls || '') + '" muted loop playsinline preload="none" data-src="' + esc(src) + '"' +
      (webm ? ' data-webm="' + esc(webm) + '"' : '') +
      (alt ? ' data-fallback="' + esc(alt) + '"' : '') +
      (poster ? ' poster="' + esc(poster) + '"' : '') + '></video>';
  }
  function videoFailed(v) {
    if (v.dataset.webm && v.src !== v.dataset.webm) { v.src = v.dataset.webm; v.load(); var p = v.play(); if (p && p.catch) p.catch(function () {}); return; }
    var alt = v.dataset.fallback || v.poster;
    if (alt) { var img = document.createElement('img'); img.src = alt; img.alt = ''; img.loading = 'lazy'; if (v.className) img.className = v.className; if (v.parentNode) v.parentNode.replaceChild(img, v); }
  }

  // ── Video data + cards ──
  var vcache = null;
  function loadVideos() { if (vcache) return Promise.resolve(vcache); return getJSON('/videos.json').then(function (d) { vcache = d; return d; }); }
  var playlist = [];
  function vcard(v, extraClass) {
    var year = (v.date || '').slice(0, 4);
    var thumb = v.thumb || v.remoteThumb;
    var a = document.createElement('a');
    a.className = 'tile vcard reveal ' + (extraClass || '');
    a.href = v.url; a.dataset.id = v.id; a.dataset.category = v.category;
    if (!v.embeddable) { a.target = '_blank'; a.rel = 'noopener'; }
    a.innerHTML =
      '<div class="media"><img loading="lazy" decoding="async" src="' + esc(thumb) + '" alt="">' +
        '<div class="play"><div class="playbtn">&#9654;</div></div>' +
        '<span class="dur">' + fmtDur(v.duration) + '</span>' +
        (v.embeddable ? '' : '<span class="badge right white">Vimeo ↗</span>') +
      '</div>' +
      '<div class="body"><div class="meta">' + esc(CAT_LABEL[v.category] || v.category) + (year ? ' · ' + year : '') + '</div>' +
        '<h3>' + esc(v.title) + '</h3>' +
        (v.description ? '<div class="desc">' + esc(v.description.split('\n')[0]) + '</div>' : '') + '</div>';
    a.addEventListener('click', function (e) { if (!v.embeddable) return; e.preventDefault(); openVideo(v); });
    return a;
  }

  // ── Video modal ──
  var modal, frame, mtitle, mprev, mnext, current;
  function ensureModal() {
    if (modal) return;
    modal = el('<div class="modal" role="dialog" aria-modal="true"><button class="close" aria-label="Close">×</button><div class="frame"></div><div class="m-bar"><div class="m-title"></div><div class="m-nav"><button class="prev">← Prev</button><button class="next">Next →</button></div></div></div>');
    document.body.appendChild(modal);
    frame = modal.querySelector('.frame'); mtitle = modal.querySelector('.m-title');
    mprev = modal.querySelector('.prev'); mnext = modal.querySelector('.next');
    modal.querySelector('.close').addEventListener('click', closeVideo);
    modal.addEventListener('click', function (e) { if (e.target === modal) closeVideo(); });
    mprev.addEventListener('click', function () { step(-1); }); mnext.addEventListener('click', function () { step(1); });
    document.addEventListener('keydown', function (e) {
      if (!modal.classList.contains('open')) return;
      if (e.key === 'Escape') closeVideo(); if (e.key === 'ArrowRight') step(1); if (e.key === 'ArrowLeft') step(-1);
    });
  }
  function embeddableList() { return (vcache ? vcache.videos : []).filter(function (v) { return v.embeddable; }); }
  function step(dir) {
    var list = playlist.length ? playlist : embeddableList();
    var i = list.findIndex(function (v) { return v.id === current.id; });
    if (i < 0) return; var n = list[(i + dir + list.length) % list.length]; openVideo(n);
  }
  function openVideo(v) {
    ensureModal(); current = v;
    frame.innerHTML = '<iframe src="' + playerUrl(v.id, true) + '" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="' + esc(v.title) + '"></iframe>';
    mtitle.innerHTML = esc(v.title) + '<a href="' + esc(v.url) + '" target="_blank" rel="noopener">Vimeo ↗</a>';
    var many = (playlist.length ? playlist : embeddableList()).length > 1;
    mprev.style.display = mnext.style.display = many ? '' : 'none';
    modal.classList.add('open'); lockScroll(true);
  }
  function closeVideo() { if (!modal) return; modal.classList.remove('open'); frame.innerHTML = ''; lockScroll(false); }
  function setPlaylist(list) { playlist = list.filter(function (v) { return v.embeddable; }); }

  // Inline hero player (click-to-play poster)
  function bindPlayers(root) {
    (root || document).querySelectorAll('.player[data-vimeo]').forEach(function (p) {
      var go = function () { p.innerHTML = '<iframe src="' + playerUrl(p.dataset.vimeo, true) + '" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen title="Video"></iframe>'; };
      p.addEventListener('click', go, { once: true });
      p.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    });
  }

  // ── Sites: cards + micropage ──
  var scache = null;
  function loadSites() { if (scache) return Promise.resolve(scache); return getJSON('/sites.json').then(function (d) { scache = d.sites; return scache; }); }
  function scard(s, feature) {
    var a = document.createElement('a');
    a.className = 'tile scard reveal' + (feature ? ' sfeature' : '');
    a.href = s.url; a.target = '_blank'; a.rel = 'noopener'; a.dataset.site = s.id;
    a.innerHTML =
      '<div class="media"><img loading="lazy" decoding="async" src="' + esc(s.shot) + '" alt="' + esc(s.name) + '">' +
        (s.pendingDomain ? '<span class="badge">Custom domain soon</span>' : '') +
        '<span class="btn sm yellow open">Open micro-page ↗</span></div>' +
      '<div class="body"><div class="row"><h3>' + esc(s.name) + '</h3><span class="domain">' + esc(s.domain) + '</span></div>' +
        '<div class="meta">' + esc(s.role) + (s.client ? ' · ' + esc(s.client) : '') + ' · ' + esc(s.year) + '</div>' +
        '<p class="desc">' + esc(s.tagline) + ' ' + esc(s.description.split('. ')[0]) + '.</p>' +
        '<div class="chips">' + s.tags.slice(0, 4).map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('') + '</div></div>';
    a.addEventListener('click', function (e) { e.preventDefault(); openSite(s.id); });
    return a;
  }
  var micro, mcur;
  function ensureMicro() {
    if (micro) return;
    micro = el('<div class="micro" role="dialog" aria-modal="true"><div class="sheet"><button class="close" aria-label="Close">×</button><button class="step prev" aria-label="Previous site">←</button><button class="step next" aria-label="Next site">→</button><div class="info"></div><div class="stage"></div></div></div>');
    document.body.appendChild(micro);
    micro.querySelector('.close').addEventListener('click', closeSite);
    micro.addEventListener('click', function (e) { if (e.target === micro) closeSite(); });
    micro.querySelector('.prev').addEventListener('click', function () { stepSite(-1); });
    micro.querySelector('.next').addEventListener('click', function () { stepSite(1); });
    document.addEventListener('keydown', function (e) {
      if (!micro.classList.contains('open')) return;
      if (e.key === 'Escape') closeSite(); if (e.key === 'ArrowRight') stepSite(1); if (e.key === 'ArrowLeft') stepSite(-1);
    });
  }
  function stepSite(dir) { var i = scache.findIndex(function (s) { return s.id === mcur; }); openSite(scache[(i + dir + scache.length) % scache.length].id); }
  function openSite(id) {
    loadSites().then(function (sites) {
      var s = sites.find(function (x) { return x.id === id; }); if (!s) return;
      ensureMicro(); mcur = id;
      var sheet = micro.querySelector('.sheet'); sheet.style.setProperty('--accent', s.accent || '#ff3f8e');
      micro.querySelector('.info').innerHTML =
        '<div class="meta">' + esc(s.role) + (s.client ? ' · ' + esc(s.client) : '') + ' · ' + esc(s.year) + '</div>' +
        '<h2>' + esc(s.name) + '</h2>' +
        '<div class="tag">' + esc(s.tagline) + '</div>' +
        '<p class="desc">' + esc(s.description) + '</p>' +
        '<div class="chips">' + s.tags.map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('') + '</div>' +
        '<div class="actions"><a class="btn primary" href="' + esc(s.url) + '" target="_blank" rel="noopener">Visit ' + esc(s.domain) + ' ↗</a>' +
        (s.pendingDomain ? '<span class="btn sm yellow">Custom domain coming soon</span>' : '') + '</div>' +
        '<div class="actions m-nav"><button class="btn sm" data-step="-1">← Prev site</button><button class="btn sm" data-step="1">Next site →</button>' +
        '<span class="meta" style="align-self:center">' + (sites.indexOf(s) + 1) + ' / ' + sites.length + '</span></div>';
      micro.querySelectorAll('.info [data-step]').forEach(function (b) { b.addEventListener('click', function () { stepSite(+b.dataset.step); }); });
      micro.querySelector('.stage').innerHTML =
        '<div class="browser"><div class="bar"><i></i><i></i><i></i><span class="url">' + esc(s.domain) + '</span></div>' +
        '<div class="scroller"><img src="' + esc(s.full || s.shot) + '" alt="' + esc(s.name) + ' full page"></div><div class="hint">Scroll the page ↓</div></div>' +
        (s.mobile ? '<div class="phone"><img src="' + esc(s.mobile) + '" alt=""></div>' : '');
      micro.classList.add('open'); lockScroll(true);
      sheet.scrollTop = 0;
      var scroller = micro.querySelector('.browser .scroller');
      if (scroller) scroller.addEventListener('scroll', function () { scroller.parentNode.classList.add('scrolled'); }, { once: true, passive: true });
      if (history.replaceState) history.replaceState(null, '', '#site=' + id);
    });
  }
  function closeSite() { if (!micro) return; micro.classList.remove('open'); lockScroll(false); if (history.replaceState && /#site=/.test(location.hash)) history.replaceState(null, '', location.pathname); }
  function openFromHash() { var m = location.hash.match(/#site=([\w-]+)/); if (m) openSite(m[1]); }

  // ── Art lightbox ──
  var lb, lbList = [], lbIdx = 0;
  function ensureLb() {
    if (lb) return;
    lb = el('<div class="lb" role="dialog" aria-modal="true"><button class="close" aria-label="Close">×</button><button class="step prev" aria-label="Previous">←</button><button class="step next" aria-label="Next">→</button><div class="inner"></div></div>');
    document.body.appendChild(lb);
    lb.querySelector('.close').addEventListener('click', closeLb);
    lb.addEventListener('click', function (e) { if (e.target === lb || e.target.classList.contains('inner')) closeLb(); });
    lb.querySelector('.prev').addEventListener('click', function () { showLb(lbIdx - 1); });
    lb.querySelector('.next').addEventListener('click', function () { showLb(lbIdx + 1); });
    document.addEventListener('keydown', function (e) {
      if (!lb.classList.contains('open')) return;
      if (e.key === 'Escape') closeLb(); if (e.key === 'ArrowRight') showLb(lbIdx + 1); if (e.key === 'ArrowLeft') showLb(lbIdx - 1);
    });
  }
  function openLb(list, idx) { ensureLb(); lbList = list; showLb(idx); lb.classList.add('open'); lockScroll(true); }
  function showLb(i) {
    lbIdx = (i + lbList.length) % lbList.length; var it = lbList[lbIdx];
    var media = it.type === 'loop'
      ? '<video poster="' + esc(it.poster || '') + '" autoplay muted loop playsinline onerror="this.dispatchEvent(new Event(\'lbfail\'))">' +
          '<source src="' + esc(it.src) + '" type="video/mp4">' +
          '<source src="' + esc(it.src.replace(/\.mp4$/, '.webm')) + '" type="video/webm">' +
        '</video>'
      : '<img src="' + esc(it.src) + '" alt="' + esc(it.title || '') + '">';
    lb.querySelector('.inner').innerHTML = media + '<div class="cap">' + (it.title ? '<span>' + esc(it.title) + '</span>' : '') + (it.sub ? '<small>' + esc(it.sub) + '</small>' : '') + (it.url ? '<a href="' + esc(it.url) + '" target="_blank" rel="noopener">' + esc(it.linkLabel || 'Open ↗') + '</a>' : '') + '</div>';
    lb.querySelector('.prev').style.display = lb.querySelector('.next').style.display = lbList.length > 1 ? '' : 'none';
  }
  function closeLb() { if (!lb) return; lb.classList.remove('open'); lb.querySelector('.inner').innerHTML = ''; lockScroll(false); }

  // ── Art data ──
  var acache = null;
  function loadArt() { if (acache) return Promise.resolve(acache); return getJSON('/art.json').then(function (d) { acache = d; return d; }); }
  function giphyMp4(id) { return 'https://media.giphy.com/media/' + id + '/giphy.mp4'; }
  function giphyStill(id) { return 'https://media.giphy.com/media/' + id + '/480w_s.jpg'; }
  function giphyWebp(id) { return 'https://media.giphy.com/media/' + id + '/200w.webp'; }
  // GIPHY clips render as animated WebP images: dozens of animated images are cheap for the
  // browser, dozens of <video> decoders are not, and there is no play/pause state to manage.
  function giphyImg(id, title) { return '<img loading="lazy" decoding="async" src="' + esc(giphyWebp(id)) + '" alt="' + esc(title || '') + '">'; }
  function marqueeFill(track, gifs, count) {
    var picks = gifs.slice(0, count);
    track.innerHTML = picks.map(function (g) { return '<div class="item">' + giphyImg(g.id, g.title) + '</div>'; }).join('');
    startMarquee(track, 70);
  }

  // ── Marquee: frame-driven, snapped to whole device pixels ──
  // A CSS transform animation lands content on fractional pixels every frame, and thin
  // high-contrast edges shimmer there on desktop GPUs. Here the offset is rounded to the
  // device pixel grid, the track is looped by exact width, and it pauses when hidden.
  // Runs regardless of the OS "reduce motion" flag by the owner's choice: the bands are the
  // site's signature and they move slowly. Hover pauses them.
  function startMarquee(track, speed) {
    if (!track) return;
    var base = track.innerHTML;
    // Repeat the base until it covers two viewport widths, then double it for the seamless wrap.
    var guard = 0;
    while (track.scrollWidth < window.innerWidth * 2 && guard++ < 8) track.innerHTML += base;
    track.innerHTML += track.innerHTML;
    var half = 0, x = 0, last = null, paused = false, raf = 0;
    var gap = parseFloat(getComputedStyle(track).gap) || 0;
    function measure() { half = (track.scrollWidth + gap) / 2; }
    measure();
    window.addEventListener('resize', measure);
    var host = track.parentNode;
    if (host && host.classList.contains('marquee')) { host.addEventListener('mouseenter', function () { paused = true; }); host.addEventListener('mouseleave', function () { paused = false; last = null; }); }
    document.addEventListener('visibilitychange', function () { last = null; });
    var dpr = window.devicePixelRatio || 1;
    function frame(t) {
      raf = requestAnimationFrame(frame);
      if (paused || document.hidden) return;
      if (last === null) { last = t; return; }
      var dt = Math.min(64, t - last); last = t;
      x -= speed * dt / 1000;
      if (half && x <= -half) x += half;
      var snapped = Math.round(x * dpr) / dpr;
      track.style.transform = 'translate3d(' + snapped + 'px,0,0)';
    }
    raf = requestAnimationFrame(frame);
    // Images arriving later can change nothing (fixed tiles), but fonts can: re-measure once loaded.
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measure);
  }

  // ── Public API ──
  window.GA = {
    loadVideos: loadVideos, vcard: vcard, openVideo: openVideo, setPlaylist: setPlaylist, fmtDur: fmtDur, esc: esc, CAT_LABEL: CAT_LABEL,
    loadSites: loadSites, scard: scard, openSite: openSite,
    loadArt: loadArt, openLb: openLb, loopHTML: loopHTML, giphyMp4: giphyMp4, giphyStill: giphyStill, giphyWebp: giphyWebp, giphyImg: giphyImg, marqueeFill: marqueeFill, startMarquee: startMarquee,
    observeReveals: observeReveals, observeLazy: observeLazy, bindPlayers: bindPlayers, el: el
  };

  bindPlayers(); observeReveals(); observeLazy();
  // Safety net: anything already on screen (or if the observer never fires) becomes visible.
  function revealVisible() {
    var pending = document.querySelectorAll('.reveal:not(.in)');
    pending.forEach(function (n) { if (n.getBoundingClientRect().top < window.innerHeight * 1.1) n.classList.add('in'); });
    return pending.length;
  }
  var ticking = false, lastRun = 0;
  function onScroll() {
    if (ticking) return; ticking = true;
    requestAnimationFrame(function () { var now = performance.now(); if (now - lastRun > 120) { lastRun = now; revealVisible(); } ticking = false; });
  }
  setTimeout(revealVisible, 1200);
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('beforeprint', function () { document.querySelectorAll('.reveal').forEach(function (n) { n.classList.add('in'); }); });
  window.addEventListener('hashchange', openFromHash);
  if (/#site=/.test(location.hash)) openFromHash();
})();
