---
name: haftalik
description: Haftalık bakım ve temizlik. Oturum başındaki sağlık kontrolü "haftalık bakım zamanı" dediğinde veya kullanıcı "haftalık bakım", "temizlik yap", "hafta özeti" dediğinde kullan.
---
# Haftalık bakım

Kullanıcının hiçbir şeyi hatırlaması gerekmez; zamanı geldiğinde kanca söyler, sen teklif edersin.
Önce ne yapacağını üç dört cümleyle söyle, onay gelince uygula. On dakikalık iş.
Bakım aynı zamanda sadeleştirmedir: hafıza dosyaları her oturumda tam yüklendiği için kısa
kalmak zorundadır.

## Adımlar

1. **Sağlık tablosu.** `python3 .claude/scripts/saglik.py` çıktısını göster. Kırmızı satır varsa
   önce onu çöz veya kullanıcıya ne yapılacağını söyle.
2. **Boyut kontrolü.** Açılış kancasının `[Boyut bekçisi]` uyarısı varsa (Kurallar 8.000, Açık
   Konular 6.000, Son Oturum 5.000 karakter) önce o dosya sadeleştirilir; kanca çıktısının kendisi
   9.000 karakteri aşıyorsa `session-start.py` bölümleri kısaltılır.
3. **Kural adayları.** `HAFIZA/Kural Adayları.md` dolu ise her maddeyi kullanıcıya tek tek sor:
   evet ise `Kurallar.md`'ye kural artı neden olarak taşı, hayır ise sil. Dosya boş kalsın.
4. **Açık konular budaması.** `HAFIZA/Açık Konular.md`:
   - Kapanan maddeler silinmez, `HAFIZA/Arşiv/Açık Konular Arşivi.md` dosyasının sonuna tarihli taşınır.
   - 14 gün hareketsiz açık madde kullanıcıya sorulur: kalsın mı, kapandı mı.
   - Her madde en fazla üç satır (başlık, durum, kalan iş); uzayan kısaltılır. Bir projenin durum
     notu Açık Konular'da değil o projenin `Context.md` dosyasında yaşar; Açık Konular yalnız link verir.
   - Dosya 6.000 karakteri geçmez.
5. **Projelerin nabzı.** Her projenin `PROJELER/<Proje>/<Proje> Context.md` dosyasındaki "Son
   güncelleme" tarihine bak. 30 günden eski olanları listele; kullanıcıya sor: o projeye bir
   oturum mu ayrılacak, yoksa `PROJELER/<Proje>/<Proje> — Proje.md` sayfasına "durdu" mu
   yazılacak.
6. **Bilgi tabanı.** `BİLGİ/index.md` 300 satırı geçtiyse tema başlıklarıyla grupla (eski satırlar
   başlık altında toplanır, makaleler dokunulmaz). Geçmediyse dokunma.
6b. **Katalog.** Kök `index.md` artık makine üretimi (`index-uret.py`, her oturum sonunda);
   elle satır eklenmez. Sıradışı bir şey varsa `python3 .claude/scripts/index-uret.py` çalıştır
   ve çıktının klasör gruplarına bak.
6c. **compile-stage artıklarını temizle.** Akşam derleyicisi her koşuda
   `~/.claude/projects/` altında bir `*beyin-compile-stage*` klasörü bırakıyor. Bir günden
   eskileri sil:
   `find ~/.claude/projects -maxdepth 1 -type d -name "*beyin-compile-stage*" -mmin +1440 -exec rm -rf {} +`
6d. **Kural denetimi.** `HAFIZA/Kurallar.md` dosyasının TAMAMI okunur (her kural tek cümle,
   20-30 madde); yalnız geçen hafta değil.
   - Davranışı değiştirmeyen ya da eskiyen kural silinmez, `HAFIZA/Arşiv/Kurallar 2026-09-13.md`
     dosyasının sonuna tarihli taşınır.
   - Anayasada (`CLAUDE.md`) zaten olan kural Kurallar'dan silinir (tek katman kuralı).
   - Mekanik kuralın (biçim, link, dosya düzeni) denetleyicide (`.claude/hooks/cevap-denetle.py`,
     `dosya-denetle.py`) satırı var mı bakılır; yoksa eklenir.
   - Dosya 8.000 karakteri geçmez; `HAFIZA/Son Oturum.md` 5.000'i geçiyorsa `flush.py` çıktısı
     kısaltılır.
7. **Hafta özeti.** Son yedi günün `GÜNLÜK/` dosyalarını oku ve `HAFIZA/Günce.md` sonuna
   `## Hafta özeti, <tarih>` başlığıyla beş sekiz satırlık bir giriş yaz: ne bitti, ne ilerledi, ne
   takıldı, kullanıcının ruh hali ve önceliği. Anlatı olsun, liste değil.
8. **Tarihi kaydet:** `python3 .claude/scripts/saglik.py --bakim-yapildi`. Bunu yapmazsan kanca
   her oturumda tekrar hatırlatır.

## Yapma

- Günlük ve bilgi klasörlerini elle düzenleme; onlar makinenin.
- Kullanıcı yorgunsa seçenek sıralama: tek teklif, onay, uygula.
