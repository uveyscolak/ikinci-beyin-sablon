---
name: kaynak
description: Dışarıdan bir kaynağı (web linki, PDF, YouTube veya sosyal medya videosu, yerel video/ses/metin dosyası) okuyup özetini günlüğe düşürür; akşam derleyicisi onu kavram makalesine çevirir. "kaynak ekle", "şu linki beyne al", "bu PDF'i oku ve kaydet", "bu videoyu özetle ve kaydet", "kaynak: <link>" dendiğinde kullan.
---
# Kaynak

Dışarıdan gelen bilgi beyne iki adımda girer: özet bugün `GÜNLÜK/` dosyasına düşer, akşam
derleyicisi ondan kavram makalesi çıkarır ve ertesi sabah `BİLGİ/index.md` içinde görünür.
Ham metin vault'a girmez; kaynağın kendisi linkle ya da dosya yoluyla işaret edilir.

## 1. Kaynağı tanı

- **Web sayfası, makale, gist:** `firecrawl_scrape` (markdown çıktı). Olmazsa `WebFetch`.
- **YouTube veya sosyal medya videosu:** `transkript` skill'i (önce altyazı, yoksa Whisper).
  Görüntünün kendisi önemliyse `watch` skill'i.
- **PDF:** `Read` ile, uzun PDF'te sayfa aralığıyla parça parça.
- **Yerel video veya ses:** `transkript` skill'i.
- **Yerel metin (md, txt, docx dönüşümü):** `Read`.

Kaynağı okuyup özetlemek şefin işi değil. `arastirmaci` ajanına ver: web sayfasını `WebFetch`
ile, videoyu `yt-dlp` ve Whisper ile, PDF'i `Read` ile kendisi getirir; ona kaynağı, kullanıcının
neden aldığını ve aşağıdaki özet biçimini yaz. Sayfa `WebFetch` ile açılmıyorsa şef
`firecrawl_scrape` ile çekip scratchpad'e dosya olarak koyar, ajana o dosyayı verir. Ajan özetler, şef süzer.

## 2. Neden alındığını bil

Kullanıcı neden aldığını söylemediyse tek cümleyle sor ("bunu ne için alıyoruz, hangi işe
bakıyor?"). Cevap özetin yönünü belirler: aynı makale reklam için okununca başka, sistem için
okununca başka şey çıkarır. Cevap gelmeden yazma; ama kullanıcı "sadece kaydet" derse sorma, genel
özet yaz.

## 3. Özeti günlüğe yaz

Dosya: `GÜNLÜK/YYYY-AA-GG.md` (bugün). Yoksa şu başlıkla aç:

```
# Günlük Log: YYYY-AA-GG

## Oturumlar
```

Dosyanın sonuna ekle (append), var olan hiçbir bloğa dokunma:

```
### Kaynak (SS:DD) — <kaynağın başlığı>
**Kaynak:** <link veya dosya yolu> · <tür> · <yazar, yayın tarihi varsa>
**Neden alındı:** <kullanıcının cümlesi>

## Özet
<5-10 cümle. Kaynağın ana iddiası ve dayandığı şey. Süs yok.>

## Çıkarımlar
- <Bu iş için ne anlama geliyor; iş, sistem, proje adıyla>
- <Alınabilecek somut adım varsa>

## Rakamlar ve alıntılar
- <sayı, eşik, fiyat, tam alıntı; kaynaktaki yeri ile>

## İlgili
- [[<vault'ta ilgili not>]] — <bağ tek cümle>
```

Kurallar:
- Blok 60 satırı geçmesin. Uzun kaynakta bile özet kısa, ayrıntı linkte.
- Rakam ve alıntı birebir; yuvarlama, "yaklaşık" yok. Kaynakta yoksa bölümü boş bırakma, sil.
- `## İlgili` altındaki her link gerçek bir vault notu olsun; yoksa bölümü sil. Uydurma link
  sağlık taramasında kırık çıkar.
- Aynı kaynak daha önce alınmışsa (günlükte veya `BİLGİ/index.md` içinde link/başlık grep'i)
  yeniden yazma; kullanıcıya "bunu şu tarihte almışız, makalesi şu" de ve dur.
- Ham metin, transkript, PDF kopyası vault'a girmez. Kullanıcı saklamak isterse dosya
  `ASSETS/` dışında, vault dışında bir yere konur; günlükteki blok yolunu gösterir.

## 4. Proje veya alana bağla

Kullanıcı bir proje ya da alan adı verdiyse o Context'in sonuna tek satır düş:
`- YYYY-AA-GG kaynak: <başlık> — özet [[GÜNLÜK/YYYY-AA-GG]]`. Söylemediyse dokunma.
Kaynak bir kararı değiştiriyorsa karar Kararlar dosyasına kullanıcı onayıyla girer, kendiliğinden değil.

## 5. Kullanıcıya söyle

Üç beş cümle: kaynak ne diyor, bize ne ifade ediyor, nereye yazdın. "Akşam derleyicisi kavram
makalesine çevirir, yarın sabah indekste görünür" bilgisini ilk kullanımlarda ekle. Özetin
tamamını sohbete yapıştırma; isterse günlükten okur.

## Bulamazsan

Link açılmıyor, PDF okunmuyor, video altyazısız ve Whisper yoksa tahminle özet yazma. Neyin
olmadığını tek cümleyle söyle ve dur.
