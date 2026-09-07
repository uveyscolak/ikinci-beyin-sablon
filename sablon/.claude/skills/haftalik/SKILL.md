---
name: haftalik
description: Haftalık bakım ve temizlik. Oturum başındaki sağlık kontrolü "haftalık bakım zamanı" dediğinde veya kullanıcı "haftalık bakım", "temizlik yap", "hafta özeti" dediğinde kullan.
---
# Haftalık bakım

Kullanıcının hiçbir şeyi hatırlaması gerekmez; zamanı geldiğinde kanca söyler, sen teklif edersin.
Önce ne yapacağını üç dört cümleyle söyle, onay gelince uygula. On dakikalık iş.

## Adımlar

1. **Sağlık tablosu.** `python3 .claude/scripts/saglik.py` çıktısını göster. Kırmızı satır varsa
   önce onu çöz veya kullanıcıya ne yapılacağını söyle.
2. **Kural adayları.** `HAFIZA/Kural Adayları.md` dolu ise her maddeyi kullanıcıya tek tek sor:
   evet ise `Kurallar.md`'ye kural artı neden olarak taşı, hayır ise sil. Dosya boş kalsın.
3. **Açık konular budaması.** `HAFIZA/Açık Konular.md`:
   - "Kapanmış" bölümünde 30 günden eski maddeleri sil (hepsi günlükte ve bilgi tabanında zaten var).
   - "Açık" bölümündeki her maddeyi kullanıcıya oku: hâlâ açık mı, kapandı mı, unutuldu mu.
     Kapananları "Kapanmış"a taşı, tarihle.
4. **Projelerin nabzı.** Her projenin `PROJELER/<Proje>/<Proje> Context.md` dosyasındaki "Son
   güncelleme" tarihine bak. 30 günden eski olanları listele; kullanıcıya sor: o projeye bir
   oturum mu ayrılacak, yoksa `PROJELER/<Proje>/<Proje> — Proje.md` sayfasına "durdu" mu
   yazılacak.
5. **Bilgi tabanı.** `BİLGİ/index.md` 300 satırı geçtiyse tema başlıklarıyla grupla (eski satırlar
   başlık altında toplanır, makaleler dokunulmaz). Geçmediyse dokunma.
5b. **Katalog.** Kök `index.md` artık makine üretimi (`index-uret.py`, her oturum sonunda);
   elle satır eklenmez. Sıradışı bir şey varsa `python3 .claude/scripts/index-uret.py` çalıştır
   ve çıktının klasör gruplarına bak.
5c. **compile-stage artıklarını temizle.** Akşam derleyicisi her koşuda
   `~/.claude/projects/` altında bir `*beyin-compile-stage*` klasörü bırakıyor. Bir günden
   eskileri sil:
   `find ~/.claude/projects -maxdepth 1 -type d -name "*beyin-compile-stage*" -mmin +1440 -exec rm -rf {} +`
5d. **Kural denetimi.** Geçen hafta `HAFIZA/Kurallar.md` ve `CLAUDE.md` dosyalarına eklenen
   kuralları tek tek oku: her biri gerçekten bir davranışı değiştirdi mi. Değiştirmeyeni sil.
   Uygulanmayan kural bağlamı şişirir ve uygulanan kuralların ağırlığını düşürür.
6. **Hafta özeti.** Son yedi günün `GÜNLÜK/` dosyalarını oku ve `HAFIZA/Günce.md` sonuna
   `## Hafta özeti, <tarih>` başlığıyla beş sekiz satırlık bir giriş yaz: ne bitti, ne ilerledi, ne
   takıldı, kullanıcının ruh hali ve önceliği. Anlatı olsun, liste değil.
7. **Tarihi kaydet:** `python3 .claude/scripts/saglik.py --bakim-yapildi`. Bunu yapmazsan kanca
   her oturumda tekrar hatırlatır.

## Yapma

- Günlük ve bilgi klasörlerini elle düzenleme; onlar makinenin.
- Kullanıcı yorgunsa seçenek sıralama: tek teklif, onay, uygula.
