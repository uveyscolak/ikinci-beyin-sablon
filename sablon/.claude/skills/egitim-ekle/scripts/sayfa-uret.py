# WİKİ ders sayfalarını ve transkript .md dosyalarını üretir. Tekrar çalıştırılabilir.
# Kullanım: python3 sayfa-uret.py <çalışma klasörü G> <eğitim kök klasörü B> <eğitim adı> <sağlayıcı adı>
# G içinde beklenen: dersler.json, agac_ham.json (ham sayfa verisi, id->obj), belge-esleme.tsv (varsa), ozetler.json (varsa)
import json, os, re, sys

# bs4/markdownify pip ile ayrı bir venv'e kurulur (bkz. SKILL.md 4. adım); PYTHONPATH oradan eklenir.
from bs4 import BeautifulSoup
from markdownify import markdownify as md

G = sys.argv[1]
B = sys.argv[2]
EGITIM_ADI = sys.argv[3]
SAGLAYICI_ADI = sys.argv[4]
V = os.path.join(B, 'RAW/VİDEOLAR')
dersler = json.load(open(G + '/dersler.json'))
ham = {x['id']: x for x in json.load(open(G + '/agac_ham.json'))['items']}
esleme_p = G + '/belge-esleme.tsv'
esleme = [l.rstrip('\n').split('\t') for l in open(esleme_p)] if os.path.exists(esleme_p) else []
ozetler_p = G + '/ozetler.json'
ozetler = json.load(open(ozetler_p)) if os.path.exists(ozetler_p) else {}

def metin(html):
    if not html: return ''
    soup = BeautifulSoup(html, 'lxml')
    for t in soup.select('h1, hr'): t.decompose()
    for t in soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6']):
        if t.find_parent('li'):
            t.unwrap()
        else:
            yazi = t.get_text(' ', strip=True)
            if not yazi: t.decompose(); continue
            p = soup.new_tag('p'); s = soup.new_tag('strong'); s.string = yazi; p.append(s); t.replace_with(p)
    m = md(str(soup), heading_style='ATX', bullets='-').strip()
    m = re.sub(r'\n{3,}', '\n\n', m)
    m = re.sub(r'[ \t]+\n', '\n', m)
    return m.strip()

def paragraflar(txt):
    satirlar = [s.strip() for s in txt.splitlines() if s.strip()]
    out, grup = [], []
    for s in satirlar:
        grup.append(s)
        if len(grup) >= 8 and re.search(r'[.!?…]$', s):
            out.append(' '.join(grup)); grup = []
    if grup: out.append(' '.join(grup))
    return '\n\n'.join(out)

sayfa = 0; transkript = 0
for x in dersler:
    base = x['base']; h = ham[x['id']]
    klasor = os.path.join(B, 'WİKİ', x['modul_klasor']); os.makedirs(klasor, exist_ok=True)
    kat = x['kategori'] + (' › ' + x['alt'] if x['alt'] else '')
    parca = [f"# {base}", '',
             f"Eğitim: {EGITIM_ADI} ({SAGLAYICI_ADI}) · Modül: {x['modul']} · Kategori: {kat} · Süre: {x['sure'] or '?'}",
             f"Kaynak: {x['url']}", '',
             f"![[{base}.mp4]]", '']
    ozet = ozetler.get(str(x['no'])); analiz = None
    ap = os.path.join(G, 'analiz', f"{x['no']}.md")
    if os.path.exists(ap) and os.path.getsize(ap) > 0:
        icerik = open(ap).read().strip()
        ilk, _, kalan = icerik.partition('\n')
        if ilk.upper().startswith('NE ÖĞRETİYOR:'):
            ozet = ilk.split(':', 1)[1].strip(); analiz = kalan.strip()
        else:
            analiz = icerik
    if ozet:
        parca += ['## Ne Öğretiyor', '', ozet.strip(), '']
    m = metin(h['bodyHtml'])
    if m:
        parca += ['## Ders Metni', '', m, '']
    ekler = [(ad, ext) for rid, no, ad, ext in esleme if int(no) == x['no']]
    if ekler:
        parca += ['## İndirilebilir İçerikler', '']
        for ad, ext in ekler:
            dosya = f"{base} — {ad}.{ext}"
            parca.append(f"- [[{dosya}|{ad}]] ({ext})")
        parca.append('')
    if analiz:
        parca += ['## Claude Analizi', '', analiz, '']
    txt = os.path.join(V, base + '.txt')
    if os.path.exists(txt) and os.path.getsize(txt) > 0:
        parca += ['## Transkript', '', f"[[{base} — Transkript]]", '']
        with open(os.path.join(V, base + ' — Transkript.md'), 'w') as f:
            f.write(f"# {base} — Transkript\n\n> Ders: [[{base}]] · videonun ham transkripti (Whisper large-v3-turbo q8)\n\n" + paragraflar(open(txt).read()) + '\n')
        transkript += 1
    with open(os.path.join(klasor, base + '.md'), 'w') as f:
        f.write('\n'.join(parca).rstrip() + '\n')
    sayfa += 1
print('sayfa:', sayfa, 'transkript md:', transkript)
