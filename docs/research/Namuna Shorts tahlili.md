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

## 8. Aniq vaqt o'lchovi (2026-10-28)

Har bir gol namunasi 2 fps kadrlarda ko'rib chiqildi. "Gol" = to'p to'rga kirgan lahza.

| Namuna | Goldan oldin | Goldan keyin | Keyingi qism nima | Hook ko'rinadi |
|---|---|---|---|---|
| HX5sMqdfX3E | 6.7 s | 4.2 s | quvonish yaqin plani | 0–4.5 s |
| 9C6KurxI_eM | 16.7 s | 4.8 s | quvonish | 0–2.5 s |
| zprnx_wxA50 | 12.7 s | 0.4 s | — | 0–6 s |
| ks07dnU6PU4 | 15.0 s | 3.5 s | Klopp reaksiyasi | 0–9 s |
| I5XdtMxhwY4 | 15.5 s | ~0 s | — | 0–5.5 s |
| 71LfBNHLeWg | ~6.5 s | 3.4 s | quvonish | 0–4.5 s |
| DgR9ljTuWIw | ~6 s | ~2 s | — | — |

Mediana: goldan oldin 12.7 s, keyin 3 s, jami ~16 s. Hook klipning birinchi ~45% qismida turadi.

**Bizning qaror (`config.yaml` → `shorts`):**
- Gol: aniq gol lahzasidan −12 s / +4 s, oxirida bitta reaksiya kadri.
- Xavfli vaziyat va skill: −9 s / +2 s, takror boshlanguncha.

**Aniq gol lahzasi.** Hisob paneli asl goldan 0–6 s kech yangilanadi, buni BRA–KOR'ning 5 golida kadrma-kadr tekshirdim. Stadion hayqirig'i to'p to'rga kirgandan ~1.5 s keyin eng baland nuqtaga chiqadi. Qoida: gol lahzasi = hisob o'zgarishidan −15…+3 s oraliqdagi ovoz cho'qqisi − 1.5 s. Masalan Richarlison goli: kadrda −6.0 s, qoida bo'yicha −6.2 s.

## 9. Top-30 futbol Shorts tahlili (2026-10-28)

**Manba.** 12 ta yirik kanalning (UEFA, FIFA, PSG, Real Madrid, Barcelona, Man City, 433, B/R Football, OneFootball, ESPN FC, Premier League) Shorts bo'limidan oxirgi 60 tadan, jami 660 ta Short olindi. Ko'rishlar bo'yicha saralandi, o'yindan tashqari videolar (kiyinish xonasi, reklama, oila) chiqarildi. Qolganlardan 29 tasi yuklab olindi: 1.1M–14M ko'rish. Ro'yxat `data/references/top/top30.json`, o'lchovlar `metrics.json` da.

**Raqamlar:**

| O'lchov | Natija |
|---|---|
| Uzunlik | mediana **10.1 s**, p25 7.7 s, p75 15.9 s; 4.7–34.5 s |
| Kamera almashishi | mediana **0**; 29 tadan 21 tasi bitta uzluksiz lahza |
| Ovoz | UEFA, klublar, PSG: sharhsiz (stadion shovqini yoki musiqa); Premier League: sharh saqlangan |
| Format | hammasi to'liq 9:16 kadr, xira fonli bandlar yo'q |

**Yozuvlar (asosiy xulosa):**
1. **Bitta qisqa jumla + emoji**, kichik, oq, qalin. Quti yo'q, faqat yengil soya. Kadr o'rtasi va pastki qismi orasida, taxminan 55–70% balandlikda. Misollar: "Most satisfying finish ever? 😮‍💨", "Sommer foot save 🤯", "Chaotic second goal 🤣", "Harry Kane's goal-kick 🤯", "Halfway line goal 🤯", "Pure chaos", "Iconic.".
2. **Ikki bosqichli matn** (setup → punchline): "Try to take the ball off João Neves" → "Impossible", "Dominik Szoboszlai's recovery speed" → "Here he comes!", "How long can they keep the ball in the air?" → "Let's try again…".
3. **Kutish (teaser) matni:** "Wait for Mbappé's pace 🤯", "The score… 👀", "Zion Suzuki appeared out of NOWHERE…". Oxirigacha ko'rishga undaydi.
4. **Teskari sanoq va spotlight:** "Bouaddi magic in 5… 3… 2…", o'yinchi atrofida yorug' doira, qolgan qism qoraytirilgan.
5. **O'yinchi nomi tegi:** kichik oq yozuv o'yinchi ustida (HAZARD, MARCELO, FABIAN, DOUÉ, SZOBOSZLAI).
6. **Grafikalar:** masofa belgilari (7 m → 28 m → 47 m → 51 m), sekundomer (00:13), doira va spotlight.
7. **Davomiyligi:** ko'pincha birinchi 40–70% qismda turadi, ba'zan butun klip davomida.
8. **Hisob paneli:** UEFA telekanalning o'z panelini qoldiradi (masalan "87:10 SAB 1-0 SLA"), Premier League o'z panelini qo'yadi. Ko'pchilikda esa hisob umuman ko'rsatilmaydi.
9. **Katta "GOAL" animatsiyasi:** 29 tadan hech birida yo'q.
10. **Kanal belgisi:** kichik logotip burchakda (LALIGA, PL sheri, klub gerbi).

**Video:**
- **Bitta lahza, bitta kadr.** Klip harakat boshlanishidan (yugurish, pas) natijagacha davom etadi. Gollarda oxirida 1–2 s quvonish yaqin plani bo'ladi: Doué, Ferran, Brighton.
- **Kadr.** To'liq 9:16 crop. Ba'zilari juda yaqin (Yamal, Doué), ko'pchiligi esa ancha keng: bir vaqtning o'zida 6–10 o'yinchi ko'rinadi. Ular 4K signaldan kesadi.
- **Sekinlashtirish va zoom.** Skill kliplarida sekinlashtirilgan takror yoki yaqin zoom (Doué vs Lamine, Ndiaye).
- **Rang.** Ba'zan oxirida qoraytirish yoki vinyetka (PSG "Impossible").

**Bizga xulosa (taklif):**
1. Shorts uzunligini qisqartirish: gol 10–16 s, vaziyat 7–10 s. Bizda hozir 11–20 s.
2. Hook uslubi: bitta qisqa jumla, teaser yoki ikki bosqichli variant. Kichikroq shrift, video ustida 60% balandlikda, quti va band yo'q.
3. "GOAL!" belgisini kichraytirish yoki olib tashlash. Top Shorts'da bunday belgi yo'q.
4. Hisob panelini ixtiyoriy qilish va kichraytirish.
5. O'yinchi nomi tegi: tracker va ism bor, qo'shish mumkin.
6. Spotlight doira va sekinlashtirish: skill va xavfli vaziyatlar uchun.
7. Layout: foydalanuvchi keng kadrni yoqtirgan, top Shorts esa to'liq 9:16. Ikkalasini baholash saytida solishtirish kerak.
