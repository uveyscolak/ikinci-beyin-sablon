---
name: proje-kur
description: Yeni proje ya da yeni çalışma alanı kurulumu. Kullanıcı "yeni proje", "proje kur", "proje oluştur", "şu adla proje aç", "şu klasörde proje başlat", "yeni alan", "alan aç", "çalışma alanı kur" dediğinde kullan. Proje için vault'ta PROJELER/<Ad>/ (sayfa, PRD, Kararlar, Context) ve kod klasöründe git deposu + CLAUDE.md işaretçisi açılır. Alan için verilen klasöre alan sayfası, Context ve Kararlar açılır, tetik kelimeleri yazılır.
---
# Proje ve alan kurma

Kullanıcı elle klasör açmaz, şablon kopyalamaz. "Şu adla proje kur" ya da "buraya bir alan aç"
der; gerisi burada. Aradaki fark tek soruda ayrılır: **kodu var mı?**

- **Proje** = kodu olan iş. Kod dışarıda (beyin.json `projeler` kökü altında), akıl vault'ta
  `PROJELER/<Ad>/` altında. Repoda `brain/` açılmaz.
- **Alan** = kodu olmayan çalışma alanı: pazarlama, içerik, video kurgu, görsel üretim gibi.
  Vault'ta kendi klasöründe yaşar, kod klasörü ve PRD'si yoktur.

Sırlar ikisinde de vault'a girmez, `GİZLİ/` altında durur.

## Proje kurma

1. **Üç şeyi netleştir**, eksikse sor: proje adı (klasör ve dosya öneki olur, kısa ve boşluksuz
   tercih edilir), tek cümle amaç, kod klasörü (varsayılan `projeler` kökü altında ad; kod
   olmayacaksa `--kod-yok`; var olan bir klasörse yolunu al). Ne yapacağını iki cümleyle söyle,
   onay bekleme, kur.

2. **Script'i çalıştır:**
   ```
   python3 .claude/scripts/proje-kur.py --ad "<Ad>" --amac "<tek cümle>" [--klasor <yol>] [--kod-yok]
   ```
   Script şunları açar: `PROJELER/<Ad>/` altında `<Ad> — Proje.md`, `<Ad> PRD.md`, `<Ad> Kararlar.md`,
   `<Ad> Context.md`; kod klasöründe `git init`, `.gitignore`, `CLAUDE.md` işaretçisi; `PROJELER/Projeler.md`
   hub tablosuna satır. Var olan koda dokunmaz. Vault klasörü zaten varsa durur. Dört dosyanın iskeleti
   script'in içindedir; ayrıca şablon kopyası tutulmaz.

3. **PRD'yi sohbetle doldur.** Doğrudan koda başlama. Açık uçlu sor: problem kimin, çözüm ne, kapsam
   dışı ne, "bitti" neye göre denecek. Cevapları `<Ad> PRD.md` içine yaz; ilk kararı `<Ad> Kararlar.md`
   dosyasına tarihli ekle; `<Ad> Context.md` içindeki "Şu An Nerede" ve "Sıradaki Adım" bölümlerini
   güncelle. Hızlı modda (küçük araç) PRD tek ekran olabilir.

4. **Yönerge yalnız gerekirse.** Projeye özel, tartışmaya kapalı kural doğduysa `PROJELER/<Ad>/<Ad> Yönerge.md`
   aç (şablon: `ASSETS/TEMPLATES/Yönerge.md` varsa ondan). Anayasadaki kuralı oraya kopyalama.

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
   Script `<klasör>` içine `<Ad> — Alan.md` (tetik kelimeleri frontmatter'da), `<Ad> Context.md` ve
   `<Ad> Kararlar.md` açar, `PROJELER/Projeler.md` içindeki `## Alanlar` tablosuna satır ekler.
   PRD ve kod klasörü yoktur. Var olan dosyanın üstüne yazmaz.

4. **Context'i sohbetle doldur:** şu an nerede, sıradaki adım, bitiş çizgisi. Yönerge yalnız
   alana özel, tartışmaya kapalı kural doğduysa `<klasör>/<Ad> Yönerge.md` olarak açılır.

5. **Deneyerek doğrula.** Tetik kelimelerinden birini içeren bir cümle kurulduğunda alan bir sonraki
   istemde yüklenmeli. Yüklenmiyorsa `tetik:` satırına bak.

`--kuru` her iki modda da yalnız ne yapılacağını yazar, dosyaya dokunmaz.

## Kancanın bilmesi gereken

`proje-yonerge` kancası her istemde çalışır ve iki şeye bakar:

- **Proje:** `PROJELER/` altındaki klasör adı istemde geçerse `<Ad> Yönerge.md` ve `<Ad> Context.md`
  enjekte edilir. Ekstra kayıt gerekmez.
- **Alan:** alan kökleri (`beyin.json` içinde `alan_kokleri`, varsayılan `İŞ` ve `KİŞİSEL`) altında
  en çok üç katman derinde `<Ad> — Alan.md` aranır; alan adı ya da frontmatter'daki tetik
  kelimelerinden biri istemde geçerse aynı ikili enjekte edilir.

Bir istemde en çok üç kayıt (proje + alan) yüklenir ve aynı oturumda aynı kayıt bir kez yüklenir.
