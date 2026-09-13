---
name: egitim
description: Satın alınan eğitimlerden (EĞİTİMLER/KAYNAKLAR) soru cevaplama, ders anlatma ve işe dönük damıtma. "eğitim sor", "... eğitiminde ne anlatılıyor", "beni ... konusunda eğit", "ders anlat", "sınav yap", "damıt", "playbook çıkar" dendiğinde kullan.
---
# Eğitim

Kaynak: `EĞİTİMLER/KAYNAKLAR/`. Salt okunurdur; oraya yazma. Giriş: `EĞİTİMLER/KAYNAKLAR/index.md`
eğitimleri listeler, her eğitimin kökündeki `00 İçindekiler.md` derslerini tek satır özetle verir.

Üç mod var. Kullanıcı hangisini istediğini söylemediyse sor; "sor" varsayılandır.

## Sor
1. `EĞİTİMLER/KAYNAKLAR/index.md` ile eğitimi seç; birden fazla eğitim ilgiliyse hepsine bak.
2. O eğitimin `00 İçindekiler.md` dosyasından dersleri seç (en fazla 5).
3. Ders sayfasını oku. Sayfada `## Transkript` linki varsa transkripti de oku; asıl söz orada.
4. Cevabı kaynak linkiyle ver: her iddianın yanına `[[ders sayfası]]`. Eğitmen ne dediyse onu
   aktar; kendi yorumunu ayrı ve işaretli ver. Kaynakta olmayan şeyi kaynağa mal etme.
5. Eğitimler birbiriyle çelişiyorsa çelişkiyi söyle.

## Öğret
1. Konuyu içindekilerden derslere böl, sırayı ve süreyi söyle, onay al.
2. Her dersi sade dille, tam cümlelerle anlat; bir örnekle kullanıcının işine bağla; jargonu ilk
   geçtiği yerde açıkla. Ders başına en fazla iki ekran metin.
3. Ders sonunda üç soruluk kısa sınav yap, cevabı bekle, düzelt.
4. Öğrenilenleri kullanıcı isterse `EĞİTİMLER/KENDİ NOTLARIM/<konu>/` altına, onun diliyle yaz.

## Damıt
İşe dönük çıkarımı (reçete, prompt kütüphanesi, kontrol listesi, playbook) `İŞ/` altına yaz;
mevcut dosya varsa onu güncelle. Kaynağa link ver. Birebir korunması gerekeni özetleme.

## Bakım
- Yeni eğitim eklenince: dosyaları koy, `python3 .claude/scripts/egitim-icindekiler.py`.
- Kullanıcının kendi notu eğitimin kökündeki not dosyasına (`.claude/beyin.json` içindeki
  `notlar_dosyasi`, varsayılan `NOTLARIM.md`) yazılır.
