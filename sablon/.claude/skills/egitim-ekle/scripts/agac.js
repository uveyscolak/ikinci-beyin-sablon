// chrome-devtools MCP evaluate_script içinde, kategoriler sayfası açıkken çalıştırılır.
// Döndürdüğü modül→kategori→ders ağacını agac.json'a yaz (id'ler ve başlıklar; ham HTML içermez).
async () => {
  const base = location.pathname.replace(/\/categories.*$/, '') + '/categories';
  const parse = (html) => new DOMParser().parseFromString(html, 'text/html');
  const modules = []; let cur = null; const seenCat = new Set();
  for (const n of document.querySelectorAll('h4, a[href*="/categories/"] h3')) {
    if (n.tagName === 'H4') { cur = {module: n.innerText.trim(), cats: []}; modules.push(cur); continue; }
    const m = n.closest('a').getAttribute('href').match(/categories\/(\d+)/);
    if (!m || seenCat.has(m[1])) continue; seenCat.add(m[1]);
    (cur || (cur = {module: '(modülsüz)', cats: []}, modules.push(cur), cur)).cats.push({id: m[1], title: n.innerText.trim()});
  }
  const fetchCat = async (id, depth) => {
    const doc = parse(await (await fetch(base + '/' + id, {credentials: 'include'})).text());
    const posts = [], subs = [], seenP = new Set(), seenS = new Set();
    for (const a of doc.querySelectorAll('a[href]')) {
      const h = a.getAttribute('href'); let m = h.match(/categories\/(\d+)\/posts\/(\d+)/);
      if (m && m[1] === id && !seenP.has(m[2])) { seenP.add(m[2]); posts.push({id: m[2], title: a.innerText.replace(/video lesson icon\/default Created with Sketch\./, '').trim().replace(/\s+/g, ' ')}); continue; }
      m = h.match(/categories\/(\d+)$/);
      if (m && m[1] !== id && !seenS.has(m[1]) && !seenCat.has(m[1])) { seenS.add(m[1]); subs.push({id: m[1], title: a.innerText.trim().replace(/\s+/g, ' ')}); }
    }
    const out = {id, posts, subs: []};
    if (depth < 3) for (const s of subs) { seenCat.add(s.id); const alt = await fetchCat(s.id, depth + 1); alt.title = s.title; out.subs.push(alt); }
    return out;
  };
  for (const mod of modules) for (const c of mod.cats) Object.assign(c, await fetchCat(c.id, 0));
  return modules;
}
// Not: modül başlıkları (h4) yalnız canlı sayfada var, fetch ile alınan HTML'de yok; bu yüzden
// bu script canlı kategoriler sayfasında çalışır. Sayfa 2-3'e bölünmüş olabilir, sidebar hepsini gösterir.
