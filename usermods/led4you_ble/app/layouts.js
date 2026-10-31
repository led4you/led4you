/*
 * LED4YOU "See it on your house": a night picture of a tree, a house, a garden or a window with
 * LED strings on it, each zone playing a chosen effect, so people can imagine the result before
 * putting the lights up. Effects are imitated by L4YStudio.sampler (studio.js).
 *
 * L4YLayout.mount(box, opts)
 *   opts.fx        [[id, name, is2D], ...]   effect list
 *   opts.pal       [name, ...]               palette names (index = palette id)
 *   opts.palStops  id -> [pos,r,g,b,...] | null
 *   opts.current   () -> Promise<{fx, col, pal, sx}>   what the lights show now (optional)
 *   opts.send      obj -> Promise   send a WLED state command to the connected lights (optional)
 *   opts.toast     text -> void
 *   opts.zones     () -> [{ id, name, n, strip, from, to }]   the zones (segments) of the connected lights (optional)
 *   opts.zoneRange () -> { min, max }          LED numbers a strip zone can use
 *   opts.saveZone  { id, from, to, name } -> Promise<{ id, changed }>   make / change a strip zone
 */
(function () {
	const h = (tag, attrs, ...kids) => {
		const e = document.createElement(tag);
		for (const k in attrs || {}) {
			if (k === 'class') e.className = attrs[k];
			else if (k.startsWith('on')) e[k] = attrs[k];
			else e.setAttribute(k, attrs[k]);
		}
		kids.flat().forEach(c => e.append(c && c.nodeType ? c : document.createTextNode(c ?? '')));
		return e;
	};
	const fill = el => { const f = () => el.style.setProperty('--p', (100 * (el.value - el.min) / (el.max - el.min)) + '%'); el.addEventListener('input', f); f(); return el; };
	const hex = c => '#' + c.map(v => (v | 0).toString(16).padStart(2, '0')).join('');
	const rgb = s => { const n = parseInt(s.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };

	// ---------- where the LEDs sit (logical picture 800 x 600) ----------
	const along = (pts, n, closed) => {   // n LEDs spread evenly along a path
		const P = closed ? pts.concat([pts[0]]) : pts, seg = [];
		let len = 0;
		for (let i = 1; i < P.length; i++) { const d = Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]); seg.push(d); len += d; }
		const out = [];
		for (let k = 0; k < n; k++) {
			let d = (closed ? k / n : k / Math.max(1, n - 1)) * len, i = 0;
			while (i < seg.length - 1 && d > seg[i]) { d -= seg[i]; i++; }
			const f = seg[i] ? Math.min(1, d / seg[i]) : 0;
			out.push({ x: P[i][0] + (P[i + 1][0] - P[i][0]) * f, y: P[i][1] + (P[i + 1][1] - P[i][1]) * f, z: 1 });
		}
		return out;
	};
	const SH = {
		// a string wound around a cone from the top down; z < 0 is behind the tree
		spiral: (o, n) => Array.from({ length: n }, (_, i) => { const f = i / (n - 1), a = f * o.turns * Math.PI * 2, r = (o.r0 || 0) + f * (o.w / 2 - (o.r0 || 0));
			return { x: o.cx + r * Math.sin(a), y: o.top + f * (o.base - o.top), z: Math.cos(a) }; }),
		// strands from the top of a cone to its base (like a "maypole" tree)
		strands: (o, n) => { const per = Math.max(2, Math.round(n / o.k)), out = [];
			for (let s = 0; s < o.k; s++) { const a = (s / o.k) * Math.PI * 2, z = Math.cos(a), xb = o.cx + Math.sin(a) * o.w / 2;
				for (let j = 0; j < per; j++) { const f = (s & 1 ? per - 1 - j : j) / (per - 1); out.push({ x: o.cx + (xb - o.cx) * f, y: o.top + f * (o.base - o.top), z }); } }
			return out; },
		path: (o, n) => along(o.pts, n, o.closed),
		paths: (o, n) => { const per = Math.round(n / o.list.length); return o.list.flatMap(p => along(p, per, true)); },
		grid: (o, n) => { const out = [];
			for (let r = 0; r < o.rows; r++) for (let c = 0; c < o.cols; c++) out.push({ x: o.x + (o.w * (c + .5)) / o.cols, y: o.y + (o.h * (r + .5)) / o.rows, z: 1 });
			return out; },
		net: (o, n) => o.list.flatMap(e => { const out = [], rows = Math.max(2, Math.round(Math.sqrt(n / o.list.length * e.ry / e.rx)));
			for (let r = 0; r < rows; r++) { const yy = -1 + (2 * (r + .5)) / rows, half = Math.sqrt(Math.max(0, 1 - yy * yy)), cols = Math.max(1, Math.round((n / o.list.length / rows) * half * 1.3));
				for (let c = 0; c < cols; c++) { const xx = -half + (2 * half * (r & 1 ? cols - 1 - c : c) + half) / cols; out.push({ x: e.cx + xx * e.rx * .92, y: e.cy + yy * e.ry * .85, z: 1 }); } }
			return out; }),
		circle: (o, n) => Array.from({ length: n }, (_, i) => { const a = (i / n) * Math.PI * 2 - Math.PI / 2; return { x: o.cx + Math.cos(a) * o.r, y: o.cy + Math.sin(a) * o.r * (o.sy || 1), z: 1 }; }),
		star: (o, n) => along(Array.from({ length: 10 }, (_, i) => { const a = (i / 10) * Math.PI * 2 - Math.PI / 2, r = i & 1 ? o.r * .45 : o.r; return [o.cx + Math.cos(a) * r, o.cy + Math.sin(a) * r]; }), n, true),
		custom: o => o.pts.map(p => ({ x: p[0], y: p[1], z: 1 })),
		stakes: (o, n) => { const out = [], per = Math.max(1, Math.round(n / o.pts.length));
			o.pts.forEach(([x, y, s]) => { for (let j = 0; j < per; j++) { const a = (j / per) * Math.PI * 2; out.push({ x: x + Math.cos(a) * 7 * s, y: y - 10 * s + Math.sin(a) * 4 * s, z: 1 }); } });
			return out; }
	};

	// ---------- background pictures ----------
	const sky = (g, W, H, ground) => {
		const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#060914'); gr.addColorStop(.7, '#0d1428'); gr.addColorStop(1, '#141a2c');
		g.fillStyle = gr; g.fillRect(0, 0, W, H);
		for (let i = 0; i < 70; i++) { const x = (i * 197) % W, y = (i * 113) % (ground * .7); g.fillStyle = 'rgba(255,255,255,' + (.15 + (i % 5) * .08) + ')'; g.fillRect(x, y, 1.6, 1.6); }
		g.fillStyle = '#e8ecff'; g.beginPath(); g.arc(W * .86, H * .13, 22, 0, 7); g.fill();
		g.fillStyle = '#060914'; g.beginPath(); g.arc(W * .86 + 9, H * .13 - 6, 20, 0, 7); g.fill();
		g.fillStyle = '#0b1020'; g.fillRect(0, ground, W, H - ground);
		g.fillStyle = 'rgba(255,255,255,.04)'; g.fillRect(0, ground, W, 3);
	};
	const treeShape = (g, cx, top, base, w, col) => {
		g.fillStyle = col || '#0d2416';
		for (let k = 0; k < 4; k++) { const t = top + (base - top) * k * .22, b = top + (base - top) * (.32 + k * .23), ww = w * (.42 + k * .2);
			g.beginPath(); g.moveTo(cx, t); g.lineTo(cx - ww / 2, b); g.lineTo(cx + ww / 2, b); g.closePath(); g.fill(); }
		g.fillStyle = '#20140c'; g.fillRect(cx - w * .05, base, w * .1, (base - top) * .08);
	};
	const house = (g, x, y, w, hh, roof) => {
		g.fillStyle = '#121828'; g.fillRect(x, y, w, hh);
		g.fillStyle = '#0c1120'; g.beginPath(); g.moveTo(x - 20, y); g.lineTo(x + w / 2, y - roof); g.lineTo(x + w + 20, y); g.closePath(); g.fill();
		g.fillStyle = '#1a2236'; g.fillRect(x + w * .14, y + hh * .2, w * .2, hh * .3); g.fillRect(x + w * .66, y + hh * .2, w * .2, hh * .3);
		g.fillStyle = '#2a2016'; g.fillRect(x + w * .43, y + hh * .45, w * .14, hh * .55);
		g.fillStyle = 'rgba(255,190,110,.10)'; g.fillRect(x + w * .14, y + hh * .2, w * .2, hh * .3);
	};
	const bush = (g, cx, cy, rx, ry) => { g.fillStyle = '#0b1d14'; g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, 7); g.fill(); };

	// ---------- the scenes ----------
	const Z = (name, shape, o, n, look, min, max) => ({ name, shape, o, n, look, min: min || 10, max: max || 600 });
	const SCENES = [
		{ id: 'tree', name: 'Christmas tree', bg: (g, W, H) => { sky(g, W, H, 520); treeShape(g, 400, 90, 500, 340); },
			zones: [Z('Tree', 'spiral', { cx: 400, top: 110, base: 495, w: 330, turns: 9, r0: 8 }, 250, { fx: 'Twinklefox', col: [[255, 30, 0], [0, 200, 40], [255, 170, 60]], pal: 0, sx: 128 }, 30, 600),
				Z('Star', 'star', { cx: 400, cy: 82, r: 32 }, 30, { fx: 'Breathe', col: [[255, 200, 80]], pal: 0, sx: 100 }, 5, 60)] },
		{ id: 'cone', name: 'Strand tree', bg: (g, W, H) => { sky(g, W, H, 520); g.strokeStyle = '#1b2234'; g.lineWidth = 3; g.beginPath(); g.moveTo(400, 80); g.lineTo(400, 515); g.stroke(); },
			zones: [Z('Strands', 'strands', { cx: 400, top: 90, base: 510, w: 380, k: 12 }, 300, { fx: 'Rainbow', col: [[255, 0, 0]], pal: 0, sx: 128 }, 48, 800)] },
		{ id: 'house', name: 'House', bg: (g, W, H) => { sky(g, W, H, 520); house(g, 230, 300, 340, 220, 140); treeShape(g, 680, 270, 505, 150); bush(g, 160, 500, 70, 34); bush(g, 640, 505, 20, 1); },
			zones: [Z('Roofline', 'path', { pts: [[208, 302], [400, 160], [592, 302]] }, 120, { fx: 'Chase', col: [[255, 255, 255], [255, 0, 0]], pal: 0, sx: 110 }),
				Z('Windows', 'paths', { list: [[[278, 344], [346, 344], [346, 410], [278, 410]], [[454, 344], [522, 344], [522, 410], [454, 410]]] }, 80, { fx: 'Solid', col: [[255, 150, 40]], pal: 0, sx: 128 }),
				Z('Door', 'path', { pts: [[376, 520], [376, 399], [424, 399], [424, 520]] }, 40, { fx: 'Candy Cane', col: [[255, 0, 0], [255, 255, 255]], pal: 0, sx: 80 }),
				Z('Bush', 'net', { list: [{ cx: 160, cy: 500, rx: 70, ry: 34 }] }, 60, { fx: 'Twinkle', col: [[60, 120, 255], [0, 0, 0]], pal: 0, sx: 128 }),
				Z('Tree', 'spiral', { cx: 680, top: 285, base: 500, w: 140, turns: 6 }, 100, { fx: 'Colortwinkles', col: [[255, 0, 0]], pal: 0, sx: 128 })] },
		{ id: 'garden', name: 'Garden', bg: (g, W, H) => { sky(g, W, H, 470); bush(g, 150, 470, 90, 46); bush(g, 650, 470, 90, 46); g.fillStyle = '#151b2c'; g.beginPath(); g.moveTo(370, 600); g.lineTo(390, 470); g.lineTo(410, 470); g.lineTo(430, 600); g.fill(); },
			zones: [Z('Arch', 'path', { pts: Array.from({ length: 21 }, (_, i) => { const a = Math.PI - (i / 20) * Math.PI; return [400 + Math.cos(a) * 150, 470 - Math.sin(a) * 210]; }) }, 90, { fx: 'Running', col: [[255, 255, 255], [0, 40, 120]], pal: 0, sx: 128 }),
				Z('Bushes', 'net', { list: [{ cx: 150, cy: 470, rx: 90, ry: 46 }, { cx: 650, cy: 470, rx: 90, ry: 46 }] }, 120, { fx: 'Pacifica', col: [[0, 100, 255]], pal: 0, sx: 128 }),
				Z('Path lights', 'stakes', { pts: [[350, 590, 1.3], [450, 590, 1.3], [362, 540, 1.1], [438, 540, 1.1], [372, 500, .9], [428, 500, .9]] }, 36, { fx: 'Breathe', col: [[255, 120, 20]], pal: 0, sx: 128 }, 6, 120)] },
		{ id: 'window', name: 'Window curtain', bg: (g, W, H) => { g.fillStyle = '#0c0f18'; g.fillRect(0, 0, W, H); g.fillStyle = '#05070d'; g.fillRect(170, 90, 460, 400); g.strokeStyle = '#2a3046'; g.lineWidth = 14; g.strokeRect(170, 90, 460, 400); g.fillStyle = '#1b2030'; g.fillRect(150, 490, 500, 20); },
			zones: [Z('Curtain', 'grid', { x: 190, y: 110, w: 420, h: 360, cols: 24, rows: 20 }, 480, { fx: 'Matrix', col: [[0, 255, 60]], pal: 0, sx: 128 }, 480, 480)] },
		{ id: 'halloween', name: 'Halloween house', bg: (g, W, H) => { sky(g, W, H, 520); house(g, 230, 300, 340, 220, 140); g.fillStyle = '#3a1b05'; g.beginPath(); g.ellipse(680, 485, 62, 46, 0, 0, 7); g.fill(); bush(g, 140, 505, 80, 30); },
			zones: [Z('Roofline', 'path', { pts: [[208, 302], [400, 160], [592, 302]] }, 120, { fx: 'Haunted', col: [[255, 90, 0]], pal: 0, sx: 160 }),
				Z('Windows', 'grid', { x: 278, y: 344, w: 68, h: 66, cols: 8, rows: 8 }, 64, { fx: 'Halloween Eyes', col: [[255, 0, 0], [0, 0, 0]], pal: 0, sx: 128 }, 64, 64),
				Z('Pumpkin', 'circle', { cx: 680, cy: 485, r: 60, sy: .75 }, 40, { fx: 'Candle', col: [[255, 100, 0]], pal: 0, sx: 128 }),
				Z('Bush', 'net', { list: [{ cx: 140, cy: 505, rx: 80, ry: 30 }] }, 60, { fx: 'Colortwinkles', col: [[120, 0, 255]], pal: 5, sx: 128 })] }
	];

	function mount(box, opts) {
		const fxList = opts.fx.slice().sort((a, b) => a[1].localeCompare(b[1]));
		const byName = n => opts.fx.find(f => f[1].toLowerCase() === String(n).toLowerCase());
		// "My lights": the photo and LED positions from the camera scan (scanner.js)
		const scenes = SCENES.slice();
		if (opts.custom && opts.custom.pts) {
			const c = opts.custom, ar = c.ar || 4 / 3, w = ar > 4 / 3 ? 800 : 600 * ar, hh = ar > 4 / 3 ? 800 / ar : 600, x0 = (800 - w) / 2, y0 = (600 - hh) / 2;
			const img = new Image(); if (c.photo) { img.onload = () => { bgCache = null; }; img.src = c.photo; }
			scenes.unshift({ id: 'mine', name: 'My lights', bg: (g, W, H) => {
				g.fillStyle = '#05070d'; g.fillRect(0, 0, W, H);
				if (img.complete && img.naturalWidth) { g.drawImage(img, x0, y0, w, hh); g.fillStyle = 'rgba(0,0,8,.55)'; g.fillRect(0, 0, W, H); }
			}, zones: [Z('My lights', 'custom', { pts: c.pts.map(p => [x0 + p[0] * w, y0 + p[1] * hh]) }, c.n, { fx: 'Rainbow', col: [[255, 0, 0]], pal: 0, sx: 128 }, c.n, c.n)] });
		}
		let sc = scenes[0], zones = [], bgCache = null, sel = 0, selT = -9999;   // the chosen zone stands out for a moment
		const KEY = 'l4yLayout';
		let saved = {}; try { saved = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) {}
		const keep = () => { try { saved[sc.id] = zones.map(z => ({ fx: z.fx, col: z.col, pal: z.pal, sx: z.sx, n: z.n, rz: z.rz != null && z.rz !== 'new' ? z.rz : null })); localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) {} };

		const cv = h('canvas', { class: 'lay-cv', width: '1600', height: '1200', 'aria-label': 'Preview picture' });
		const pick = h('div', { class: 'segs lay-scenes' });
		const tabs = h('div', { class: 'segs lay-zones' });
		const ed = h('div', { class: 'lay-ed' });

		const realZones = () => { try { return opts.zones ? opts.zones() : []; } catch (e) { return []; } };
		// a linked part shows as many LEDs as its real zone (within what the drawing can show)
		const fitReal = z => { const r = realZones().find(q => q.id === z.rz); if (r) z.n = Math.max(z.def.min, Math.min(z.def.max, r.n)); };
		const isLinked = z => z.rz != null && z.rz !== 'new';
		const linkInOrder = () => {
			const real = realZones();
			if (real.length < 2) { opts.toast && opts.toast('Make zones in Setup › Zones first.'); return; }
			zones.forEach((z, i) => { z.rz = i < real.length ? real[i].id : null; fitReal(z); mk(z); });
			keep(); build(); opts.toast && opts.toast('Linked the parts to your zones in order.');
		};
		const sendAll = () => {
			const real = realZones(), linked = zones.filter(z => isLinked(z) && z.fx >= 0 && real.some(r => r.id === z.rz));
			if (!linked.length) { opts.toast && opts.toast('Link the parts to zones of your lights first (above each effect).'); return; }
			opts.send({ on: true, seg: linked.map(z => ({ id: z.rz, on: true, fx: z.fx, col: z.col, pal: z.pal, sx: z.sx })) })
				.then(() => opts.toast && opts.toast('Sent ' + linked.length + ' part(s) to their zones.')).catch(() => opts.toast && opts.toast('Could not send it to the lights.'));
		};
		// zones saved elsewhere (Setup › Zones): show the new list in the editor of the part on screen
		window.addEventListener('l4yzones', () => { if (cv.isConnected && ed.isConnected) { zones.forEach(fitReal); editor(); } });
		const build = () => {
			const old = saved[sc.id] || [];
			zones = sc.zones.map((z, i) => {
				const s = old[i] || {}, f = (s.fx != null && opts.fx.find(x => x[0] === s.fx)) || byName(z.look.fx);
				// an effect the list does not have (yet): imitate it by name, it cannot be sent
				const zz = { def: z, fx: f ? f[0] : -1, nm: f ? f[1] : z.look.fx, col: s.col || z.look.col.concat([[0, 0, 0], [0, 0, 0]]).slice(0, 3), pal: s.pal ?? z.look.pal, sx: s.sx ?? z.look.sx, n: s.n || z.n, rz: s.rz ?? null };
				zz.pts = SH[z.shape](z.o, zz.n); return zz;
			});
			zones.forEach(z => { if (isLinked(z)) fitReal(z); mk(z); });
			bgCache = null; sel = Math.min(sel, zones.length - 1);
			pick.replaceChildren(...scenes.map(s => h('button', { type: 'button', class: 'seg' + (s === sc ? ' sel' : ''), onclick: () => { sc = s; sel = 0; build(); } }, s.name)));
			tabs.replaceChildren(...zones.map((z, i) => h('button', { type: 'button', class: 'seg' + (i === sel ? ' sel' : ''), onclick: () => { sel = i; selT = performance.now(); build(); } }, z.def.name)));
			editor();
		};
		const mk = z => {
			const f = opts.fx.find(x => x[0] === z.fx) || [-1, z.nm || 'Solid', 0];
			z.pts = SH[z.def.shape](z.def.o, z.n);
			const xs = z.pts.map(p => p.x), ys = z.pts.map(p => p.y);
			z.bx = [Math.min(...xs), Math.max(...xs) - Math.min(...xs) || 1, Math.min(...ys), Math.max(...ys) - Math.min(...ys) || 1];
			// matrix effects need the real grid size (a curtain is 24 x 20), otherwise they come out squashed
			const o = z.def.o, isGrid = z.def.shape === 'grid';
			const gw = isGrid ? o.cols : 24, gh = isGrid ? o.rows : Math.max(5, Math.round(24 * z.bx[3] / z.bx[1]));
			z.smp = L4YStudio.sampler({ name: f[1], d2: !!f[2] && (isGrid || z.def.shape === 'custom'), col: z.col, pal: z.pal >= 2 ? opts.palStops(z.pal) : null, speed: z.sx, gw, gh });
		};
		const editor = () => {
			const z = zones[sel]; if (!z) { ed.replaceChildren(); return; }
			const fxSel = h('select', { 'data-notr': '', 'aria-label': 'Effect' }, fxList.map(f => h('option', { value: String(f[0]) }, f[1])));
			if (z.fx < 0) fxSel.prepend(h('option', { value: '-1' }, z.nm));
			fxSel.value = String(z.fx);
			const palSel = h('select', { 'data-notr': '', 'aria-label': 'Palette' }, opts.pal.map((n, i) => h('option', { value: String(i) }, n)));
			palSel.value = String(z.pal);
			const cols = [0, 1, 2].map(i => h('input', { type: 'color', class: 'colbtn sm', value: hex(z.col[i] || [0, 0, 0]), 'aria-label': 'Colour ' + (i + 1) }));
			const spd = fill(h('input', { type: 'range', min: '0', max: '255', value: String(z.sx), 'aria-label': 'Speed' }));
			const cnt = fill(h('input', { type: 'range', min: String(z.def.min), max: String(z.def.max), value: String(z.n), 'aria-label': 'Number of LEDs' }));
			const cntL = h('span', {}, z.n + ' LEDs');
			const upd = () => { z.fx = +fxSel.value; z.pal = +palSel.value; z.col = cols.map(c => rgb(c.value)); z.sx = +spd.value; z.n = +cnt.value; cntL.textContent = z.n + ' LEDs'; mk(z); keep(); };
			[fxSel, palSel].forEach(e => e.onchange = upd); cols.forEach(c => c.oninput = upd); spd.oninput = upd; cnt.oninput = upd;
			const useNow = async () => {
				if (!opts.current) return;
				try { const c = await opts.current(); z.fx = c.fx; z.pal = c.pal || 0; z.sx = c.sx ?? 128; if (c.col) z.col = c.col.concat([[0, 0, 0], [0, 0, 0]]).slice(0, 3); mk(z); keep(); editor(); opts.toast && opts.toast('Copied the look of your lights.'); }
				catch (e) { opts.toast && opts.toast('Could not read the lights.'); }
			};
			// which zone of the real lights this part of the picture is: its LED count follows the real zone
			const real = realZones(), rz = real.find(r => r.id === z.rz);
			const link = h('select', { 'aria-label': 'Zone of my lights' }, h('option', { value: '' }, 'Not linked (all my lights)'),
				real.map(r => h('option', { value: String(r.id), 'data-notr': '' }, r.name + ' (' + (r.strip ? 'LED ' + r.from + '–' + r.to : r.n + ' LEDs') + ')')),
				opts.saveZone ? h('option', { value: 'new' }, 'New zone: choose the LEDs…') : '');
			link.value = z.rz === 'new' ? 'new' : rz ? String(rz.id) : '';
			link.onchange = () => { z.rz = link.value === '' ? null : link.value === 'new' ? 'new' : +link.value; fitReal(z); if (z.rz !== 'new') { mk(z); keep(); } editor(); };
			// from LED .. to LED of the linked (or new) zone, on the lights themselves
			let leds = '';
			if (opts.saveZone && (z.rz === 'new' || (rz && rz.strip))) {
				const rg = opts.zoneRange ? opts.zoneRange() : { min: 1, max: 1500 };
				const used = Math.max(rg.min - 1, ...real.filter(r => r.strip && r.id !== z.rz && r.to < rg.max).map(r => r.to));
				const f0 = rz ? rz.from : Math.min(used + 1, rg.max), t0 = rz ? rz.to : rg.max;
				const fromI = h('input', { type: 'number', class: 'search', min: String(rg.min), max: String(rg.max), value: String(f0), 'aria-label': 'From LED' });
				const toI = h('input', { type: 'number', class: 'search', min: String(rg.min), max: String(rg.max), value: String(t0), 'aria-label': 'To LED' });
				const nm = h('input', { type: 'text', class: 'search', maxlength: '16', value: rz ? rz.name : z.def.name, 'aria-label': 'Zone name' });
				const save = async () => {
					const a = +fromI.value | 0, b = +toI.value | 0;
					if (a < rg.min || b > rg.max || b < a) { opts.toast && opts.toast('Choose LEDs from ' + rg.min + ' to ' + rg.max + ' (the first number not bigger than the second).'); return; }
					try {
						const r = await opts.saveZone({ id: rz ? rz.id : null, from: a, to: b, name: nm.value.trim() });
						z.rz = r.id; fitReal(z); mk(z); keep(); editor();
						opts.toast && opts.toast('Zone ' + (nm.value.trim() || z.def.name) + ': LED ' + a + ' to ' + b + '.' + (r.changed.length ? ' Made shorter: ' + r.changed.join(', ') + '.' : ''));
					} catch (e) { opts.toast && opts.toast(e.message === 'full' ? 'Up to 16 zones.' : e.message === 'matrix' ? 'Those LEDs are in the matrix: set matrix zones in Setup › Zones.' : 'Could not send it to the lights.'); }
				};
				leds = h('div', { class: 'lay-leds' },
					h('div', { class: 'lay-row3' }, h('label', {}, h('span', { class: 'lab' }, 'From LED'), fromI), h('label', {}, h('span', { class: 'lab' }, 'to LED'), toI)),
					h('label', {}, h('span', { class: 'lab' }, 'Zone name'), nm),
					h('div', { class: 'note' }, 'LED 1 is the first LED after the board (the LEDs of all outputs are counted one after the other). Other zones on these LEDs are made shorter.'),
					h('div', { class: 'row' }, h('button', { class: 'btn', type: 'button', onclick: save }, rz ? 'Save these LEDs' : 'Make this zone')));
			}
			const sendNow = () => z.fx < 0 ? opts.toast && opts.toast('Connect to lights with the newest LED4YOU to use this effect.') : opts.send({ on: true, seg: Object.assign(rz ? { id: z.rz } : {}, { fx: z.fx, col: z.col, pal: z.pal, sx: z.sx }) }).then(() => opts.toast && opts.toast('Your lights now show the ' + z.def.name + ' look.')).catch(() => opts.toast && opts.toast('Could not send it to the lights.'));
			ed.replaceChildren(
				...(opts.zones ? [h('label', { class: 'lab' }, 'On my lights, this part is'), link,
					leds,
					h('div', { class: 'note' }, rz ? 'Linked: "Show it on my lights" sends this part only to ' + rz.name + '.' : z.rz === 'new' ? '' : real.length > 1 ? 'Not linked: it goes to all your lights.' : 'Choose "New zone" to give this part its own LEDs.')] : []),
				h('label', { class: 'lab' }, 'Effect'), fxSel,
				h('div', { class: 'lay-row' }, cols, h('span', { class: 'note' }, 'Colours')),
				h('label', { class: 'lab' }, 'Palette'), palSel,
				h('div', { class: 'lbl' }, h('span', {}, 'Speed')), spd,
				...(z.def.min === z.def.max || rz ? [] : [h('div', { class: 'lbl' }, h('span', {}, 'LEDs in this zone'), cntL), cnt]),
				h('div', { class: 'row' },
					opts.current ? h('button', { class: 'btn', type: 'button', onclick: useNow }, 'Use the look of my lights') : '',
					opts.send ? h('button', { class: 'btn primary', type: 'button', onclick: sendNow }, 'Show it on my lights') : ''));
		};

		// drawing
		const draw = now => {
			if (!cv.isConnected && draw.seen) return;
			requestAnimationFrame(draw);
			if (!cv.isConnected || !cv.clientWidth || document.hidden) return;
			draw.seen = true;
			if (now - (draw.last || 0) < 40) return; draw.last = now;
			const W = 800, H = 600, g = cv.getContext('2d');
			if (!bgCache) { bgCache = document.createElement('canvas'); bgCache.width = 1600; bgCache.height = 1200; const b = bgCache.getContext('2d'); b.scale(2, 2); sc.bg(b, W, H); }
			g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(bgCache, 0, 0); g.setTransform(2, 0, 0, 2, 0, 0);
			const t = now / 1000;
			g.globalCompositeOperation = 'lighter';
			zones.forEach((z, zi) => {
				const n = z.pts.length, hi = zi === sel || now - selT > 1600 ? 1 : .25;
				// LEDs behind the tree first, dimmer and smaller
				const order = z.pts.map((p, i) => i).sort((a, b) => z.pts[a].z - z.pts[b].z);
				for (const i of order) {
					const p = z.pts[i], c = z.smp(i, n, t, (p.x - z.bx[0]) / z.bx[1], (p.y - z.bx[2]) / z.bx[3]);
					const k = (p.z < 0 ? .3 + .7 * (1 + p.z) * .5 : 1) * hi, m = Math.max(c[0], c[1], c[2]);
					if (m < 6) continue;
					const r = (c[0] * k) | 0, gg = (c[1] * k) | 0, b = (c[2] * k) | 0, sz = p.z < 0 ? 2.2 : 3;
					g.fillStyle = 'rgba(' + r + ',' + gg + ',' + b + ',.16)'; g.beginPath(); g.arc(p.x, p.y, sz * 3.2, 0, 6.283); g.fill();
					g.fillStyle = 'rgb(' + r + ',' + gg + ',' + b + ')'; g.beginPath(); g.arc(p.x, p.y, sz, 0, 6.283); g.fill();
				}
			});
			g.globalCompositeOperation = 'source-over';
		};

		box.replaceChildren(
			h('section', { class: 'card' },
				h('div', { class: 'ct' }, 'See it on your house'),
				h('div', { class: 'note' }, 'Pick a place, then choose what each part of the lights does. It is a drawing to get an idea: real lights look brighter and softer.'),
				pick, h('div', { class: 'lay-wrap' }, cv)),
			h('section', { class: 'card' },
				h('div', { class: 'ct' }, 'Zones'),
				tabs, ed,
				opts.zones && opts.send ? h('div', { class: 'row lay-all' },
					h('button', { class: 'btn', type: 'button', onclick: linkInOrder }, 'Link parts to my zones in order'),
					h('button', { class: 'btn primary', type: 'button', onclick: sendAll }, 'Show everything on my lights')) : ''));
		build();
		requestAnimationFrame(draw);
	}

	const css = `
.lay-wrap { margin-top: 10px; border-radius: 14px; overflow: hidden; border: 1px solid var(--line); }
.lay-cv { display: block; width: 100%; height: auto; aspect-ratio: 4 / 3; background: #060914; }
.lay-scenes, .lay-zones { margin-top: 8px; }
.lay-leds { margin: 8px 0 4px; padding: 10px; border: 1px solid var(--line); border-radius: 12px; display: flex; flex-direction: column; gap: 6px; }
.lay-leds label { display: flex; flex-direction: column; gap: 4px; }
.lay-leds .search { margin: 0; }
.lay-row3 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.lay-all { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); flex-wrap: wrap; }
.lay-ed { margin-top: 12px; display: flex; flex-direction: column; gap: 6px; }
.lay-ed select { width: 100%; }
.lay-row { display: flex; gap: 8px; align-items: center; margin: 6px 0; }
.colbtn.sm { width: 40px; height: 40px; }
`;
	window.L4YLayout = { mount, css, scenes: SCENES.map(s => s.name) };
})();
