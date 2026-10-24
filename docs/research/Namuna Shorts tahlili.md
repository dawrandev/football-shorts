# Namuna Shorts tahlili (2026-10-24)

Foydalanuvchi yuborgan 10 ta Shorts kadrma-kadr ko'rib chiqildi:
- 20 kadrlik grid'lar;
- ffprobe metadata;
- kamera almashishlari (`scdet`);
- Whisper bilan ovoz tahlili.

Fayllar `data/references/` da (git'ga kirmaydi).

| ID | Kanal | Ko'rishlar | Uzunlik | Format | Turi | Sarlavha |
|---|---|---|---|---|---|---|
| ks07dnU6PU4 | UEFA | 19.9M | 18.5 s | 720×1280 | gol + Klopp reaksiyasi | This Liverpool team! 😮‍💨 |
| I5XdtMxhwY4 | UEFA | 10.4M | 15.6 s | 1080×1920 | Walcott yugurishi + assist | 99 pace, 99 dribbling |
| uM5RmeXaF70 | ballerjr | 7.6M | 32.7 s | 1440×1440 | Ronaldo Puskás goli, fan-edit | Puskas first winner💀 |
| MDeF_xql66E | 24h football | 7.2M | 24.0 s | 1080×1440 | skill kompilyatsiya, fan-edit | Insane skills💀⚽ |
| zprnx_wxA50 | UEFA | 6.5M | 13.1 s | 1080×1920 | yakka gol | Troy Parrott's solo goal |
| HX5sMqdfX3E | PSG | 3.5M | 10.9 s | 1080×1920 | assist + gol + quvonish | Magic from Dembélé. Finish from Ferran. ✨ |
| 9C6KurxI_eM | PSG | 2.0M | 21.5 s | 1080×1920 | jamoaviy hujum + gol | Pure football. 🤌 |
| 71LfBNHLeWg | PSG | 1.0M | 9.9 s | 1080×1920 | himoyadagi blok + quvonish | That passion! 😤🧱 |
| bCPHa3WUf-4 | CrossBar | 29K | 20.6 s | 1440×1440 | Neymar jarima zarbasi, fan-edit | That Swerve🔥 |
| DgR9ljTuWIw | OnlyBestGoals | 20K | 8.0 s | 1080×1920 | gol, blur fon | Kenan Yıldız "Il Del Piero Turco" |

## 1. Uzunlik va ritm — eng muhim farq

- **Uzunlik:** namunalar 8–33 s, mediana ~16 s. Bizning gol kliplarimiz 28–53 s, ya'ni ikki-uch barobar uzun.
- **Gol klipining tuzilishi (rasmiy UEFA/PSG):**
  - Klip hal qiluvchi harakat boshlanganda ochiladi: yakka yugurish yoki assistdan oldingi pas. Bu goldan 6–12 s oldin.
  - Gol klipning 60–80% qismiga to'g'ri keladi.
  - Keyin 2–5 s quvonish yoki reaksiya keladi. Bu bitta yaqin plan: gol muallifining yuzi yoki murabbiy (Klopp).
  - Takror deyarli yo'q. Bitta Shorts bitta ko'rinishdan iborat.
- **Kamera almashishi:** odatda 0–1 marta, jonli keng kadrdan quvonish kadriga. Fan-edit'larda ko'proq.
- **Xulosa:** foydalanuvchi "golgacha va goldan keyingi vaziyat uzoqroq" degan edi, namunalar buni tasdiqlaydi. Shorts uchun alohida qisqa profil kerak: goldan oldin ~8 s, keyin ~5 s, takror yo'q. Takror va to'liq versiya alohida qoladi.

## 2. Kadr: 9:16 crop, harakat ortidan

- **Rasmiy kanallar (7 tadan 6 tasi):** to'liq 9:16 crop, kadr to'p va o'yinchi ortidan suriladi.
  - Zoom oddiy 9:16 crop'dan ham kuchliroq. Keng kadrda o'yinchi kadr balandligining ~15% ini egallaydi, bu taxminan 1.5–2× zoom.
  - Ular toza 4K signaldan kesadi. Bizda 1080p bor, shuning uchun zoom 1.0–1.5× oralig'ida moslashuvchan bo'lishi kerak.
- **DgR9:** 16:9 kadr markazda, ustida va ostida xiralashtirilgan zoom fon. Bu bizdagi `blur` zaxira layout'i bilan bir xil.
- **Fan-edit'lar:** kvadrat (1:1) yoki 3:4.
- **Hisob paneli:** odatda kadrda yo'q, chunki crop uni kesib tashlaydi. Bizda ham shunday bo'ladi. Hisobni o'zimizning chiroyli overlay'imiz bilan beramiz.

## 3. Yozuvlar

- **Hook matni.** Kadrning yuqori yoki o'rta qismida kichik oq matn va bitta emoji turadi. U birinchi ~50–60% davomida ko'rinadi, keyin yo'qoladi. Misollar:
  - "Incredible solo goal 🤩"
  - "Dembélé x Ferran again 😤"
  - "Try and catch Walcott 🥵"
  - "Wait for Klopp's reaction..."
  - "Only two touch allowed 😮"

  Hook vazifasi tomoshabinni oxirigacha ushlab turish ("wait for...").
- **O'yinchi nomi teglari.** PSG va UEFA'da o'yinchi ustida kichik oq yozuv uchib yuradi ("FERRAN", "MASCHERANO", "DOUÉ"). Fan-edit'da qizil yonib turgan nom va strelka ("DEMBÉLÉ ▼"). Buning uchun o'yinchini kuzatish (M4) va kimligini bilish kerak. Bu M6 darajasidagi ish.
- **Hikoya matni.** Faqat fan-edit'da: "The goal that made FIFA create the Puskás award".
- **"GOAL" animatsiyasi.** Hech birida yo'q. Professional kanallar katta animatsiya ishlatmaydi. Ta'sirni kesish, reaksiya va hook beradi.

## 4. Ovoz

- **Sharhlovchi ovozi** 10 tadan hech birida yo'q (Whisper nutq topmadi).
  - Rasmiy kanallar: toza stadion ovozi va musiqa.
  - Fan-edit'lar: musiqa ("Why, why, why…", "Ow, ow…").
- **Bizdagi muammo:** sharh ovozi kadrga yopishgan.
- **Yechim:** Demucs (MIT) yoki shunga o'xshash manba ajratish bilan sharhni (vocals) olib tashlash, stadion shovqinini qoldirish va ustidan musiqa qo'yish. Musiqa litsenziyasi uchun YouTube Audio Library yoki Shorts ilovasidagi musiqa ishlatiladi.

## 5. Sarlavhalar

- Qisqa (2–7 so'z), o'yinchi atrofida, his-tuyg'u va emoji: "Magic from Dembélé. Finish from Ferran. ✨", "That Swerve🔥", "99 pace, 99 dribbling".
- Bizning sarlavha generatori `ReplayEvent` maydonlaridan (tur, o'yinchi, jamoalar) shu uslubda ishlaydi. LLM bir nechta variant beradi, ismlar roster bilan tekshiriladi.

## 6. Fan-edit uslubi (ikkinchi navbat)

- Boshida o'yinchi yuzining yaqin plani.
- Zarba paytida slow-motion.
- Rang grading: kontrast va vinyetka.
- Oxirida qorong'ilashib tugash.
- Zoom-in va o'tishlar.

Bular avtomatlashtirsa bo'ladigan effektlar, lekin rasmiy uslubdan keyin.

## 7. Bizning pipeline'ga xulosa (ustuvorlik bo'yicha)

1. **M4 reframe:** 9:16 crop, to'p va o'yinchi ortidan, moslashuvchan zoom, silliq harakat. Namunalarning 6 tasi shunga tayanadi.
2. **Shorts profili:** 10–25 s.
   - Gol: −8 / +5 s, oxirida bitta reaksiya kadri.
   - Xavfli vaziyat: −8 / +3 s.
   - Takror va to'liq versiya alohida fayl.
3. **Ovoz:** sharhni olib tashlash va musiqa qo'yish.
4. **Hook matni + sarlavha:** LLM'dan, hook birinchi yarmida ko'rinadi.
5. **O'yinchi nomi teglari:** tracking + identifikatsiya.
6. **Fan-edit effektlari:** slow-mo, grading.
