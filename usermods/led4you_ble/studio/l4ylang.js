/* LED4YOU language loader for the board's own pages (served as /l4ylang.js).
   English is built in; other languages are fetched from the LED4YOU site, so the pages stay
   small on the board. Without internet the pages simply stay in English. */
(function () {
	var L = { en: 'English', pt: 'Português', es: 'Español', fr: 'Français' }, l = '';
	try { l = localStorage.getItem('l4yLang') || ''; } catch (e) {}
	if (!L[l]) { var n = (navigator.language || 'en').slice(0, 2); l = L[n] ? n : 'en'; }
	var BASE = 'https://led4you.github.io/led4you/i18n/';
	function load() {
		if (l === 'en' || window.L4YI18n) return;
		var a = document.createElement('script'); a.src = BASE + 'wled_t.js';
		a.onload = function () { var b = document.createElement('script'); b.src = BASE + 'i18n.js'; document.head.appendChild(b); };
		document.head.appendChild(a);
	}
	function ui() {
		// effect and palette names are the same everywhere: keep them in English
		['fxlist', 'pallist'].forEach(function (id) { var e = document.getElementById(id); if (e) e.setAttribute('data-notr', ''); });
		var s = document.createElement('select');
		s.setAttribute('aria-label', 'Language'); s.setAttribute('data-notr', '');
		s.style.cssText = 'font-size:13px;padding:4px 6px;border-radius:999px;border:1px solid #444;background:#20242f;color:#eef0f6;width:auto;margin:0 6px;';
		for (var k in L) { var o = document.createElement('option'); o.value = k; o.textContent = '\u{1F310} ' + L[k]; s.appendChild(o); }
		s.value = l;
		s.onchange = function () { try { localStorage.setItem('l4yLang', s.value); } catch (e) {} location.reload(); };
		var bar = document.getElementById('l4ybar');
		if (bar) bar.insertBefore(s, document.getElementById('buttonPower'));
		else { s.style.cssText += 'position:fixed;top:8px;right:8px;z-index:9999;'; document.body.appendChild(s); }
		load();
		if (bar) { checkUpdate(); previews(); }
	}
	// main page: a small animation next to every effect showing how it looks (drawn by studio.js from the LED4YOU site)
	function previews() {
		var list = document.getElementById('fxlist'), col = null;
		if (!list) return;
		fetch('/json/state', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) { var sg = (j.seg || [])[0]; col = sg && sg.col; }).catch(function () {});
		var st = document.createElement('style');
		st.textContent = '#fxlist .lstI{position:relative}#fxlist .lstI canvas.pv{position:absolute;right:14px;top:50%;margin-top:-6px;width:96px;height:12px;border-radius:6px;pointer-events:none}#fxlist .lstIname{padding-right:104px}';
		document.head.appendChild(st);
		function deco() {
			if (!window.L4YStudio) return;
			var items = list.querySelectorAll('.lstI'), i;
			for (i = 0; i < items.length; i++) {
				var it = items[i]; if (it.querySelector('canvas.pv')) continue;
				var nm = it.querySelector('.lstIname'), opt = (it.getAttribute('data-opt') || '').split(';')[3] || '';
				it.appendChild(L4YStudio.preview({ name: nm ? nm.textContent : '', d2: opt.indexOf('2') >= 0, col: col, w: 96, h: 12 }));
			}
		}
		var sc = document.createElement('script'); sc.src = 'https://led4you.github.io/led4you/studio.js';
		sc.onload = function () { deco(); new MutationObserver(deco).observe(list, { childList: true }); };
		document.head.appendChild(sc);
	}
	// main page: tell when a newer LED4YOU is on the site (the update itself runs in the Studio page)
	function checkUpdate() {
		Promise.all([
			fetch('/json/state', { cache: 'no-store' }).then(function (r) { return r.json(); }),
			fetch('https://led4you.github.io/led4you/firmware/latest.json', { cache: 'no-store' }).then(function (r) { return r.json(); })
		]).then(function (a) {
			var cur = (a[0].l4y && a[0].l4y.fw) || 0, v = a[1].version || 0;
			if (v <= cur) return;
			var d = document.createElement('a');
			d.href = '/studio#update';
			d.style.cssText = 'display:block;margin:8px auto;max-width:600px;padding:10px 14px;border-radius:14px;background:linear-gradient(90deg,#ff2e93,#8b5cff,#00d4ff);color:#fff;font-weight:700;text-align:center;text-decoration:none;';
			var t = document.createElement('span'); t.textContent = 'LED4YOU v' + v + ' is available. Tap to update.';
			d.appendChild(t);
			var bar = document.getElementById('l4ybar');
			bar.parentNode.insertBefore(d, bar.nextSibling);
		}).catch(function () {});
	}
	if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ui); else ui();
})();
