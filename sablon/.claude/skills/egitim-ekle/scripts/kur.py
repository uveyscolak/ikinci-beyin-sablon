# agac.json (kategoriler sayfasından) + agac_ham.json (sayfalar.js çıktısı, id->obj) çaprazlar,
# global sıra numaralı dersler.json üretir. Tekrar çalıştırılabilir.
# Kullanım: python3 kur.py <çalışma klasörü G> <eğitim kök klasörü B> <ürün slug'ı> <ürün URL kökü>
import json, re, os, sys

G = sys.argv[1]
B = sys.argv[2]
SLUG = sys.argv[3]  # örn. danismanlik-akademisi-2-0
URL_KOK = sys.argv[4]  # örn. https://www.digiensacademy.com/products

ham = json.load(open(G + '/agac_ham.json'))
items = {x['id']: x for x in ham['items']}
agac = json.load(open(G + '/agac.json'))

def tr_upper(s):
    return s.replace('i', 'İ').upper()

def temiz(s):
    s = s.replace(':', ' -').replace('/', '-')
    s = re.sub(r'[?"*<>|#^\[\]\\]', '', s)
    s = re.sub(r'\s+-\s+-\s+', ' - ', s)
    s = re.sub(r'\s+', ' ', s).strip(' .')
    return s

dersler = []
n = 0
for mi, m in enumerate(agac, 1):
    mod_klasor = '%02d-%s' % (mi, temiz(tr_upper(m['modul'])))

    def ekle(kat, alt, ids):
        nonlocal n
        grup = alt or kat
        for pid in ids:
            n += 1
            it = items[pid]
            baslik = it.get('title') or '?'
            ad = grup['ad'] + ' - ' + baslik if re.match(r'^Bölüm \d+', baslik) else baslik
            base = '%02d - %s' % (n, temiz(ad))
            dersler.append({
                'no': n, 'id': pid, 'cat': it.get('cat', kat['id']), 'modul': m['modul'],
                'modul_klasor': mod_klasor, 'kategori': kat['ad'], 'alt': alt['ad'] if alt else None,
                'baslik': baslik, 'base': base, 'wistia': it.get('wistia'), 'sure': it.get('duration'),
                'downloads': it.get('downloads', []),
                'url': f"{URL_KOK}/{SLUG}/categories/{kat['id']}/posts/{pid}",
            })

    for c in m['kategoriler']:
        ekle(c, None, c['dersler'])
        for a in c.get('alt', []):
            ekle(c, a, a['dersler'])

bases = [x['base'] for x in dersler]
assert len(set(bases)) == len(bases), 'çakışan ad var, temiz() kuralını gözden geçir'

# wistia süresi ve başlığı: G/wistia/<id>.json (yt-dlp --dump-single-json wistia:<id> çıktısı)
for x in dersler:
    wp = os.path.join(G, 'wistia', f"{x['wistia']}.json")
    if x['wistia'] and os.path.exists(wp):
        j = json.load(open(wp))
        x['wistia_title'] = j.get('title')
        x['saniye'] = j.get('duration')

json.dump(dersler, open(G + '/dersler.json', 'w'), ensure_ascii=False, indent=1)
print('ders sayısı:', len(dersler))
for x in dersler:
    print(x['modul_klasor'][:6], x['base'], '|', x['sure'], '| dl:', len(x['downloads']))
