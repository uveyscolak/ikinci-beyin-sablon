---
name: haftalik
description: Haftalık bakım ve temizlik. Oturum başındaki sağlık kontrolü "haftalık bakım zamanı" dediğinde veya kullanıcı "haftalık bakım", "temizlik yap", "hafta özeti" dediğinde kullan.
---
# Haftalık bakım

Kullanıcının hiçbir şeyi hatırlaması gerekmez; zamanı geldiğinde kanca söyler, sen teklif edersin.
Önce ne yapacağını üç dört cümleyle söyle, onay gelince uygula. On dakikalık iş.

Bakım aynı zamanda sadeleştirmedir: hafıza dosyaları her oturumda tam yüklendiği için kısa kalmak
zorundadır. Sınır bir uyarı değil, dosyanın biçimidir.

## Adımlar

1. **Sağlık tablosu.** `python3 .claude/scripts/saglik.py` çıktısını göster. Kırmızı satır varsa
   önce onu çöz veya kullanıcıya ne yapılacağını söyle.

2. **Sayım satırları.** Açılışta "Kurallar 34/30" gibi bir sayım satırı geldiyse o dosya bu
   bakımda sadeleştirilir. Sınırlar: Açık Konular en fazla 20 madde ve her madde tek satır,
   Kurallar en fazla 30 kural ve her kural tek cümle artı tek cümle neden, Son Oturum 5.000
   karakter. Açılış kancası çıktısı 6.000 karakteri aşıyorsa `session-start.py` bölümleri kısalır.

3. **Bekleyenler.** `HAFIZA/Bekleyenler.md` dolu ise her maddeyi kullanıcıya tek tek sor.
   Bölümler ve ne yapılacağı:
   - Kural adayları: evet ise `HAFIZA/Kurallar.md` dosyasına kural artı neden olarak taşı,
     hayır ise sil.
   - Birleştirme adayları: onay gelirse iki kural tek cümleye iner, eski hali tarihiyle
     `HAFIZA/Arşiv/` altına taşınır, silinmez.
   - Çelişkiler: doğruysa kararı ilgili Kararlar dosyasına işle, yanlışsa kaynağı düzelt, maddeyi sil.
   - Link önerileri: doğruysa linki kur, yanlışsa sil.
   - Kapatılanlar: gözden geçir, gerekiyorsa Açık Konular'dan arşive taşı.
   Dosya bakım sonunda boş kalsın.

4. **Açık konular budaması.** `HAFIZA/Açık Konular.md`:
   - Her madde tek satır: başlık, tek cümle durum, projenin Durum dosyasına bağlantı.
     Ayrıntı buraya kopyalanmaz, projenin kendi `Durum.md` dosyasında yaşar.
   - Kapanan maddeler silinmez, `HAFIZA/Arşiv/Açık Konular Arşivi.md` dosyasının sonuna tarihli
     taşınır.
   - 14 gün hareketsiz açık madde kullanıcıya sorulur: kalsın mı, kapandı mı.
   - Dosya 20 maddeyi geçmez.

5. **Kural denetimi.** `HAFIZA/Kurallar.md` dosyasının tamamı okunur, yalnız geçen hafta değil.
   - Davranışı değiştirmeyen ya da eskiyen kural silinmez, `HAFIZA/Arşiv/` altındaki tarihli
     Kurallar dosyasının sonuna taşınır.
   - Anayasada (`CLAUDE.md`) zaten olan kural Kurallar'dan silinir; bir kural tek katmanda yaşar,
     tekrarlanan kural er geç çelişir.
   - Mekanik kuralın (biçim, link, dosya düzeni) denetleyicide (`.claude/hooks/cevap-denetle.py`,
     `dosya-denetle.py`) satırı var mı bakılır; yoksa eklenir. Kural yalnız yazılmakla değil
     denetlenmekle yaşar.
   - Dosya 30 kuralı geçmez.

6. **Projelerin nabzı.** Her projenin `PROJELER/<Proje>/Durum.md` dosyasındaki
   `Son gerçek doğrulama` tarihine bak. 30 günden eski olanları listele; kullanıcıya sor: o projeye
   bir oturum mu ayrılacak, yoksa `Proje.md` sayfasına "durdu" mu yazılacak.

7. **Kararlar dosyalarının boyutu.** 60.000 karakteri geçen `Kararlar.md` dosyası yıl bazında
   bölünür; eski yıl aynı klasörün `Arşiv/` dizinine `Kararlar-<yıl>.md` olarak iner, yeni yıl
   aktif dosyada devam eder. Hiçbir karar silinmez.

   ```bash
   find PROJELER İŞ KİŞİSEL -name "Kararlar.md" -size +58k -exec wc -c {} \;
   ```

8. **Kod deposunda akıl kaldı mı.** Karar, durum, araştırma, plan, devir notu gibi belgeler kod
   deposunda durmaz, vault'ta `PROJELER/<Proje>/` altına taşınır; repoda yalnız kod ve kodun
   belgesi (README, kurulum, API) kalır. Kod köklerinde bu tür belge var mı bak, varsa taşı.

9. **Bağlanmamış iş dosyaları.** Açılış kancası İŞ ve KİŞİSEL altında hiçbir Durum dosyasının
   `## Kaynaklar` listesinde geçmeyen yeni dosyaları basar. Bakımda bunların hepsine bak,
   ait oldukları Durum dosyasının Kaynaklar listesine ekle.

10. **Katalog ve artıklar.** Kök `index.md` makine üretimidir (`index-uret.py`, her oturum
    sonunda); elle satır eklenmez. Sıradışı bir şey varsa
    `python3 .claude/scripts/index-uret.py` çalıştır ve klasör gruplarına bak.
    Gece bakımının bıraktığı bir günden eski geçici klasörleri sil:
    `find ~/.claude/projects -maxdepth 1 -type d -name "*beyin-compile-stage*" -mmin +1440 -exec rm -rf {} +`

11. **Token raporu.** `HAFIZA/Token Raporu.md` dosyasına bak. Kullanım belirgin biçimde
    artıyorsa sebebini söyle: hangi dosya şişti, hangi blok gereksiz geliyor.

12. **Tarihi kaydet:** `python3 .claude/scripts/saglik.py --bakim-yapildi`. Bunu yapmazsan kanca
    her oturumda tekrar hatırlatır.

## Yapma

- Günlük klasörünü elle düzenleme; o makinenin.
- Kullanıcı yorgunsa seçenek sıralama: tek teklif, onay, uygula.
- Kural ya da açık konu silme; hepsi arşive iner.
- Dondurma dönemi 2026-10-17'ye kadar sürüyor: bakımda yapısal değişiklik önerme, yalnız ölçüm
  ve onarım yap.
