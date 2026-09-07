---
name: beyin-doktor
description: Beynin sağlık kontrolü. Kancalar, script'ler, hafıza dosyalarının tazeliği, günlük loglar, derleme durumu, kırık linkler, git ve yedek tek tabloda raporlanır. "beyin doktor", "doktor", "sağlık kontrolü", "beyin çalışıyor mu", "hafıza bozuk mu" dendiğinde veya bir mekanizmanın sessizce çalışmadığından şüphelenildiğinde kullan.
---

# Beyin Doktoru

Bu skill beynin mekanik katmanını denetler. Amaç sessiz arızayı görünür yapmak: kanca ateşlemiyor
mu, özet düşmüyor mu, Son Oturum bayat mı, derleyici takılı mı, linkler kopuk mu, yedek var mı.

## Nasıl çalışırsın

1. Vault kökünde çalış (CLAUDE.md'nin olduğu klasör). Komutları olduğu gibi çalıştır, tahmin etme.
2. Her kontrolü 🟢 / 🟡 / 🔴 olarak sınıfla.
3. Sonucu tek tabloda ver; her 🔴 için bir "Düzeltme:" satırı ve komut.
4. En sonda tek cümlelik hüküm.

Kontroller salt okunurdur. Kendiliğinden düzeltme; raporla, kullanıcı isterse düzelt.

## Kontroller

### 1. Kanca dosyaları var ve çalıştırılabilir

```bash
for h in session-start prompt-counter proje-yonerge session-end pre-compact; do f=".claude/hooks/$h.sh"; if [ ! -f "$f" ]; then echo "$h: DOSYA YOK"; elif [ ! -x "$f" ]; then echo "$h: calistirilabilir degil"; else echo "$h: ok"; fi; done; [ -f .claude/hooks/session-start.py ] && echo "session-start.py: ok" || echo "session-start.py: YOK"
```
🟢 hepsi ok. 🔴 eksik. Düzeltme: `chmod +x .claude/hooks/*.sh`; dosya yoksa yedekten kopyala.

### 2. Kancalar GLOBAL ayarda tam bir kez bağlı, vault ayarında hiç yok

Kancalar `~/.claude/settings.json` içinde yaşar (K1 kararı); vault'un `.claude/settings.json`
dosyasında olursa her olay iki kez ateşler.

```bash
python3 - <<'PYCHK'
import json, os
EV = {"SessionStart": ["session-start.sh"], "UserPromptSubmit": ["prompt-counter.sh", "proje-yonerge.sh"], "SessionEnd": ["session-end.sh"], "PreCompact": ["pre-compact.sh"]}
def say(path):
    try: d = json.load(open(os.path.expanduser(path), encoding="utf-8"))
    except FileNotFoundError: return None
    n = {}
    for ev, ms in (d.get("hooks") or {}).items():
        for m in ms or []:
            for h in m.get("hooks") or []:
                for name in EV.get(ev, []):
                    if name in (h.get("command") or ""): n[name] = n.get(name, 0) + 1
    return n
g = say("~/.claude/settings.json") or {}; v = say(".claude/settings.json") or {}
for ev, names in EV.items():
    for name in names: print(f"{name}: global={g.get(name,0)} vault={v.get(name,0)}")
PYCHK
```
🟢 her satır `global=1 vault=0`. 🔴 global 0 ise o kanca hiç çalışmıyor; vault 1 ise çift ateşliyor.
Düzeltme: kurulum rehberindeki global kanca bloğunu `~/.claude/settings.json` içine koy; vault'takini sil.

### 3. Özyineleme koruması

```bash
for f in .claude/hooks/*.sh; do grep -q 'BEYIN_INVOKED_BY' "$f" && echo "$(basename "$f"): guard var" || echo "$(basename "$f"): GUARD YOK"; done
```
🟢 hepsinde var. 🔴 eksik olan kanca arka plan `claude -p` çağrısında yeniden tetiklenir.

### 4. python3 ve claude yolda

```bash
command -v python3 >/dev/null && echo "python3: $(python3 -V 2>&1)" || echo "python3: YOK"; command -v claude >/dev/null && echo "claude: $(claude --version 2>&1 | head -1)" || echo "claude: YOK"; [ -f .claude/scripts/.state/python3-missing ] && echo "python3-missing isareti VAR" || echo "isaret yok"
```
🟢 ikisi de var, işaret yok. 🔴 yoksa flush ve derleme çalışmaz.

### 5. Son Oturum tazeliği (yeni)

```bash
f="HAFIZA/Son Oturum.md"; m=$(stat -f %m "$f"); n=$(date +%s); echo "Son Oturum: $(( (n-m)/3600 )) saat once yazildi; baslik: $(grep -m1 '^## Oturum:' "$f")"; ls -t GÜNLÜK/*.md | head -1 | xargs -I{} sh -c 'echo "son gunluk: {} $(( ($(date +%s) - $(stat -f %m "{}"))/3600 )) saat once"'
```
🟢 Son Oturum, son günlükten eski değil (ikisi aynı oturumdan). 🔴 Son Oturum günlükten bir günden
fazla eskiyse makine yazımı çalışmıyor. Düzeltme: `python3 .claude/scripts/flush.py --hook-input <hookin> --dry-run` ile dene; `health.json`'a bak.

### 6. Günlük log tazeliği ve tekrar

```bash
f=$(ls -t GÜNLÜK/*.md | head -1); m=$(stat -f %m "$f"); n=$(date +%s); echo "GÜNLÜK: $f, $(( (n-m)/3600 )) saat once"; echo "bugunku oturum sayisi: $(grep -c '^### Oturum' "GÜNLÜK/$(date +%F).md" 2>/dev/null || echo 0)"; python3 -c "import json;d=json.load(open('.claude/scripts/.state/flush-signatures.json'));print('imza kaydi:',len(d))" 2>/dev/null || echo "imza kaydi: yok"
```
🟢 48 saatten yeni. 🟡 48 ile 96 saat. 🔴 96 saatten eski. Bir günde aynı içerikli iki üç giriş varsa
imza mekanizması çalışmıyor demektir.

### 7. Derleme durumu ve son hata

```bash
python3 -c "import json;d=json.load(open('.claude/scripts/.state/compile-state.json'));print('last_run:',d.get('last_run'));print('last_status:',d.get('last_status'));print('ingested:',len(d.get('ingested',{})));print('son 5 kosu:',[r['status'] for r in d.get('runs',[])[-5:]])" 2>/dev/null || echo "compile: state yok"; [ -f .claude/scripts/.state/health.json ] && python3 -c "import json;d=json.load(open('.claude/scripts/.state/health.json'));print('health:',d.get('component'),d.get('error','')[:200])" || echo "health: kayit yok"
```
🟢 `last_status ok`, son koşuların çoğu ok. 🔴 `fail:` ile başlıyor veya son beş koşunun yarısından
fazlası başarısız; `health.json` içindeki stderr kuyruğu sebebi söyler (limit, ağ, izin).
Düzeltme: `python3 .claude/scripts/compile.py --dry-run`, sonra `python3 .claude/scripts/compile.py`.

### 8. Bilgi tabanı: indeks büyüklüğü ve kırık link (yeni)

```bash
echo "index satiri: $(grep -c '^| \[\[' BİLGİ/index.md)"; python3 - <<'PYL'
import re; from pathlib import Path
names={p.stem.casefold() for p in Path('.').rglob('*.md') if '/.trash/' not in str(p)}
link=re.compile(r'\[\[([^\]|#]+)')
bad=0; tot=0
for p in Path('BİLGİ').rglob('*.md'):
    for m in link.finditer(p.read_text(encoding='utf-8',errors='replace')):
        tot+=1; bad+= m.group(1).strip().split('/')[-1].casefold() not in names
print(f"BİLGİ link: {tot}, kırık: {bad}")
PYL
```
🟢 kırık 0, indeks 300 satır altı. 🟡 kırık birkaç tane (yeni açılacak not olabilir). 🔴 kırık yüzde
ondan fazla: dosya adları başlıkla uyuşmuyor. Düzeltme: kavram dosya adı başlığın kendisi olmalı.

Vault genelindeki kırık wiki-link ve ölü düz metin yolların tam listesi (dosya başına gruplu):
`python3 .claude/scripts/saglik.py --linkler`

Yapısal sağlık (öksüz sayfa, eksik proje çekirdeği, tek yönlü link, alan tetiği, kapsam dışı
klasör, hub eksiği) tam listesi: `python3 .claude/scripts/saglik.py --yapi`

### 9. Kurallar ve kural adayları

```bash
echo "kurallar: $(grep -c '^- \*\*kural:\*\*' HAFIZA/Kurallar.md) madde"; echo "kural adayi: $(grep -c '^- \[' 'HAFIZA/Kural Adayları.md' 2>/dev/null || echo 0) bekliyor"
```
🟢 kurallar var. 🟡 aday birikmiş: kullanıcıya sor, onaylananı Kurallar'a taşı, gerisini sil.

### 10. Git: uzak depo, push, bekleyen değişiklik (yeni)

```bash
git remote get-url origin 2>/dev/null || echo "REMOTE YOK"; echo "bekleyen: $(git status --porcelain | wc -l | tr -d ' ') dosya"; git log --oneline -1; git status -sb | head -1
```
🟢 remote var, `ahead` yok, bekleyen 20'nin altı. 🟡 bekleyen 20 ile 100 arası. 🔴 remote yok veya
`ahead` birikmiş (push çalışmıyor). Düzeltme: `git push origin HEAD`; remote yoksa Rehber Adım 6.

### 11. Yedek ve proje beyinleri

```bash
python3 - <<'PYB'
import json
from pathlib import Path
a = {}
try: a = json.load(open('.claude/beyin.json', encoding='utf-8'))
except Exception: pass
y = a.get('yedek'); print('yedek klasörü:', y if y else 'ayarda yok (beyin.json "yedek")')
if y and Path(y).is_dir(): print('son klon:', sorted(p.name for p in Path(y).iterdir() if p.is_dir())[-1:])

proj_root = Path('PROJELER')
eksik, genel_sayfa = [], []
for p in sorted(proj_root.iterdir()):
    if p.is_dir():
        if not (p / f'{p.name} Context.md').exists(): eksik.append(p.name)
    else:
        genel_sayfa.append(p.name)
print('Context.md eksik proje:', eksik if eksik else 'yok')
print('PROJELER kökünde genel sayfa (klasör dışı):', len(genel_sayfa))

k = a.get('projeler')
kalinti = []
if k and Path(k).is_dir():
    for p in sorted(Path(k).iterdir()):
        if p.is_dir() and (p / 'brain').is_dir(): kalinti.append(p.name)
print('kod kökünde brain/ kalıntısı:', kalinti if kalinti else 'yok')
print('kontrol bitti')
PYB
```
🟢 bir haftadan yeni klon var, her projenin `PROJELER/<P>/` klasöründe `<P> Context.md` var,
kod kökünde hiçbir projede `brain/` kalıntısı yok, `PROJELER/` kökünde klasör dışı yalnız genel
sayfalar duruyor. 🟡 klon eski. 🔴 Context.md eksik veya kod kökünde `brain/` kalıntısı varsa:
proje beyni eksik veya taşıma yarım kalmış demektir (kullanıcıya sor).

### 12. Eğitimler salt okunur mu, içindekiler var mı (yeni)

```bash
echo "yazilabilir dosya: $(find 'EĞİTİMLER/KAYNAKLAR' -type f -perm -u+w | wc -l | tr -d ' ')"; python3 -c "import unicodedata as u; from pathlib import Path; k=Path('EĞİTİMLER/KAYNAKLAR'); w=[d for d in k.rglob('*') if d.is_dir() and u.normalize('NFC',d.name).casefold()==u.normalize('NFC','WİKİ').casefold()]; print('icindekiler:', sum((d.parent/'00 İçindekiler.md').exists() for d in w), '/', len(w), 'egitim')"
```
🟢 yazılabilir 0, her eğitimde içindekiler var. 🔴 yazılabilir dosya varsa kilit açık kalmış:
`chmod -R a-w "EĞİTİMLER/KAYNAKLAR"`. İçindekiler eksikse `python3 .claude/scripts/egitim-icindekiler.py`.

### 13. Sır kaçağı

```bash
find . -path ./.git -prune -o -type f \( -name "*.bak" -o -name "*.orig" -o -name "settings.local.json.*" \) -print | head; git ls-files | grep -E 'GİZLİ|settings\.local\.json|\.env$' || echo "izlenen sirli dosya yok"
```
🟢 iki bölüm de boş. 🔴 bir şey çıkarsa: vault dışına taşı, `git rm --cached`, anahtarı yenile.

## Rapor formatı

```
| Kontrol | Durum | Bulgu |
| --- | --- | --- |
| Kanca dosyaları | 🟢 | hepsi yerinde |
| Global bağlantı | 🟢 | beş kanca, birer kez |
| ... | | |
```

Tablodan sonra yalnız 🔴 satırlar için "Düzeltme:" satırı ve komut. Sonra tek cümlelik hüküm:
"Beyin sağlıklı" veya "Beyin ayakta ama derleyici iki gündür takılı, önce onu çöz."
