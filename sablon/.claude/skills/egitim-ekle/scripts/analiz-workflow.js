// Workflow (paralel ajan) scripti: her ders için transkripti eksiksiz "Claude Analizi" metnine
// çevirir, transkriptle denetler, sorunluyu düzeltir. Tüm ajanlar Sonnet.
// args = {V: '<...RAW/VİDEOLAR klasörü>', OUT: '<...analiz çıktı klasörü>', dersler: [{no, base}, ...]}
export const meta = {
  name: 'egitim-claude-analizi',
  description: 'Eğitim transkriptlerini eksiksiz Claude Analizi metnine çevir, transkriptle denetle, sorunluyu düzelt',
  phases: [
    { title: 'Yaz', detail: 'her ders için transkriptten eksiksiz analiz metni' },
    { title: 'Denetle', detail: 'analiz ile transkripti karşılaştır: eksik, uydurma, kayma' },
    { title: 'Düzelt', detail: 'temiz çıkmayan analizleri yerinde düzelt' },
  ],
}
const YAZ = {type:'object', properties:{no:{type:'integer'}, yazildi:{type:'boolean'}, transkript_karakter:{type:'integer'}, analiz_karakter:{type:'integer'}, not:{type:'string'}}, required:['no','yazildi']}
const DENET = {type:'object', properties:{no:{type:'integer'}, temiz:{type:'boolean'}, eksik:{type:'array', items:{type:'string'}}, uydurma:{type:'array', items:{type:'string'}}, kayma:{type:'array', items:{type:'string'}}}, required:['no','temiz','eksik','uydurma','kayma']}
const DUZ = {type:'object', properties:{no:{type:'integer'}, duzeltildi:{type:'boolean'}, not:{type:'string'}}, required:['no','duzeltildi']}

const yazPrompt = (d, args) => `Görev: eğitim, ders ${d.no}: "${d.base}".
Transkript dosyası: ${args.V}/${d.base}.txt (Whisper ham çıktısı; her satır bir konuşma parçası, zaman damgası yok).
Çıktı dosyası: ${args.OUT}/${d.no}.md — Write aracıyla yaz (varsa üzerine yaz).

Ne yazacaksın: "Claude Analizi". Bu bir özet DEĞİL; transkriptin insan konuşmasından arındırılmış, eksiksiz yazılı kopyası. Sonradan bu eğitim hakkında sorulan sorular yalnız bu metinden cevaplanacak; metinde olmayan şey kaybolmuş sayılır.

Kurallar:
1. Eksiksizlik: derste konuyla ilgili söylenen her şey metinde olacak: her iddia ve gerekçesi, her adım, formül, kural, rakam, tarih, isim, araç, örnek, uyarı, öneri, soru-cevap. Anlatım sırası korunacak. "vb." veya "benzer örnekler" diye kısaltma yok; örnek varsa örnek yazılır.
2. Atılacaklar: dolgu sözleri, aynı şeyin tekrarı (tek kez yaz), selamlaşma ve kapanış, teknik aksaklık ("ses geliyor mu"), konu dışı sohbet, konuşma dili bozuklukları. Anlatıcının kendi hayatından verdiği örnekler konu dışı DEĞİLDİR, alınır.
2b. Kısaltma anlatımdan yapılır, bilgiden değil. Anlatıcı aynı sonuca çıkan bir şeyi üç satırda anlatmışsa sen tek cümlede yazarsın, ama o bilgi metinde durur. Şu dördü hiçbir koşulda kısaltılmaz ve atlanmaz: somut örnek (kişi, marka, film, olay adı), sayı ve ölçü (süre, fiyat, oran, adet), araç ve ürün adı, "şunu yapma" türü uyarı. Bir sıralama varsa bütün adımları yaz, ortadakini atlama.
3. Ekleme yok: transkriptte olmayan hiçbir bilgi, yorum, değerlendirme, öneri, uyarlama yazılmaz. Anlatıcının iddiası doğrudan yazılır ama yeni iddia üretilmez. Whisper'ın açıkça yanlış yazdığı bir terim veya isim varsa doğrusu yazılır; emin değilsen olduğu gibi bırak.
4. Dil ve biçim: düz Türkçe, yazı dili, kısa ve net cümleler; her cümle tek başına anlaşılır. Dersin doğal bölümlerine göre "### " alt başlıklar (en fazla 10). Madde listesi yalnız gerçekten sıralı adım veya liste için; normal anlatım paragraf. Kalın yalnız formül ve adı konmuş kavramlar için. YAML frontmatter yok; dosya "---" ile başlamaz; "#" ve "##" seviyesinde başlık kullanma.
5. Uzunluk: içerik neyi gerektiriyorsa; tipik olarak transkriptin %40-70'i. Kısa tutmak için içerik atma.
6. Dosyanın ilk satırı tam olarak şu biçimde: "NE ÖĞRETİYOR: " ardından dersin ne öğrettiğini söyleyen tek paragraf (en fazla 300 karakter, süs yok). Sonra bir boş satır, sonra analiz gövdesi.

Transkripti baştan sona oku (uzunsa parça parça, hiçbir bölümü atlamadan). Dosyayı yazdıktan sonra bir kez daha okuyup transkriptle kısaca karşılaştır: atladığın bölüm varsa ekle.

Dönüş (StructuredOutput): no=${d.no}, yazildi, transkript_karakter, analiz_karakter, not (varsa sorun: transkript bozuk, konu dışı bölüm, emin olunamayan terimler; yoksa boş).`

