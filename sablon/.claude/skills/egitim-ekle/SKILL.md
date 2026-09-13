---
name: egitim-ekle
description: Kajabi altyapılı bir eğitim sitesinden (Digiens Academy ve benzerleri) satın alınmış bir eğitimi ders sayfası, video, transkript, belge ve Claude Analizi ile eksiksiz vault'a çeker. "şu eğitimi ekle", "bu eğitimi indir", "eğitim çek" dendiğinde kullan.
---
# Eğitim Ekle

Kajabi ders listesi Wistia video, S3 belge ve HTML ders gövdesinden oluşur; hiçbiri tek istekle
alınmaz. Bu skill sırayla ağacı çıkarır, ders sayfalarını çeker, videoyu indirir, transkript
çıkarır, belgeleri eşler, Claude Analizi yazdırır, sayfaya derler.

## 0. Girdi ve klasörler

Girdi: kategoriler sayfasının linki (`.../products/<slug>/categories`).
Hedef: `EĞİTİMLER/KAYNAKLAR/<Sağlayıcı>/<EĞİTİM>/` altında `RAW/VİDEOLAR`, `RAW/BELGELER`,
`RAW/GÖRSELLER`, `WİKİ`. Çalışma klasörü kod deposu dışında, örn. `<kod kökü>/_gecici/<slug>/` —
scratchpad oturum bitince silinir, ara dosyalar oraya güvenilmeden buraya konur.

## 1. Giriş — şef

chrome-devtools MCP ile sayfayı aç. Login'e düşerse kullanıcıya söyle: "açtığım Chrome penceresinde
bir kez giriş yap, Beni Hatırla işaretli olsun." Profil `~/.cache/chrome-devtools-mcp/chrome-profile`
kalıcıdır, sonraki eğitimlerde tekrar login gerekmez. Şifre GİZLİ'ye yazılmaz, kullanıcı kendi girer.

## 2. Ağaç — şef, `scripts/agac.js`

Kategoriler sayfası açıkken `evaluate_script` ile çalıştır (canlı sayfada çalışır, fetch'li HTML'de
modül başlıkları yok). Sayfa 2-3'e bölünmüş olabilir, sidebar hepsini gösterdiği için script hepsini
gezer. Çıktıyı `agac.json` olarak çalışma klasörüne yaz.

## 3. Ders sayfaları — şef başlatır, arastirmaci veya şef okur

Şef ham çıktıyı kendi bağlamına almaz. `scripts/sayfalar.js`'i pairs listesiyle `evaluate_script`
ile **await etmeden** başlat (protocol timeout ~30 sn, iş uzun sürer). Sonra ayrı bir kısa
`evaluate_script` ile `window.__egitim.done` yoklanır; `true` olunca `filePath` parametresiyle
sonucu dosyaya dök (filePath yalnız izin verilen çalışma klasörleri altında olabilir; yerel HTTP
alıcı sandbox yüzünden çalışmaz).

Çıktıyı `agac_ham.json` adıyla çalışma klasörüne koy, sonra **amele**: `scripts/kur.py` ile
`dersler.json` üret (global sıra no, temiz dosya adı, modül klasörü). Aynı oturumda Wistia süresi
için `yt-dlp --referer <site> --dump-single-json wistia:<id>` her ders için `wistia/<id>.json`'a
(8 paralel), sonra `kur.py` tekrar çalıştırılır.

## 4. Video indirme — amele, `scripts/indir.sh`

`indir.sh <dersler.json> <VİDEOLAR klasörü> <site referer>`. yt-dlp `hd_mp4-1080p/best`, 3 paralel,
var olanı atlar. **Bilinen tuzak:** macOS `xargs` `-d` desteklemez, NUL ayraçlı `-0` kullanılır;
`-L 1` boşlukta satırı böler, o yüzden kullanılmaz.

## 5. Belgeler — şef tetikler, amele indirir ve yerleştirir

