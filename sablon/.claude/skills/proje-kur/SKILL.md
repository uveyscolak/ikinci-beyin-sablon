---
name: proje-kur
description: Yeni proje ya da yeni çalışma alanı kurulumu. Kullanıcı "yeni proje", "proje kur", "proje oluştur", "şu adla proje aç", "şu klasörde proje başlat", "yeni alan", "alan aç", "çalışma alanı kur" dediğinde kullan. Proje için vault'ta PROJELER/<Ad>/ (sayfa, PRD, Kararlar, Durum) ve kod klasöründe git deposu + CLAUDE.md işaretçisi açılır. Alan için verilen klasöre alan sayfası, Durum ve Kararlar açılır, tetik kelimeleri yazılır.
---
# Proje ve alan kurma

Kullanıcı elle klasör açmaz, şablon kopyalamaz. "Şu adla proje kur" ya da "buraya bir alan aç"
der; gerisi burada. Aradaki fark tek soruda ayrılır: **kodu var mı?**

- **Proje** = kodu olan iş. Kod dışarıda (beyin.json `projeler` kökü altında), akıl vault'ta
  `PROJELER/<Ad>/` altında. Repoda `brain/` açılmaz.
- **Alan** = kodu olmayan çalışma alanı: pazarlama, içerik, video kurgu, görsel üretim gibi.
  Vault'ta kendi klasöründe yaşar, kod klasörü ve PRD'si yoktur.

Proje ile alan arasında mekanizma farkı yoktur; ikisi de aynı dosyaları taşır.
Sırlar ikisinde de vault'a girmez, `GİZLİ/` altında durur.

## Dört dosyanın ne olduğu

Dosya adları sadedir, proje adı öne eklenmez. Klasör zaten hangi proje olduğunu söyler; adın
başına proje adını yazmak kenar çubuğunda adları uzatır ve dar ekranda hepsi aynı görünür.
Ayırt etme işi linkte çözülür, adda değil.

- **`Proje.md`** — vitrin: ne, neden var, kod nerede, git durumu. Canlı durumu tekrarlamaz.
  Başında `Tetik:` satırı taşıyabilir; projenin klasör adı zaten tetiktir, liste onun üstüne eklenir.
- **`Kurallar.md`** — yalnız o projeye özel, tartışmaya kapalı teknik kurallar: hangi dosya önce
  okunur, hangi araç kullanılır, neye dokunulmaz. Üslup, dil, biçim ve genel davranış kuralı
  buraya yazılmaz, onlar anayasada yaşar. Bir Kurallar dosyası "çelişirse bu geçerlidir" diyemez;
  anayasa her zaman üsttedir. Gerekmedikçe açılmaz, en fazla 3.000 karakter.
- **`PRD.md` = HEDEF.** Kurulumda yazılan donmuş spec: problem, kapsam, kabul kriterleri, kapsam
  dışı. Günlük iş buradan değil Durum'dan yürür. Yalnız projelerde vardır, alanlarda yoktur.
- **`Kararlar.md` = NEDEN.** Yalnız eklenir. Bir seçim yapıldığında tarih, ne, neden ve varsa
  "denedik olmadı" yazılır. Gerekçe yalnızca burada yaşar; eskiyi silme, geçersiz kalsa bile
  tarihiyle dursun. 60.000 karakteri geçince yıl bazında bölünür, eski yıl aynı klasörün `Arşiv/`
  dizinine `Kararlar-<yıl>.md` olarak iner.
- **`Durum.md` = ŞU AN.** Üç bölümü vardır:
  - `## Şu An` — projenin o anki hali, nerede kalındı, sıradaki adım, açık sorular, bitiş çizgisi.
    En fazla 3.000 karakter, her oturumda kendiliğinden gelir. Son satırında en son üç kararın
    tarihi ve tek satırlık başlığı durur. Gerekçeyi buraya kopyalama, Kararlar'a link ver.
  - `## Kaynaklar` — kullanıcının kendi iş dosyalarına ve eğitim notlarına köprü. Dosya adları düz
    metin olarak durur, uzunluğu serbesttir. Kullanıcı kendi dosyasını buraya ekler, Claude oradan
    okur; listede olmayan yeni bir iş dosyası doğarsa açılış kancası söyler.
  - Sonda tek satır: `Son gerçek doğrulama: YYYY-AA-GG`. İki ay dokunulmamış bir projeye
    dönüldüğünde hafızadaki rakama değil gerçeğe bakılmasını sağlar.
  - Eski Durum metni silinmez, aynı klasörün `Arşiv/` dizinine iner.
