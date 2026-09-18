---
name: beyin-doktor
description: Beynin sağlık kontrolü. Kancalar, script'ler, hafıza dosyalarının tazeliği, günlük loglar, derleme durumu, kırık linkler, git ve yedek tek tabloda raporlanır. "beyin doktor", "doktor", "sağlık kontrolü", "beyin çalışıyor mu", "hafıza bozuk mu" dendiğinde veya bir mekanizmanın sessizce çalışmadığından şüphelenildiğinde kullan.
---

# Beyin Doktoru

Bu skill beynin mekanik katmanını denetler. Amaç sessiz arızayı görünür yapmak: kanca ateşlemiyor
mu, özet düşmüyor mu, Son Oturum bayat mı, gece bakımı takılı mı, linkler kopuk mu.

## Mekanizma haritası — makine neyi kendi yapar

Hafıza bir disiplin değil, mekanizma. Neyin ne zaman çalıştığı burada; bir şey beklendiği gibi
olmuyorsa arıza aşağıdaki halkalardan birindedir.

**Oturum açılınca.** `CLAUDE.md` ve içindeki üç dosya bağı (Kurallar, Açık Konular, Son Oturum)
Claude Code'un kendi dosya mekanizmasıyla tam yüklenir; bağlam özetlense bile diskten yeniden
okunur. Açılış kancası (`session-start.py`) bunun üstüne yalnız o an üretilen bilgiyi basar ve
çıktısı en fazla 6.000 karakterdir: sağlık kontrolü, sınırı aşan dosyalar için sayım satırı
("Kurallar 34/30" gibi), push bekleyen depolar, `HAFIZA/Bekleyenler.md` içinden en fazla üç madde,
`HAFIZA/Hatırlatmalar.md` içinden günü gelen satırlar, token raporundan tek satır, hiçbir Durum
dosyasının Kaynaklar listesinde geçmeyen en fazla üç iş dosyası, gece bakımı düştüyse tek satır ve
bugünün günlük kuyruğu. Sınır 6.000'dir çünkü Claude Code 10.000 karakteri aşan kanca çıktısını
dosyaya atıp yalnız ilk 2.000 karakterini gösterir.

**Her istemde.** `proje-yonerge.py` çalışır. Bir proje adı, bir `Tetik:` satırındaki kelime ya da
bir alanın tetik kelimesi geçerse o kaydın bloğu enjekte edilir; blok en fazla 8.500 karakterdir
ve Kurallar dosyasını, Durum'un `## Şu An` bölümünü, `## Kaynaklar` listesindeki dosya adlarını,
Kararlar'ın son üç başlığını ve tarifler listesini taşır. Aynı kanca `.claude/tetik-indeks.json`
dosyasına da bakar ve eşleşme varsa tek satır ipucu basar ("İlgili notlar: A, B, C"); dosya
yüklenmez, yalnız ad gelir.

**Bağlam özetlenmeden önce.** `pre-compact` kancası proje izlek dosyasını siler; konu tekrar
geçince blok yeniden gelir. Bu silme olmazsa bir proje bloğu oturumda bir kez gelir ve bir daha
hiç gelmez.

**Oturum kapanınca.** Kök `index.md` ve `.claude/tetik-indeks.json` yeniden üretilir, konuşmanın
özeti `GÜNLÜK/YYYY-AA-GG.md` dosyasına yazılır, `HAFIZA/Son Oturum.md` makine tarafından yenilenir
ve vault'un tamamı commit'lenip push'lanır. Kullanıcı oturum içinde Son Oturum dosyasını elle
yazdıysa makine o oturum için dokunmaz.

**Her gece saat dörtte.** `gece-bakim.py` model çağırmadan dört iş yapar: madde ve boyut sayımı,
kırık bağlantı ile bağlanmamış iş dosyası taraması, tetik indeksinin üretimi, token raporunun
`HAFIZA/Token Raporu.md` dosyasına yazımı. Sonra tek bir Sonnet çağrısı yapılır; girdisi dar
(Kurallar, Açık Konular, son günün günlüğü), çıktısı yalnız öneridir ve yalnız
`HAFIZA/Bekleyenler.md` dosyasına yazılır. İçeriğe dokunmaz, onay kullanıcıdan gelir. Haiku hiçbir
yerde kullanılmaz. Çağrı haftalık kullanım sınırına takılırsa atlanır, atlandığı kaydedilir ve
bir sonraki açılışta tek satırla söylenir.

**Git kaydı öncesi.** `.git/hooks/pre-commit` sır taraması yapar; bu Claude Code kanca zincirinden
bağımsız ikinci katmandır, yazma yolu ne olursa olsun kaydedilen metni tarar.