Ders sayfasındaki `/courses/downloads/<id>/<slug>` linkleri tarayıcıda
`fetch(url, {credentials:'include', mode:'no-cors'})` ile hepsi aynı anda tetiklenir. Ardından
`list_network_requests` (fetch türü) ile isteklerin reqid'i alınır; 302 yönlendirmesi S3'e gider,
imzalı URL 7 gün geçerli. Görseller `get_network_request` + `responseFilePath` ile doğrudan diske
iner; pdf/docx/xlsx tarayıcı gövdeyi vermez (ERR_ABORTED), tam S3 URL'si ağ kaydından okunup amele
`curl` ile indirir. Eşleme iki TSV'de tutulur: `belge-url.tsv` (reqid → S3 URL),
`belge-esleme.tsv` (reqid, ders no, görünen ad, uzantı — örnek `ornek/` klasöründe yok ama biçimi
`kur.py` çıktısındaki gibi elle tutulur). Amele bu eşlemeyle dosyayı `NN - Başlık — Ad.ext` adıyla
`RAW/BELGELER` veya `RAW/GÖRSELLER`'e yerleştirir.

## 6. Transkript — amele, arka planda

`scripts/transkript.py` yorumlayıcısı Whisper motorunun kurulu olduğu venv'in python'ı (bu
vault'ta Widdownder projesinin venv'i). Video indirme sürerken paralel başlar:
`scripts/transkript-dongu.sh <dersler.json> <VİDEOLAR klasörü> <indir.log> <venv python yolu>` —
indirilen videoyu görünce hemen transkript çıkarır, indirme bitip iş kalmayınca kendi durur.

## 7. Claude Analizi — Workflow (Sonnet)

`scripts/analiz-workflow.js`, `args = {V, OUT, dersler:[{no,base}]}` ile Workflow olarak çalıştırılır:
yaz → denetle → düzelt, üçü de Sonnet. 88 derslik bir eğitim ~20M token, ~40 dakika. Oturum
sınırına takılırsa `resumeFromRunId` ile kaldığı yerden devam eder.

## 8. Sayfa üretimi ve kapanış

1. **amele**: `scripts/sayfa-uret.py <G> <B> <eğitim adı> <sağlayıcı adı>` — WİKİ ders sayfaları ve
   `— Transkript.md` dosyalarını üretir (venv gerekli: `pip install beautifulsoup4 markdownify lxml`
   ayrı bir venv'e, `sys.path.insert` ile eklenir).
2. **şef**: `python3 .claude/scripts/egitim-icindekiler.py` çalıştırıp `00 İçindekiler.md`'yi tazele.
3. **denetci**: yapı kontrolü (dosya sayısı, boş sayfa var mı) ve 3 rastgele dersin transkript
   sadakati örneklemi.
4. **şef**: commit (`git add -A && git commit`), push etme.

## Bilinen tuzaklar

- `evaluate_script` ~30 sn'de zaman aşımına uğrar; uzun işi §3'teki arka plan deseniyle yap.
- Kajabi ders sayfası CSP'si localhost'a fetch'i engeller; sonucu dosyaya `filePath` ile al.
- Sandbox içinde yerel bir HTTP alıcı (örn. `127.0.0.1:8765`) çalışmaz, denenmesin.
- `agac.js` yalnız canlı sayfada çalışır; sonucu `fetch`lenen HTML'de modül adı yoktur.

## Kim yapar

| Adım | Kim |
|---|---|
| Giriş, ağaç script'i çalıştırma, karar, süzme | Şef |
| Ders sayfası çekme, kur.py, dersler.json üretimi | Amele |
| Video indirme, transkript, belge indirme/yerleştirme | Amele (arka planda) |
| Claude Analizi (yazma, denetleme, düzeltme) | Workflow, Sonnet |
| Sayfa üretimi, İçindekiler tazeleme | Amele / şef (script) |
| Yapı ve sadakat kontrolü | Denetci |

## Bulamazsan

Login isteniyor, sayfa yapısı farklı (Kajabi dışı bir platform) veya ağ isteği beklenen deseni
vermiyorsa tahmin etme; kullanıcıya ne bulunamadığını tek cümleyle söyle.