const denetPrompt = (d, args) => `Görev: Denetim. Ders ${d.no}: "${d.base}".
Transkript: ${args.V}/${d.base}.txt. Analiz: ${args.OUT}/${d.no}.md. Yalnız oku, hiçbir dosyayı değiştirme.

Analiz, transkriptin insan konuşmasından arındırılmış EKSİKSİZ kopyası olmalı: her iddia, adım, formül, rakam, isim, araç, örnek, uyarı ve öneri, aynı sırayla. Dolgu, tekrar, selamlaşma, teknik aksaklık ve konuşma bozuklukları atılmış olmalı; onların yokluğu hata değildir. Uzun anlatımın tek cümleye inmesi de hata değildir — bilgi durduğu sürece.

En sık kaçan dört şeyi ayrıca ara: somut örnek (kişi, marka, film, olay adı) genelleştirilmiş mi ("Breaking Bad" → "bir dizi"); sayı ve ölçü düşmüş veya bir kademesi atlanmış mı; araç ve ürün adı kaybolmuş mu; uyarı yumuşatılmış mı. Bunlar "üslup farkı" değil, eksiktir.

İkisini baştan sona oku (uzunsa parça parça) ve şunları çıkar:
- eksik: transkriptte olup analizde olmayan içerik (her madde tek cümle, transkriptteki ifadeye yakın; rakam ve isim varsa yaz). Üslup farkı ve atılması gereken dolgu eksik sayılmaz.
- uydurma: analizde olup transkriptte olmayan bilgi, yorum, öneri veya değiştirilmiş rakam/isim.
- kayma: anlamı transkriptten farklı aktarılmış yerler (örn. "yapmayın" → "yapın", koşulun düşmesi, rakamın yanlış birimi).
- temiz: üç liste de boşsa true, aksi halde false.
Şüphede kalırsan listeye yaz; gereksiz bir madde ucuz, kaçan bir madde pahalıdır.
Dönüş (StructuredOutput): no=${d.no}, temiz, eksik, uydurma, kayma.`

const duzeltPrompt = (d, v, args) => `Görev: Düzeltme. Ders ${d.no}: "${d.base}".
Transkript: ${args.V}/${d.base}.txt. Analiz dosyası: ${args.OUT}/${d.no}.md — Edit aracıyla yerinde düzelt.
Denetçi şu sorunları buldu:
EKSİK (transkriptte var, analizde yok): ${JSON.stringify(v.eksik)}
UYDURMA (analizde var, transkriptte yok): ${JSON.stringify(v.uydurma)}
KAYMA (anlam farkı): ${JSON.stringify(v.kayma)}
Her eksiği transkriptte bulup doğru yere, dosyanın üslubuyla (yazı dili, kısa cümle) ekle; her uydurmayı sil; her kaymayı transkripte göre düzelt. Denetçinin bir maddesi transkriptle çelişiyorsa transkript esas alınır, o maddeyi not'ta belirt. Dosyanın ilk satırı "NE ÖĞRETİYOR: ..." biçiminde kalsın; YAML frontmatter ekleme; dosya "---" ile başlamasın.
Dönüş (StructuredOutput): no=${d.no}, duzeltildi, not.`

const sonuc = await pipeline(args.dersler,
  d => agent(yazPrompt(d, args), {label: `yaz:${d.no}`, phase: 'Yaz', schema: YAZ, model: 'sonnet'}),
  (y, d) => (y && y.yazildi) ? agent(denetPrompt(d, args), {label: `denetle:${d.no}`, phase: 'Denetle', schema: DENET, model: 'sonnet'}).then(v => ({yaz: y, denet: v})) : {yaz: y, denet: null},
  (r, d) => (r.denet && !r.denet.temiz) ? agent(duzeltPrompt(d, r.denet, args), {label: `düzelt:${d.no}`, phase: 'Düzelt', schema: DUZ, model: 'sonnet'}).then(z => ({...r, duzelt: z})) : r,
)
const kisa = (s) => (s || '').slice(0, 160)
const toplam = args.dersler.length
const ozet = {yazildi: 0, denetlendi: 0, temiz: 0, duzeltildi: 0, sorunlu: [], notlar: []}
sonuc.forEach((r, i) => {
  const no = args.dersler[i].no
  if (!r || !r.yaz) { ozet.sorunlu.push({no, durum: 'yazılamadı'}); return }
  if (r.yaz.yazildi) ozet.yazildi++
  if (r.yaz.not) ozet.notlar.push({no, not: kisa(r.yaz.not)})
  if (r.denet) {
    ozet.denetlendi++
    if (r.denet.temiz) ozet.temiz++
    else ozet.sorunlu.push({no, eksik: r.denet.eksik.length, uydurma: r.denet.uydurma.length, kayma: r.denet.kayma.length, duzeltildi: r.duzelt ? r.duzelt.duzeltildi : false, not: kisa(r.duzelt && r.duzelt.not)})
  }
  if (r.duzelt && r.duzelt.duzeltildi) ozet.duzeltildi++
})
log(`yazıldı ${ozet.yazildi}/${toplam}, denetlendi ${ozet.denetlendi}, temiz ${ozet.temiz}, düzeltildi ${ozet.duzeltildi}`)
return ozet