**Denetleyiciler.** `cevap-denetle.py` cevap bitmeden son mesajı tarar (dosya linki biçimi),
`dosya-denetle.py` vault'a yazılan `.md` dosyanın üst bilgi bloğuyla başlamadığına bakar.
İkincisi yalnız Write ve Edit araçlarını görür; Bash ile yazılan dosya kapsam dışıdır.

**Kancalar global kuruludur:** hangi klasörde çalışılırsa çalışılsın hafıza her zaman
`<VAULT>` içine yazılır. Disk bağlı değilse kancalar sessizce çıkmaz, görünür tek
satırlık uyarı bırakır.

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

### 7. Gece bakımı durumu ve son hata

```bash
python3 -c "import json;d=json.load(open('.claude/scripts/.state/gece-bakim-state.json'));print('last_run:',d.get('last_run'));print('last_status:',d.get('last_status'));print('ingested:',len(d.get('ingested',{})));print('son 5 kosu:',[r['status'] for r in d.get('runs',[])[-5:]])" 2>/dev/null || echo "gece bakimi: state yok"; [ -f .claude/scripts/.state/health.json ] && python3 -c "import json;d=json.load(open('.claude/scripts/.state/health.json'));print('health:',d.get('component'),d.get('error','')[:200])" || echo "health: kayit yok"
```
🟢 `last_status ok`, son koşuların çoğu ok. 🔴 `fail:` ile başlıyor veya son beş koşunun yarısından
fazlası başarısız; `health.json` içindeki stderr kuyruğu sebebi söyler (limit, ağ, izin).
Düzeltme: `python3 .claude/scripts/gece-bakim.py --dry-run`, sonra `python3 .claude/scripts/gece-bakim.py`.

### 8. Tetik indeksi ve kırık link

```bash
python3 -c "import json;d=json.load(open('.claude/tetik-indeks.json'));print('tetik kaydi:',len(d))" 2>/dev/null || echo "tetik-indeks.json: YOK"
```
🟢 indeks var ve kayıt sayısı sıfırdan büyük. 🔴 dosya yoksa ipucu satırı hiç basılmıyor demektir;
`python3 .claude/scripts/index-uret.py` çalıştır.

Vault genelindeki kırık wiki-link ve ölü düz metin yolların tam listesi (dosya başına gruplu):
`python3 .claude/scripts/saglik.py --linkler`

Yapısal sağlık (öksüz sayfa, eksik proje çekirdeği, tek yönlü link, alan tetiği, kapsam dışı
klasör, hub eksiği, bağlanmamış iş dosyası) tam listesi: `python3 .claude/scripts/saglik.py --yapi`

### 9. Hafıza dosyalarının biçimi ve Bekleyenler

```bash
echo "kural: $(grep -c '^- \*\*' HAFIZA/Kurallar.md) / 30 madde"; echo "acik konu: $(grep -c '^### ' 'HAFIZA/Açık Konular.md') / 20 madde"; echo "bekleyen: $(grep -c '^- ' 'HAFIZA/Bekleyenler.md' 2>/dev/null || echo 0) madde"; for f in "HAFIZA/Hatırlatmalar.md" "HAFIZA/Token Raporu.md"; do [ -f "$f" ] && echo "$f: var" || echo "$f: YOK"; done
```
🟢 sayılar sınırın altında, iki yeni dosya yerinde. 🟡 sınır aşılmış: `haftalik` skill'iyle
sadeleştir, Claude iki madde seçip kullanıcıya sorar. 🟡 Bekleyenler birikmiş: kullanıcıya sor,
onaylananı Kurallar'a taşı, gerisini sil.

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
        if not (p / 'Durum.md').exists(): eksik.append(p.name)
    else:
        genel_sayfa.append(p.name)
print('Durum.md eksik proje:', eksik if eksik else 'yok')
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
🟢 bir haftadan yeni klon var, her projenin `PROJELER/<P>/` klasöründe `Durum.md` var, kod kökünde hiçbir projede `brain/` kalıntısı yok, `PROJELER/`
kökünde klasör dışı yalnız genel sayfalar duruyor. 🟡 klon eski. 🔴 Durum.md eksik veya kod
kökünde `brain/` kalıntısı varsa: proje beyni eksik veya taşıma yarım kalmış demektir (kullanıcıya sor).

### 12. Eğitimlerde içindekiler var mı (yeni)

```bash
python3 -c "import unicodedata as u; from pathlib import Path; k=Path('EĞİTİMLER/KAYNAKLAR'); w=[d for d in k.rglob('*') if d.is_dir() and u.normalize('NFC',d.name).casefold()==u.normalize('NFC','WİKİ').casefold()]; print('icindekiler:', sum((d.parent/'00 İçindekiler.md').exists() for d in w), '/', len(w), 'egitim')"
```
🟢 her eğitimde içindekiler var. 🔴 İçindekiler eksikse `python3 .claude/scripts/egitim-icindekiler.py`.

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
