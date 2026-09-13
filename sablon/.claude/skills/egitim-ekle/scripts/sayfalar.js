// chrome-devtools MCP evaluate_script içinde çalışır. Protocol timeout ~30 sn olduğu için
// await ETMEDEN başlatılır; sonucu `window.__egitim` üzerinden ayrı bir evaluate_script ile yoklayıp,
// bitince (done:true) filePath ile dosyaya dök (filePath yalnız izin verilen çalışma klasörleri altında olabilir).
(pairs) => {  // pairs: ['<catId>/<postId>', ...]; ürün kökü location.pathname'den çıkarılır
  const root = location.pathname.replace(/\/categories.*$/, '');
  window.__egitim = {done: false, ok: 0, fail: [], items: []}; const st = window.__egitim;
  const worker = async (p) => { const [c, id] = p.split('/');
    try { const r = await fetch(`${root}/categories/${c}/posts/${id}`, {credentials: 'include'}); const html = await r.text();
      if (!r.ok) { st.fail.push(p + ':' + r.status); return; }
      const doc = new DOMParser().parseFromString(html, 'text/html'); const body = doc.querySelector('.post-body');
      const w = html.match(/wistia_async_([a-z0-9]+)/); const dur = doc.querySelector('.post-actions-duration'); const title = doc.querySelector('.post-body-title, .post-body h1');
      st.items.push({cat: c, id, title: title ? title.innerText.trim() : null, wistia: w ? w[1] : null, duration: dur ? dur.innerText.replace(/[\s\S]*Sketch\./, '').trim() : null, bodyHtml: body ? body.innerHTML : null,
        downloads: [...doc.querySelectorAll('.downloads-link')].map(a => ({href: a.getAttribute('href'), name: a.innerText.replace(/download icon[\s\S]*$/, '').trim()})), iframes: [...doc.querySelectorAll('iframe')].map(f => f.getAttribute('src'))});
      st.ok++; } catch (e) { st.fail.push(p + ':' + e); } };
  const queue = pairs.slice();
  Promise.all(Array.from({length: 4}, async () => { while (queue.length) await worker(queue.shift()); })).then(() => { st.done = true; });
  return 'başladı: ' + pairs.length;
}
