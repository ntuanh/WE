/* =========================================================
   Hiệu ứng thời tiết — tuyết, mưa, giông, nắng, hoa anh đào, đom đóm
   Vẽ trên một canvas nằm giữa video nền và nội dung, nên không che chữ
   và không ăn click. Lựa chọn được nhớ trong localStorage.
   ========================================================= */
(function () {
  'use strict';

  var KEY = 'we-fx';
  var TAU = Math.PI * 2;

  var MODES = [
    { id: 'auto',      icon: '🌤️', label: 'Tự động' },
    { id: 'sunny',     icon: '☀️', label: 'Nắng' },
    { id: 'rain',      icon: '🌧️', label: 'Mưa' },
    { id: 'storm',     icon: '⛈️', label: 'Giông' },
    { id: 'snow',      icon: '❄️', label: 'Tuyết' },
    { id: 'sakura',    icon: '🌸', label: 'Hoa anh đào' },
    { id: 'fireflies', icon: '✨', label: 'Đom đóm' },
    { id: 'off',       icon: '🚫', label: 'Tắt' }
  ];

  function modeById(id) {
    for (var i = 0; i < MODES.length; i++) if (MODES[i].id === id) return MODES[i];
    return null;
  }

  // "Tự động" theo giờ và mùa: tối thì đom đóm, còn lại theo tháng.
  function autoMode(d) {
    var h = d.getHours(), m = d.getMonth();
    if (h >= 19 || h < 5) return 'fireflies';
    if (m === 11 || m <= 1) return 'snow';
    if (m === 2 || m === 3) return 'sakura';
    if (m >= 5 && m <= 8) return 'rain';
    return 'sunny';
  }

  function load() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function save(v) {
    try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ }
  }

  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var choice = modeById(load()) ? load() : (reduced ? 'off' : 'auto');

  // ---------- canvas ----------
  var canvas = document.createElement('canvas');
  canvas.id = 'fx-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  var overlay = document.querySelector('.overlay');
  if (overlay) overlay.after(canvas); else document.body.prepend(canvas);

  var ctx = canvas.getContext('2d');
  var W = 0, H = 0, dpr = 1;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
  }

  function rand(a, b) { return a + Math.random() * (b - a); }

  // Số hạt theo diện tích màn hình, để điện thoại không bị dày đặc.
  function count(base) {
    var k = (W * H) / (1280 * 800);
    return Math.round(Math.max(base * 0.35, Math.min(base * 1.6, base * k)));
  }

  // Sprite tròn mờ vẽ sẵn một lần — drawImage nhanh hơn tạo gradient mỗi hạt.
  function glowSprite(size, stops) {
    var c = document.createElement('canvas');
    c.width = c.height = size;
    var g = c.getContext('2d');
    var grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    stops.forEach(function (s) { grad.addColorStop(s[0], s[1]); });
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    return c;
  }

  var FLAKE = glowSprite(32, [[0, 'rgba(255,255,255,1)'], [0.35, 'rgba(255,255,255,0.85)'], [1, 'rgba(255,255,255,0)']]);
  var MOTE = glowSprite(32, [[0, 'rgba(255,244,210,1)'], [0.3, 'rgba(255,214,140,0.6)'], [1, 'rgba(255,200,120,0)']]);
  var FLY = glowSprite(64, [[0, 'rgba(250,255,200,1)'], [0.12, 'rgba(230,255,140,0.9)'], [0.4, 'rgba(190,240,90,0.25)'], [1, 'rgba(160,220,60,0)']]);

  // ---------- hiệu ứng ----------
  // Mỗi hiệu ứng là một hàm tạo, trả về hàm tick(dt) vẽ một khung hình.

  function snow() {
    var flakes = [], n = count(140), t = 0;

    function flake(anywhere) {
      var r = rand(0.8, 3.8);
      return {
        x: rand(0, W), y: anywhere ? rand(-20, H) : rand(-40, -8), r: r,
        vy: 16 + r * 13, phase: rand(0, TAU), sway: rand(0.4, 1.3),
        amp: rand(0.3, 1.2) * r * 6, a: rand(0.55, 0.95)
      };
    }
    for (var i = 0; i < n; i++) flakes.push(flake(true));

    return function (dt) {
      t += dt;
      var wind = Math.sin(t * 0.15) * 14 + 6;
      for (var i = 0; i < flakes.length; i++) {
        var f = flakes[i];
        f.y += f.vy * dt;
        f.x += wind * dt * (f.r / 2.5);
        f.phase += f.sway * dt;
        if (f.y > H + 12) flakes[i] = f = flake(false);
        if (f.x > W + 20) f.x -= W + 40; else if (f.x < -20) f.x += W + 40;

        var x = f.x + Math.sin(f.phase) * f.amp, s = f.r * 4;
        ctx.globalAlpha = f.a;
        ctx.drawImage(FLAKE, x - s / 2, f.y - s / 2, s, s);
      }
      ctx.globalAlpha = 1;
    };
  }

  function rain(storm) {
    var drops = [], splashes = [];
    var n = count(storm ? 340 : 190);
    var wind = storm ? 240 : 80;
    var flash = 0, bolt = null, nextBolt = rand(2, 6), echo = 0;

    function drop(anywhere) {
      var z = rand(0.45, 1);
      return {
        x: rand(-wind * 0.6, W), y: anywhere ? rand(-H, H) : rand(-120, -20),
        z: z, len: rand(12, 22) * z, vy: rand(850, 1150) * z
      };
    }
    for (var i = 0; i < n; i++) drops.push(drop(true));

    function makeBolt() {
      var segs = [], x = rand(W * 0.15, W * 0.85), y = 0;
      var path = [[x, y]];
      while (y < H * rand(0.55, 0.85)) {
        x += rand(-38, 38);
        y += rand(18, 42);
        path.push([x, y]);
        if (Math.random() < 0.12) {
          var bx = x, by = y, branch = [[bx, by]];
          for (var k = 0; k < 5; k++) { bx += rand(-30, 30) + (Math.random() < 0.5 ? -14 : 14); by += rand(14, 30); branch.push([bx, by]); }
          segs.push(branch);
        }
      }
      segs.unshift(path);
      return segs;
    }

    function strokePath(p) {
      ctx.moveTo(p[0][0], p[0][1]);
      for (var i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]);
    }

    return function (dt) {
      // Bầu trời sẫm lại một chút khi mưa
      ctx.fillStyle = storm ? 'rgba(18,24,40,0.28)' : 'rgba(30,40,60,0.12)';
      ctx.fillRect(0, 0, W, H);

      for (var i = 0; i < drops.length; i++) {
        var d = drops[i];
        d.x += wind * d.z * dt;
        d.y += d.vy * dt;
        if (d.y > H) {
          // Chỉ giọt ở lớp gần mới bắn tung toé
          if (d.z > 0.75 && Math.random() < 0.5) {
            for (var s = 0; s < 3; s++) {
              splashes.push({ x: d.x, y: H - rand(0, 4), vx: rand(-70, 70) + wind * 0.2, vy: rand(-200, -80), life: rand(0.25, 0.45) });
            }
          }
          drops[i] = drop(false);
        }
      }

      // Hai lớp: xa (mảnh, nhạt) và gần (dày, rõ) — mỗi lớp một lần stroke
      ctx.lineCap = 'round';
      for (var layer = 0; layer < 2; layer++) {
        ctx.beginPath();
        for (var j = 0; j < drops.length; j++) {
          var dr = drops[j];
          if ((dr.z > 0.75) !== !!layer) continue;
          var k = dr.len / dr.vy;
          ctx.moveTo(dr.x, dr.y);
          ctx.lineTo(dr.x - wind * dr.z * k, dr.y - dr.len);
        }
        ctx.lineWidth = layer ? 1.3 : 0.9;
        ctx.strokeStyle = layer ? 'rgba(210,225,255,0.55)' : 'rgba(190,210,245,0.32)';
        ctx.stroke();
      }

      ctx.fillStyle = 'rgba(215,230,255,0.6)';
      for (var p = splashes.length - 1; p >= 0; p--) {
        var sp = splashes[p];
        sp.life -= dt;
        if (sp.life <= 0) { splashes.splice(p, 1); continue; }
        sp.vy += 900 * dt;
        sp.x += sp.vx * dt;
        sp.y += sp.vy * dt;
        ctx.beginPath();
        ctx.arc(sp.x, sp.y, 1.2, 0, TAU);
        ctx.fill();
      }

      if (!storm) return;

      nextBolt -= dt;
      if (nextBolt <= 0) {
        flash = 1;
        bolt = makeBolt();
        nextBolt = rand(5, 11);
        echo = Math.random() < 0.6 ? rand(0.12, 0.25) : 0;
      }
      if (echo > 0) {
        echo -= dt;
        if (echo <= 0) flash = Math.max(flash, 0.8);
      }
      if (flash > 0) {
        ctx.fillStyle = 'rgba(225,232,255,' + (flash * 0.32) + ')';
        ctx.fillRect(0, 0, W, H);
        if (bolt) {
          ctx.save();
          ctx.shadowColor = 'rgba(190,210,255,0.9)';
          ctx.shadowBlur = 18;
          ctx.strokeStyle = 'rgba(255,255,255,' + flash + ')';
          ctx.lineJoin = 'round';
          ctx.beginPath(); strokePath(bolt[0]); ctx.lineWidth = 2.4; ctx.stroke();
          ctx.beginPath();
          for (var b = 1; b < bolt.length; b++) strokePath(bolt[b]);
          ctx.lineWidth = 1.2; ctx.stroke();
          ctx.restore();
        }
        flash -= dt * 2.6;
        if (flash <= 0) { flash = 0; if (echo <= 0) bolt = null; }
      }
    };
  }

  function sunny() {
    var motes = [], n = count(55), t = 0;

    function mote(anywhere) {
      return {
        x: rand(0, W), y: anywhere ? rand(0, H) : H + 10, r: rand(2, 6),
        vy: rand(-14, -5), vx: rand(-6, 6), phase: rand(0, TAU), rate: rand(0.6, 1.6)
      };
    }
    for (var i = 0; i < n; i++) motes.push(mote(true));

    function rays(cx, cy, len, num, spin, width) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(spin);
      ctx.beginPath();
      for (var i = 0; i < num; i++) {
        var a = (i / num) * TAU;
        ctx.moveTo(0, 0);
        ctx.lineTo(Math.cos(a - width) * len, Math.sin(a - width) * len);
        ctx.lineTo(Math.cos(a + width) * len, Math.sin(a + width) * len);
        ctx.closePath();
      }
      ctx.fill();
      ctx.restore();
    }

    return function (dt) {
      t += dt;
      var sx = W * 0.86, sy = H * 0.06;
      var R = Math.max(W, H) * 1.05;

      ctx.globalCompositeOperation = 'lighter';

      var glow = ctx.createRadialGradient(sx, sy, 0, sx, sy, R * 0.75);
      glow.addColorStop(0, 'rgba(255,222,150,0.42)');
      glow.addColorStop(0.35, 'rgba(255,190,110,0.12)');
      glow.addColorStop(1, 'rgba(255,170,90,0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, W, H);

      var rg = ctx.createRadialGradient(sx, sy, 0, sx, sy, R);
      rg.addColorStop(0, 'rgba(255,236,190,' + (0.16 + Math.sin(t * 0.7) * 0.03) + ')');
      rg.addColorStop(1, 'rgba(255,220,160,0)');
      ctx.fillStyle = rg;
      rays(sx, sy, R, 14, t * 0.035, 0.05);
      rays(sx, sy, R * 0.8, 9, -t * 0.025 + 0.4, 0.035);

      var core = ctx.createRadialGradient(sx, sy, 0, sx, sy, 90);
      core.addColorStop(0, 'rgba(255,253,240,0.95)');
      core.addColorStop(0.4, 'rgba(255,236,190,0.45)');
      core.addColorStop(1, 'rgba(255,220,160,0)');
      ctx.fillStyle = core;
      ctx.fillRect(sx - 90, sy - 90, 180, 180);

      // Lóa ống kính dọc theo đường từ mặt trời qua tâm màn hình
      var fx = W / 2 - sx, fy = H / 2 - sy, wob = Math.sin(t * 0.4) * 0.02;
      [[0.55, 26, 'rgba(255,200,140,0.10)'], [0.85, 12, 'rgba(180,230,255,0.12)'],
       [1.15, 46, 'rgba(255,170,200,0.07)'], [1.45, 18, 'rgba(255,230,160,0.10)']].forEach(function (f) {
        ctx.fillStyle = f[2];
        ctx.beginPath();
        ctx.arc(sx + fx * (f[0] + wob), sy + fy * (f[0] + wob), f[1], 0, TAU);
        ctx.fill();
      });

      for (var i = 0; i < motes.length; i++) {
        var m = motes[i];
        m.phase += m.rate * dt;
        m.x += (m.vx + Math.sin(m.phase) * 6) * dt;
        m.y += m.vy * dt;
        if (m.y < -10) motes[i] = m = mote(false);
        var s = m.r * 3;
        ctx.globalAlpha = 0.35 + 0.35 * Math.sin(m.phase * 1.3);
        ctx.drawImage(MOTE, m.x - s / 2, m.y - s / 2, s, s);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    };
  }

  function sakura() {
    var petals = [], n = count(46);
    var COLORS = ['#ffd1dc', '#ffb7c9', '#fbc4d4', '#ffe0e8', '#f7a8bf'];

    function petal(anywhere) {
      var fromLeft = !anywhere && Math.random() < 0.3;
      return {
        x: anywhere ? rand(0, W) : (fromLeft ? -20 : rand(-W * 0.2, W)),
        y: anywhere ? rand(0, H) : (fromLeft ? rand(0, H * 0.6) : -20),
        s: rand(5, 11), vy: rand(28, 60), vx: rand(25, 65),
        rot: rand(0, TAU), vrot: rand(-1.8, 1.8),
        flip: rand(0, TAU), vflip: rand(1.5, 3.6),
        phase: rand(0, TAU), c: COLORS[(Math.random() * COLORS.length) | 0]
      };
    }
    for (var i = 0; i < n; i++) petals.push(petal(true));

    return function (dt) {
      for (var i = 0; i < petals.length; i++) {
        var p = petals[i];
        p.phase += dt;
        p.x += (p.vx + Math.sin(p.phase * 1.4) * 22) * dt;
        p.y += p.vy * dt;
        p.rot += p.vrot * dt;
        p.flip += p.vflip * dt;
        if (p.y > H + 24 || p.x > W + 24) petals[i] = p = petal(false);

        var s = p.s;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.scale(1, 0.25 + Math.abs(Math.cos(p.flip)) * 0.75);
        ctx.globalAlpha = 0.88;
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.moveTo(0, s);
        ctx.bezierCurveTo(s * 0.95, s * 0.55, s * 0.75, -s * 0.75, s * 0.18, -s);
        ctx.lineTo(0, -s * 0.72);
        ctx.lineTo(-s * 0.18, -s);
        ctx.bezierCurveTo(-s * 0.75, -s * 0.75, -s * 0.95, s * 0.55, 0, s);
        ctx.fill();
        ctx.restore();
      }
      ctx.globalAlpha = 1;
    };
  }

  function fireflies() {
    var flies = [], n = count(30);

    function fly() {
      return {
        x: rand(0, W), y: rand(H * 0.25, H), ang: rand(0, TAU), speed: rand(12, 30),
        phase: rand(0, TAU), rate: rand(0.7, 1.7), r: rand(14, 26)
      };
    }
    for (var i = 0; i < n; i++) flies.push(fly());

    return function (dt) {
      ctx.fillStyle = 'rgba(12,18,48,0.22)';
      ctx.fillRect(0, 0, W, H);

      ctx.globalCompositeOperation = 'lighter';
      for (var i = 0; i < flies.length; i++) {
        var f = flies[i];
        f.ang += rand(-2.2, 2.2) * dt;
        f.x += Math.cos(f.ang) * f.speed * dt;
        f.y += Math.sin(f.ang) * f.speed * dt;
        f.phase += f.rate * dt;
        if (f.x < -30) f.x = W + 30; else if (f.x > W + 30) f.x = -30;
        if (f.y < H * 0.1) f.ang = Math.abs(f.ang) % Math.PI;
        else if (f.y > H + 20) f.ang = -Math.abs(f.ang) % Math.PI;

        var glow = Math.max(0, Math.sin(f.phase));
        ctx.globalAlpha = 0.15 + glow * glow * 0.85;
        var s = f.r * 2;
        ctx.drawImage(FLY, f.x - s / 2, f.y - s / 2, s, s);
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    };
  }

  var EFFECTS = {
    snow: snow,
    rain: function () { return rain(false); },
    storm: function () { return rain(true); },
    sunny: sunny,
    sakura: sakura,
    fireflies: fireflies
  };

  // ---------- vòng lặp ----------
  var active = null, tick = null, raf = 0, last = 0;

  function effective() { return choice === 'auto' ? autoMode(new Date()) : choice; }

  function start() {
    cancelAnimationFrame(raf);
    raf = 0;
    active = effective();
    resize();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    tick = EFFECTS[active] ? EFFECTS[active]() : null;
    canvas.classList.toggle('on', !!tick);
    if (tick && !document.hidden) { last = 0; raf = requestAnimationFrame(frame); }
    updateButton();
  }

  function frame(now) {
    var dt = last ? Math.min((now - last) / 1000, 0.05) : 0.016;
    last = now;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    tick(dt);
    raf = requestAnimationFrame(frame);
  }

  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { cancelAnimationFrame(raf); raf = 0; }
    else if (tick && !raf) { last = 0; raf = requestAnimationFrame(frame); }
  });

  var resizeTimer = 0;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(start, 200);
  });

  // "Tự động" đổi hiệu ứng khi qua giờ/mùa mà không cần tải lại trang.
  setInterval(function () {
    if (choice === 'auto' && autoMode(new Date()) !== active) start();
  }, 5 * 60 * 1000);

  // ---------- nút chọn ----------
  var wrap = document.createElement('div');
  wrap.className = 'fx-picker';
  wrap.innerHTML =
    '<div class="fx-menu" role="menu" hidden></div>' +
    '<button type="button" class="fx-toggle" aria-haspopup="true" aria-expanded="false" title="Hiệu ứng thời tiết"></button>';
  document.body.appendChild(wrap);

  var btn = wrap.querySelector('.fx-toggle');
  var menu = wrap.querySelector('.fx-menu');

  MODES.forEach(function (m) {
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'menuitemradio');
    b.dataset.mode = m.id;
    b.innerHTML = '<span class="fx-ico">' + m.icon + '</span><span>' + m.label + '</span>';
    b.addEventListener('click', function () {
      choice = m.id;
      save(choice);
      start();
      setOpen(false);
      btn.focus();
    });
    menu.appendChild(b);
  });

  function updateButton() {
    var shown = modeById(active) || modeById(choice);
    btn.textContent = shown.icon;
    btn.setAttribute('aria-label', 'Hiệu ứng: ' + modeById(choice).label +
      (choice === 'auto' ? ' (' + shown.label + ')' : ''));
    menu.querySelectorAll('button').forEach(function (b) {
      var on = b.dataset.mode === choice;
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.classList.toggle('on', on);
    });
    var autoBtn = menu.querySelector('[data-mode="auto"] span:last-child');
    if (autoBtn) autoBtn.textContent = 'Tự động · ' + modeById(autoMode(new Date())).label;
  }

  function setOpen(open) {
    menu.hidden = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    wrap.classList.toggle('open', open);
  }

  btn.addEventListener('click', function () { setOpen(menu.hidden); });
  document.addEventListener('click', function (e) { if (!wrap.contains(e.target)) setOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { setOpen(false); btn.focus(); } });

  start();
})();