- Diğer notlar (mimari, araştırma, roadmap) aynı klasörde, aynı sade adla.

Alanlar aynı dosyaları kullanır ama hepsi `BEYİN/` alt klasöründe durur: `BEYİN/Alan.md`,
`BEYİN/Durum.md`, `BEYİN/Kararlar.md`, gerekirse `BEYİN/Kurallar.md`. Damıtılmış tarifler
`BEYİN/TARİFLER/` altında (`<Konu> Tarifi.md`). Tek kural: BEYİN Claude'un, gerisi kullanıcının.
Alan klasöründe kullanıcının okuduğu iş dosyaları da durur; beyin dosyaları tek klasörde toplanınca
kapalı kalır, göz iş dosyasında olur. Projede alt klasör yoktur, orada zaten başka dosya yoktur.

## Link yazımı — her zaman tam yol

Vault'ta yirmiye yakın `Durum.md` ve bir o kadar `Kararlar.md` vardır. Kısa link (`[[Kararlar]]`)
bunlardan hangisine gideceğini bilemez; Obsidian birini seçer ama seçimi tesadüfidir.
Bu yüzden her link tam yolla yazılır, görünen metin kısa tutulur:

    [[İŞ/GÖRSEL ÜRETİM/BEYİN/Kararlar|Kararlar]]
    [[PROJELER/Shopify/Durum|Durum]]

