---
name: hatirla
description: Geçmiş bir konuşmayı, kararı, rakamı veya olayı bulur. "hatırla", "ne konuşmuştuk", "ne zaman karar vermiştik", "geçen hafta ... demiştik", "daha önce ... yapmış mıydık" dendiğinde kullan.
---
# Hatırla

Önce soruyu ikiye ayır. Hangi yoldan gideceğin soru türüne bağlı.

## 0. Bağlamdakine bak

Son Oturum, Açık Konular, Kurallar ve indeksin son satırları zaten önünde. Cevap oradaysa hiç dosya açma.

## A yolu — kavram sorusu

"X hakkında ne biliyoruz", "şu konuda ne konuşmuştuk", "neden öyle yapmıştık" gibi sorular. Damıtılmış bilgi arıyorsun, tek bir cümle değil.

- `BİLGİ/index.md` tablosunda anahtar kelimeyi ara. Tablo satırı şu düzende: makale adı, özet, kaynak günlük, güncellenme tarihi.
  ```bash
  grep -n -i "tedarikçi\|fiyat" "BİLGİ/index.md"
  ```
- Eşleşen makaleyi oku: `BİLGİ/kavramlar/<Başlık>.md`. Cevabı buradan ver.
- Ayrıntı gerekiyorsa makalenin `## Kaynaklar` bölümündeki günlük tarihlerine git, o günün `GÜNLÜK/<tarih>.md` dosyasını oku.
- Makale yoksa B yoluna geç.

## B yolu — tarih, rakam veya tam alıntı sorusu

"Ne zaman", "kaç para", "tam olarak ne demişti" gibi sorular. Kesin veri arıyorsun; damıtılmış özet bunu kaybeder.

- Önce `GÜNLÜK/` içinde ara. İki üç anahtar kelime seç, önce hangi günlerde geçtiğini bul, sonra o günü oku.
  ```bash
  grep -rn -i -l "tedarikçi" GÜNLÜK/ | sort
  grep -n -i -B2 -A12 "fiyat listesi" GÜNLÜK/2026-01-15.md
  ```
- Dosya adı tarihtir (`2026-01-15.md`); içe aktarılan eski sohbetler `import-YYYY-AA-part-NNN.md`.
- Günlükte yoksa `BİLGİ/index.md` üzerinden kavram makalesine bak.

## Diğer kaynaklar

- Proje sorusuysa: `PROJELER/<Proje>/<Proje> Kararlar.md` (tarihli kararlar ve gerekçeleri) ve `PROJELER/<Proje>/<Proje> — Proje.md`.
- Alan sorusuysa: alan klasöründeki `<Ad> Kararlar.md` ve `<Ad> Context.md`.
- Hâlâ yoksa kök `index.md` üzerinden el yazısı notlara bak.

## Kaynak vermek zorunlu

Her cevabın sonunda nereden geldiğini yaz: kavram makalesinin adı ve günlük tarihi.

Örnek: "Bu karar 15 Ocak'ta alınmış. Kaynak: [[Tedarikçi Fiyat Anlaşması]], GÜNLÜK/2026-01-15.md".

## Makale eskiyse

Kavram makalesi vardır ama içindeki bilgi günlükten eski olabilir. Makaledeki "güncellendi" tarihi, konuyu geçen günlük dosyasının tarihinden eskiyse **günlüğe güven**.

O durumda:
- Cevabı günlükteki yeni bilgiden ver, makalenin eskidiğini bir cümleyle söyle.
- `HAFIZA/Çelişki Adayları.md` dosyasına tarihli bir madde ekle:
  `- [YYYY-AA-GG] çelişki: <makale adı>: eski "<...>" / yeni "<...>" — kaynak: <günlük dosyası>`
- Aynı anlamda bir madde zaten varsa tekrar ekleme.

## Bulamazsan

Tahmin etme. "Bulamadım, nerede olduğunu biliyor musun?" de.

Hafızadaki sayıya körü körüne güvenme: iş yapmadan önce gerçek durumu say (Kurallar).