Kısa link yalnız vault'ta tek örneği olan dosyalar için serbesttir (`[[Projeler]]`).
Genel sayfalar (`Projeler.md` hub'ı, rehberler) `PROJELER/` kökünde kalır, alt klasöre inmez.

## Linkleme çift yönlü ve zorunlu

Yeni sayfa açılınca Durum'daki `## Alt Sayfalar` listesine eklenir ve yeni sayfadan
`[[PROJELER/<Proje>/Durum|Durum]]` ile geri link verilir. Öksüz sayfa yasak.
Boş sayfa da açılmaz; alt sayfa içerik hak edince doğar.

## Proje kurma

1. **Üç şeyi netleştir**, eksikse sor: proje adı (klasör ve dosya öneki olur, kısa ve boşluksuz
   tercih edilir), tek cümle amaç, kod klasörü (varsayılan `projeler` kökü altında ad; kod
   olmayacaksa `--kod-yok`; var olan bir klasörse yolunu al). Ne yapacağını iki cümleyle söyle,
   onay bekleme, kur.

2. **Script'i çalıştır:**
   ```
   python3 .claude/scripts/proje-kur.py --ad "<Ad>" --amac "<tek cümle>" [--klasor <yol>] [--kod-yok]
   ```
   Script şunları açar: `PROJELER/<Ad>/` altında `Proje.md`, `PRD.md`, `Kararlar.md`,
   `Durum.md`; kod klasöründe `git init`, `.gitignore`, `CLAUDE.md` işaretçisi; `PROJELER/Projeler.md`
   hub tablosuna satır. Var olan koda dokunmaz. Vault klasörü zaten varsa durur. Dört dosyanın iskeleti
   script'in içindedir; ayrıca şablon kopyası tutulmaz.

3. **PRD'yi sohbetle doldur.** Doğrudan koda başlama. Açık uçlu sor: problem kimin, çözüm ne, kapsam
   dışı ne, "bitti" neye göre denecek. Cevapları `PRD.md` içine yaz; ilk kararı `Kararlar.md`
   dosyasına tarihli ekle; `Durum.md` dosyasındaki `## Şu An` bölümünü doldur, `## Kaynaklar`
   bölümünü boş bırak (kullanıcı kendi dosyasını ekleyecek), sona `Son gerçek doğrulama` satırını koy.
   Hızlı modda (küçük araç) PRD tek ekran olabilir.

4. **Kurallar dosyası yalnız gerekirse.** Projeye özel, tartışmaya kapalı kural doğduysa `PROJELER/<Ad>/Kurallar.md`
   aç (şablon: `ASSETS/TEMPLATES/Kurallar.md` varsa ondan). Anayasadaki kuralı oraya kopyalama.

5. **Bitirirken** kullanıcıya üç satırda söyle: kod nerede, beyin nerede, sıradaki adım ne.

## Alan açma

1. **Üç şeyi netleştir:** alan adı (dosya öneki olur), tek cümle amaç, klasör (vault'a göreli, ör.
   `İŞ/ALT KLASÖR`). Klasör yoksa açılır, varsa içindeki dosyalara dokunulmaz.

2. **Tetik kelimelerini birlikte seç.** Bunlar alanın sohbette tanınmasını sağlar; alan adı zaten
   her zaman tetiktir, liste onun üstüne eklenir.
   - Üç ile altı kelime yeter. Uzun liste alanı her konuşmada yükler.
   - **Kök yaz, çekim yazma:** "reklam" yaz, "reklamlar" ve "reklamları" kendiliğinden eşleşir
     (eşleşme alt dize üzerinden çalışır, kelime sonu aranmaz).
   - **Üç harften kısa kelime yok sayılır.** Çok genel kelime de seçme ("iş", "not", "plan"
     gibi) — her cümlede geçer, alan boşuna yüklenir.
   - Alanın kendi işine özgü, başka alanla çakışmayan kelimeler seç.

3. **Script'i çalıştır:**
   ```
   python3 .claude/scripts/proje-kur.py --alan "<klasör>" --ad "<Ad>" --amac "<tek cümle>" --tetik "a,b,c"
   ```
   Script `<klasör>/BEYİN/` içine `Alan.md` (tetik kelimeleri ve `ad:` frontmatter'da), `Durum.md` ve
   `Kararlar.md` açar, `PROJELER/Projeler.md` içindeki `## Alanlar` tablosuna satır ekler.
   PRD ve kod klasörü yoktur. Var olan dosyanın üstüne yazmaz.

4. **Durum'u sohbetle doldur:** `## Şu An` bölümüne şu an nerede, sıradaki adım ve bitiş çizgisi;
   `## Kaynaklar` bölümü kullanıcının iş dosyaları için boş bekler; sona `Son gerçek doğrulama` satırı.
   Kurallar dosyası yalnız alana özel, tartışmaya kapalı kural doğduysa
   `<klasör>/BEYİN/Kurallar.md` olarak açılır.

5. **Deneyerek doğrula.** Tetik kelimelerinden birini içeren bir cümle kurulduğunda alan bir sonraki
   istemde yüklenmeli. Yüklenmiyorsa `tetik:` satırına bak.

`--kuru` her iki modda da yalnız ne yapılacağını yazar, dosyaya dokunmaz.

## Kancanın bilmesi gereken

`proje-yonerge` kancası her istemde çalışır ve iki şeye bakar:

- **Proje:** `PROJELER/` altındaki klasör adı ya da `Proje.md` içindeki `Tetik:` satırındaki bir
  kelime istemde geçerse projenin bloğu enjekte edilir.
- **Alan:** alan kökleri (`beyin.json` içinde `alan_kokleri`, varsayılan `İŞ` ve `KİŞİSEL`) altında
  en çok üç katman derinde `BEYİN/Alan.md` aranır (adı ön bloktaki `ad:` alanından); alan adı ya da
  ön bloktaki tetik kelimelerinden biri istemde geçerse aynı blok enjekte edilir.

Blok en fazla 8.500 karakterdir ve şunları taşır: Kurallar dosyası (en fazla 3.000 karakter),
Durum'un `## Şu An` bölümü (en fazla 3.000), `## Kaynaklar` listesindeki dosya adları,
Kararlar dosyasının son üç başlığı ve `TARİFLER/` klasöründeki tariflerin listesi.
Eşleşme kelime bazlıdır. Bir istemde en çok üç kayıt yüklenir ve aynı oturumda aynı kayıt bir kez
gelir; bağlam özetlenmeden önce kanca bu izi siler, konu tekrar geçince blok yeniden gelir.
