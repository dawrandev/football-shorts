# Football Shorts — reja

**Maqsad:** to'liq futbol match videosi kiradi, tayyor vertikal (1080×1920) Shorts/Reels chiqadi. Gollar, xavfli vaziyatlar va yaxshi hujumlar avtomatik topiladi, kliplar foydalanuvchi tanlagan uzunlikda kesiladi, kadr to'p ortidan yuradi va ustiga "GOAL" animatsiyasi, klub nomlari va hisob qo'shiladi.

**Bosqichlar:** avval o'zimiz CLI orqali ishlatamiz. Keyinroq shu yadroning ustiga sayt (API + navbat) quriladi va odamlarga ochiladi.

Tadqiqot hisobotlari `docs/research/` papkasida.

---

## 1. "Model" degani bu yerda nima

Bu loyihada bitta katta model yo'q. Bu **pipeline**, ya'ni ketma-ket ishlaydigan modullar zanjiri. Laravel'dagi Job zanjiriga o'xshaydi, ammo bu loyihada Laravel analogiyalarini kamroq ishlatamiz.

| Qism | Kim qiladi | O'zimiz o'qitamizmi? |
|---|---|---|
| Gol topish | Ekrandagi hisobni o'qish: EasyOCR + bizning mantiq | Yo'q, tayyor OCR yetadi |
| Xavfli vaziyat | Ovoz balandligi (librosa) + sharhlovchi so'zlari (faster-whisper) | Yo'q |
| Kesish chegarasi | Kamera almashishi (PySceneDetect) | Yo'q |
| To'pni topish | RF-DETR detektori | **Ha**, to'p va o'yinchilar datasetida fine-tune qilamiz. Bu birinchi "o'z modelimiz" bo'ladi |
| Lahzalarni tartiblash | Qoidalar, keyinroq ixtiyoriy Gemini | Keyinroq: o'z ma'lumotlarimizda kichik klassifikator |
| Render | FFmpeg + NVENC | Yo'q |

Pipeline ishlagan sari biz qo'lda tasdiqlagan yoki rad etgan kliplar o'z datasetimizga aylanadi. Keyinroq shu dataset ustida o'zimizning "highlight klassifikatori"ni o'qitamiz. Tadqiqot ko'rsatdiki, SoccerNet weights'ni tijoriy maqsadda ishlatib bo'lmaydi, shuning uchun dataset o'zimizniki bo'lishi kerak.

## 2. Texnik qarorlar

- **Muhit:** mavjud `C:\Users\dawra\ai-env` (Python 3.12, PyTorch cu130, RTX 5090). Paketlarni o'rnatish buyruqlarini men beraman, siz ishga tushirasiz.
- **Litsenziyalar:** Ultralytics YOLO (AGPL) va SoccerNet weights ishlatilmaydi. Ruxsat etilganlar: RF-DETR (Apache 2.0), supervision (MIT), EasyOCR (Apache 2.0), faster-whisper (MIT), PySceneDetect (BSD), FFmpeg.
- **Arxitektura:** `src/fshorts/` ichida har bir bosqich interfeys orqali almashtiriladigan modul bo'ladi. Masalan, `EventSource` interfeysi uchta implementatsiyaga ega bo'ladi: OCR, audio va API. Har bir bosqich natijasi JSON qilib saqlanadi, shuning uchun bosqichni alohida qayta ishga tushirish mumkin. Kelajakdagi sayt shu yadroni chaqiradi.
- **Konfiguratsiya:** `config.yaml` fayli. Unda klip uzunligi (oldin/keyin soniyalari), format (crop/blur), shrift va ranglar, hamda har bir telekanal uchun hisob panelining joylashuvi (ROI preset) saqlanadi.
- **Tekshiruv:** har bir milestone uchun 3 ta test match bo'yicha qo'lda belgilangan "to'g'ri javoblar" (`tests/ground_truth/*.json`) yoziladi va natija ular bilan solishtiriladi.

```
football-shorts/
  config.yaml
  src/fshorts/
    ingest/      # video probe, audio extract, frame sampling
    events/      # ocr_score.py, audio_peaks.py, asr_keywords.py, fusion.py
    clipping/    # windows, scene snap
    reframe/     # detector, ball tracker, smoothing, crop path
    render/      # ffmpeg layouts, overlays, captions
    cli.py
  tests/
  data/          # matches, outputs (gitignored)
  docs/
```

## 3. Milestones

Har bir milestone tugagach to'xtaymiz, natijani ko'rsataman va keyingisi uchun ruxsatingizni kutaman.

**M0 — Tayyorgarlik (1 kun)**
- Loyiha skeleti, git, `.gitignore` (videolar repoga kirmaydi), `config.yaml`.
- FFmpeg (NVENC bilan) o'rnatilganini tekshirish.
- Siz **3 ta test match** faylini `data/matches/` papkasiga qo'yasiz. Ideal holatda har biri boshqa telekanaldan, to'liq 90 daqiqalik va mp4 formatida bo'lsin.
- Har bir match uchun gol daqiqalarini qo'lda yozib chiqamiz. Bu "ground truth" bo'ladi.
- ✅ Tayyor: `fshorts probe match.mp4` buyrug'i videoning davomiyligi, fps va o'lchamini chiqaradi.

**M1 — Nomzod lahzalar (2–3 kun)**
- Audio ajratiladi, ovoz balandligi (RMS) va spectral flux bo'yicha peak'lar topiladi.
- faster-whisper "gol", "goal", "penalty" kabi kalit so'zlarni qidiradi. Sharhlovchi o'zbek, rus yoki ingliz tilida bo'lishi mumkin.
- ✅ Tayyor: `candidates.json` fayli. Unda ground truth'dagi gollarning ≥90% bor, va nomzodlar soni bir match uchun 60 tadan oshmaydi.

**M2 — Gol tasdiqlash (2–3 kun)**
- Hisob paneli joyi (ROI) har telekanal uchun bir marta belgilanadi va preset sifatida saqlanadi.
- Hisob 1 fps tezlikda OCR qilinadi. Debounce qo'llanadi: yangi hisob 3 marta ketma-ket o'qilsagina qabul qilinadi. Bekor qilingan gol (VAR) ham hisobga olinadi.
- Ekrandagi match soati ham o'qiladi, shu orqali videodagi vaqt match daqiqasiga bog'lanadi.
- ✅ Tayyor: 3 ta test match'da gollarning **100%** topiladi va noto'g'ri gol 0 ta.

**M3 — Avtomatik kesish (1–2 kun)**
- Klip oynasi config'dan olinadi, masalan goldan 12 soniya oldin va 6 soniya keyin. Kerak bo'lsa replay qo'shiladi.
- Klip chegaralari PySceneDetect yordamida kamera almashgan joyga moslanadi.
- ✅ Tayyor: `fshorts cut match.mp4` buyrug'i 16:9 kliplarni va `clips.json` faylini chiqaradi. Kliplar o'rtasida uzilib qolmaydi.

**M4 — 9:16 reframe + birinchi o'z modelimiz (3–5 kun)**
- **Model:** RF-DETR'ni ochiq litsenziyali to'p/o'yinchi datasetida fine-tune qilamiz. Litsenziyani avval tekshiramiz.
- **Kuzatish:** `BallTracker` va One-Euro filter. Kadr markazida "o'lik zona" bo'ladi, unda kadr qimirlamaydi. Kamera almashganda kuzatish qaytadan boshlanadi.
- **Zaxira:** to'p yo'qolsa, kadr xiralashtirilgan fonli formatga o'tadi.
- ✅ Tayyor: 10 ta klipda kadr to'pni ushlab turadi va silkinmaydi. Buni birga ko'rib baholaymiz.

**M5 — Brending va eksport (2–3 kun)**
- "GOAL" animatsiyasi (alpha kanalli .mov), klub nomlari, logolar va hisob.
- Whisper natijasidan subtitr chiqadi.
- Eksport parametrlari: `h264_nvenc`, 1080×1920, ~12 Mbps.
- ✅ Tayyor: `fshorts run match.mp4` bitta buyruq bilan yuklashga tayyor Shorts beradi. Bitta match RTX 5090'da 25 daqiqadan kam vaqtda ishlanadi.

**M6 — Ixtiyoriy kengaytmalar (keyin kelishamiz)**
- Gemini lahzalarni tartiblaydi va sarlavha yozadi.
- Nashrdan oldin kliplarni ko'rib, tasdiqlash yoki rad etish uchun oddiy UI.
- Tasdiqlangan yoki rad etilgan kliplardan o'z highlight klassifikatorimiz uchun dataset yig'iladi.
- Keyin sayt: API, ishlar navbati va foydalanuvchilar.

## 3a. Strategiya yangilanishi (2026-10-22)

`docs/research/Futbol highlight model strategiyasi.md` hisobotidan keyin rejaga quyidagilar qo'shildi:
- **Dataset yig'ish M1'dan boshlanadi.** M2 OCR natijasini "weak label" sifatida saqlaydi. M3 ga oddiy review CLI qo'shiladi (accept/reject + sabab), u PLAN'da avval M6'da edi.
- **M4 to'rt qismga bo'lindi.**
  - **M4a:** RF-DETR-M bilan prototip.
  - **M4b:** o'z kadrlarimiz belgilanadi (Grounding DINO + SAM2 → CVAT) va RF-DETR qayta o'qitiladi.
  - **M4c:** to'p uchun 3 kadrli heatmap modeli (WASB uslubida).
  - **M4d:** kadr qayerga qarashi tartib bilan tanlanadi: to'p, u ko'rinmasa Kalman bashorati, keyin o'yinchilar markazi, oxirida kadr markazi. Natija offline silliqlanadi.
- **M6 qadamlari:**
  - **M6a:** LightGBM ranker. U muzlatilgan encoder feature'lari (V-JEPA 2, SigLIP2/DINOv2, audio) va bizning signallarimiz ustida o'qitiladi.
  - **M6b:** Qwen3-VL lokal labeler.
  - **M6c:** Gemini faqat runtime'da ishlaydi, uning javoblari training'ga kirmaydi.
  - **M6d:** temporal head.
  - **M6e:** sayt.
- **Litsenziya qoidalari:**
  - **Ishlatilmaydi:** VideoMAE V2 weights (NC), DEIMv2 (2026-08 dan NC), RF-DETR XL/2XL (PML), Ultralytics va YOLOv10/12/13 (AGPL), SoccerNet'da o'qitilgan weights.

## 3b. Natijalar

- **M0 ✅** skelet, `fshorts probe`, NVENC tekshirildi.
- **M1 ⚠️ 16/18 gol (89%) ≤50 nomzod bilan**, 3 ta FIFA match'da, maqsad ≥90% edi.
  - **Ishlash vaqti:** bir match ~90 s (Whisper large-v3-turbo + audio).
  - **Manbalar:** asosiy signal sharhlovchi iboralari. FIFA arxiv ovozida stadion hayqirig'i golni shovqindan ajratmaydi (gollarda +3.6–6 dB, oddiy kadrlarning p90'i esa 4 dB).
  - **Tushib qolgan 2 gol:** ikkalasida ham sharhlovchi gol iborasini aytmagan va ovoz piki bo'lmagan. Ularni M2 (hisob o'zgarishi) qoplaydi.
  - **Tuning:** shu 3 match'ga moslab sozlash to'xtatildi, overfitting xavfi bor.
- **M2 ✅ 18/18 gol, 0 noto'g'ri gol**, 3 ta match'da (2018 va 2022 grafikalari).
  - **Usul:** EasyOCR yuqori chap 1000×140 hududni 1 fps tezlikda o'qiydi va ikki jamoa kodi orasidagi raqamlarni oladi. Layout'ga bog'lanmagan, FIFA banneri panelni surganda ham ishlaydi.
  - **Debounce:** yangi hisob 3 marta ketma-ket o'qilsa qabul qilinadi. VAR bekor qilsa, gol o'chiriladi.
  - **Aniqlik:** hisob o'zgarish vaqti gol vaqtidan −13…+70 s farq qiladi. Katta farq panel takror ko'rsatilayotganda yashirin turgan hollarda bo'ladi.
  - **Vaqt:** bir match uchun ~5–6 daqiqa (OCR har sekundda). Keyin tezlashtirish mumkin: panel kadrlar orasida o'zgarmasa, OCR o'tkazib yuboriladi.
  - **Weak label:** `goals.json` + `score_readings.json` (soat bilan) match workspace'ida saqlanadi.
- **M3 ✅ `fshorts cut` + `fshorts review`.** 3 ta match'dan 18 ta gol klipi va 45 ta xavfli vaziyat klipi chiqdi. Bir match ~55 s'da kesiladi (NVENC).
  - **Gol lahzasi:** odatda hisob o'zgargan vaqt olinadi. Panel uzoq yashirin turgan bo'lsa, oraliqdagi kuchli sharhlovchi reaksiyasi ishlatiladi. Nacho goli: 3701 s, belgi 3698 s.
  - **Gol klipi:** −20/+8 s, ustiga takror. Panel yashirin turgan oraliq takror deb olinadi, ≤25 s.
  - **Xavfli vaziyatlar:** kliplar −12/+6 s, gol kliplari bilan ustma-ust tushmaydi. Faqat panel ko'ringan oraliqdan olinadi, ya'ni studiya suhbati kirmaydi. "4-4-2" kabi sxemalar hisob deb sanalmaydi.
  - **Kamera almashishi:** chegaralar FFmpeg `scdet` topgan joylarga suriladi. Boshlanish faqat oldinga, tugash faqat keyinga suriladi.
  - **Review:** klip pleyerda ochiladi, y/n va sabab kiritiladi. Natija `data/labels/human/<match>.json` ga yoziladi, keyingi modelning training ma'lumoti shu bo'ladi.

## 3c. M3.5 — klip sifati (2026-10-24)

Siz ko'rib chiqqan birinchi kliplar bo'yicha baholaringiz `data/labels/human/` ga yozildi (24 ta klip).
Asosiy muammo: "xavfli vaziyat" kliplarining ~70% i bo'sh edi. Sharhlovchi statistika va eski gollar haqida gapirgan joylar ham "gol" so'zi uchun tanlanib qolgan. Research: `docs/research/Klip sifati va xavfli vaziyatlar.md`.

**Yangi usul — takror (replay) asosida:**
- **Hisob paneli shabloni.** OCR o'qigan kadrlardan har bir match uchun panel shabloni o'rganiladi va har kadrda panel bor-yo'qligi solishtiriladi. Bu OCR'dan ishonchliroq: match oxirida OCR o'qimagan joylarda ham panelni topadi.
- **Kadr turi.** SigLIP2 zero-shot har kadrni ajratadi: keng kadr, yaqin plan, tribuna/skameyka, logotip, darvoza oldi.
- **Takror = panel yo'q, 3–60 s.** Rejissyor faqat muhim lahzani takrorlaydi. Takrordan oldingi oxirgi jonli keng kadr zarba vaqti hisoblanadi.
- **Eski takrorlarni ajratish.** Avval efirga chiqqan kadrlar qayta ko'rsatilsa, ular piksel bo'yicha bir xil bo'ladi. 64×36 thumbnail solishtirish shuni topadi.
- **Takror turini aniqlash.** Lokal Qwen3-8B (Apache-2.0) takror atrofidagi sharhni o'qiydi va nima bo'lganini aytadi: seyv, darvozadan tashqari zarba, blok, ustun, skill, fol, ofsayd va hokazo. O'yinchi nomini ham beradi.

**Kategoriyalar:** `goal`, `goal_replay`, `chance`, `chance_replay`, `skill`, `skill_replay`.

**Chegara qoidalari:**
- Klip takror qoldig'i, skameyka yoki tribuna kadri bilan boshlanmaydi.
- Xavfli vaziyat klipi zarbadan 4 s keyin tugaydi, takror boshlanishidan oldin.
- Kamera almashishiga surish takror chegarasidan o'tmaydi.
- Gol oldidagi penalti va gol takrorlari golga tegishli bo'ladi.

**Keyingi qadamlar (rejada):**
1. **Kadr turi modelini o'qitish.** Zero-shot o'rniga SigLIP2 embedding ustida linear probe, o'z belgilangan kadrlarimiz bilan.
2. **Takrorsiz lahzalar.** Masalan Vini skill'i: sharhni LLM bilan sirpanuvchi oynada o'qish.
3. **Nomlash.** Ikki jamoa tarkibini Whisper'ga prompt qilish, ismlarni roster bilan fuzzy-match qilish, sarlavha shablonlari ("Vini highlight BRA vs KOR").
4. **Vizual spotting.** V-JEPA 2 / SigLIP2 xususiyatlari ustida temporal head, labellar ko'paygach. LightGBM ranker.
5. **Namuna Shorts tahlili ✅** `docs/research/Namuna Shorts tahlili.md`. Asosiy xulosalar:
   - Shorts 10–25 s bo'ladi. Gol: −8/+5 s va bitta reaksiya kadri, takrorsiz.
   - 9:16 crop harakat ortidan yuradi (M4).
   - Sharh ovozi yo'q: stadion shovqini va musiqa.
   - Boshida hook matni, o'yinchi ustida nom teglari.
   - Katta "GOAL" animatsiyasi ishlatilmaydi.
6. **Eslatma:** gol kliplari uzunligi bo'yicha funksiyani siz tushuntirasiz.

## 3d. M4a — birinchi 9:16 reframe (2026-10-24)

- **Buyruq:** `fshorts vertical <match> [--kinds goal,chance]`. Kesilgan kliplardan `vertical/` papkasiga 1080×1920 NVENC fayllar chiqadi.
- **Detektor:** RF-DETR Medium (Apache-2.0, COCO) fp16 + batch 8, 11.7 ms/kadr, klip bo'ylab 10 fps.
  - O'yinchilar juda yaxshi topiladi (keng kadrda 15–22 ta).
  - To'p faqat ~40% kadrda topiladi. Shuning uchun o'z to'p modelimiz (M4c) hali kerak.
- **Kadr markazi:**
  1. To'p (75%) va unga yaqin o'yinchilar markazi (25%).
  2. Yaqin plan bo'lsa, katta odam markazda.
  3. Bo'shliqlar interpolatsiya bilan to'ldiriladi.
  4. Har kamera kadri alohida Gauss bilan silliqlanadi (0.6 s), kesishda kadr to'g'ridan-to'g'ri sakraydi.
- **Hisob paneli:** zoom 1.15 va tepadagi 10% chiziq crop'dan tashqarida, shuning uchun telekanal paneli kadrga kirmaydi.
- **Zaxira:** kuzatish kam bo'lsa (`min_coverage`), xiralashtirilgan fonli layout ishlatiladi.
- **Natija:** BRA–KOR'ning 19 ta gol va xavfli vaziyat klipi ~105 s'da tayyor bo'ldi (detection keshda).
- **Keyingi qadamlar:**
  - M4b/c: o'z kadrlarimizni belgilab, to'p uchun RF-DETR fine-tune yoki 3 kadrlik heatmap model.
  - Moslashuvchan zoom.
  - 10 ta klip bo'yicha sifat bahosi.

## 3e. Video sifati va o'z to'p modelimiz (2026-10-26)

**Sifat.** Manba YouTube 1080p VP9, ~3.5 Mbit/s. Yuqoriroq formati faqat Premium uchun.
- Vertikal endi to'g'ridan-to'g'ri match faylidan yasaladi: bitta kodlash, avval ikki marta edi.
- Kattalashtirish Lanczos bilan, ustidan yengil unsharp.
- NVENC: p7/hq, CQ 18, AQ, ~18 Mbit/s.

**To'pni kuzatish.**
- 3×2 tile'larda qidirish: tayyor model to'pni jonli kadrlarning 75% idan 92% igacha topadi.
- Constant-velocity tracker qo'lqop, bosh va butsani rad etadi.
- To'p ko'rinmasa, TV kamera markaziga tayaniladi.

**O'z to'p modelimiz (self-training).**
- `fshorts balldata`: kesmali detektor + tracker tasdiqlagan to'plar avtomatik label bo'ladi. 2 match'dan 2846 train va 312 valid tile, BRA–KOR faqat test uchun. Label aniqligi ~93% (30 namunadan 28 tasi).
- `fshorts trainball`: RF-DETR Medium fine-tune, 640 px, 20 epoch, ~15 daqiqa. Eng yaxshi val mAP 0.774.
- O'qitishda ishlatilmagan BRA–KOR match'ida, 19 ta klip:
  - to'p topilgan kadrlar 45.9% → 51.3%;
  - to'p 9:16 oyna ichida 94.3% → 95.3%;
  - ishonch 0.5–0.6 → 0.85–0.93;
  - 30 namunadan 27 tasida haqiqiy to'p.
- Keyingi qadamlar: ikkinchi self-training raundi, xatolar (butsa, logotip) hard-negative bo'ladi, ko'proq match qo'shiladi.

## 3f. Keng kadr, super-resolution, ovoz (2026-10-26)

**`wide` layout (standart).**
- To'p ortidan yuradigan 4:5 nisbatli oyna 9:16 ekranning o'rtasida turadi, tepa va pastki qismi oynaning xiralashtirilgan nusxasi bilan to'ldiriladi.
- Oyna 9:16 crop'dan 47% keng, kattalashtirish ~1.4×.
- To'p kadr ichida: `crop` layout'da ~95%, `wide` layout'da ~99% (BRA–KOR, 19 klip).

**Super-resolution.**
- Real-ESRGAN general-x4v3 (BSD-3), `weights_only` yuklanadi.
- x4 natija GPU'da kichraytiriladi, bir kadr ~31 ms.
- Siqish bloklari yo'qoladi, kontur va raqamlar tiniqlashadi. Kamchiligi: o't sal silliqlashadi.

**Sharhni olib tashlash — hali yechilmagan.**
- Demucs stadion shovqinini ham "vocals"ga qo'shib yuboradi.
- SepFormer DNS4 sharhning ko'p qismini oladi, lekin baland qichqiriqlar qoladi.
- DeepFilterNet Windows/py3.12 da build bo'lmaydi. ClearerVoice eski numpy va opencv talab qiladi, shuning uchun alohida venv kerak bo'ladi.

## 3g. M5 — tayyor Shorts va baholash sayti (2026-10-28)

- **Qisqa versiya.** `fshorts vertical` standart holatda qisqa versiya yasaydi. Vaqtlar namunalar o'lchovidan olingan: `docs/research/Namuna Shorts tahlili.md`, 8-bo'lim.
  - Gol: −12/+4 s. Gol lahzasi = ovoz cho'qqisi − 1.5 s, chunki hisob paneli 0–6 s kechikadi.
  - Xavfli vaziyat va skill: −9/+2 s.
  - To'liq versiya `--profile full` bilan qoladi.
- **Bezak** (`wide` layout'ning tepa va past qismida):
  - hisob paneli, gol lahzasida hisob sariq rangda yangilanadi;
  - inglizcha hook birinchi 45% davomida;
  - lahza belgisi: GOAL!, WHAT A SAVE, SO CLOSE, JUST WIDE, BLOCKED, SKILLS;
  - "⚽ O'yinchi 29'" yozuvi.
- **Sarlavha.** Qwen3-8B sharhdan inglizcha hook va YouTube sarlavhasini yozadi, natija `captions.json` da. Render oldidan LLM xotiradan bo'shatiladi, chunki aks holda GPU xotirasi to'lib qoladi.
- **`fshorts run <match>`:** butun jarayon bitta buyruq bilan, keshlangan qadamlar qayta ishlatiladi.
- **`fshorts studio`:** brauzerda Shorts'larni ketma-ket ko'rib baholash.
  - 1–5 yulduz, sabab tugmalari va izoh.
  - Baholar `data/labels/human/shorts/` ga yoziladi, ranker uchun dataset bo'ladi.
  - Telefondan ochish uchun `--host 0.0.0.0`.
- **Ma'lum kamchilik:** 8B model ba'zan ismlarni chalkashtiradi ("Saved by Wang Yi-chan"). Keyingi qadam: jamoa tarkibi bilan tekshirish.

## 3h. M6 — matn va ko'rinish, baholar asosida (reja, 2026-10-29)

**Baholar xulosasi (48 Short, 3 match):**

| Ko'rsatkich | Natija |
|---|---|
| O'rtacha baho | gol **4.4**, xavfli vaziyat **2.8**, skill 3.0 |
| Eng ko'p belgi | `ends_early` 25, `good_cut` 24, `boring` 9, `ball_lost` 6, `wrong_text` 6, `starts_late` 6 |
| Izohlar | 6 ta golda "takroriy lavha kerak", 5 tasida "ozgina wide kerak" |
| Hisob paneli | yoqmadi |

**Noto'g'ri matnlarning sababi.** Ismlar faqat sharhdan olinadi, model esa ularni tekshirmaydi.
- Gol muallifi xato chiqqan: Nacho golida "Isco's shot!" yozilgan.
- "Ramos saved!" yozilgan, vaholanki Ramos himoyachi.
- Ism o'rniga "the goalkeeper" chiqqan.
- Ikki ism qo'shilib ketgan: "Bremer Cho".
- Griezmannning bu birinchi goli edi, lekin "strikes again" deb yozilgan.

Hooklar bir xil shablonda: "X's shot! ⚽", "X misses! 😱".

**Top-30 Shorts bilan farq (kadrlar yonma-yon solishtirildi):**
- **Matn joyi.** Ularda matn videoning o'zida, kadr balandligining ~55–70% qismida turadi. Bitta qisqa qalin oq qator, ostida yengil soya bor, quti yo'q.
- **Kadr.** Ularda hisob paneli, xira bandlar va GOAL belgisi yo'q. Bizda esa yuqorida hisob paneli bor, matn pastki xira bandda katta yozilgan.

### Qadamlar

**T1. Matn namunalari dataseti.**
- **Ma'lumot yig'ish.** 29 ta top Short'dan har 0.25 soniyada OCR olinadi. Har bir yozuv uchun quyidagilar saqlanadi:
  - so'zlari va emoji;
  - kadrdagi joyi (y%, x%);
  - shrift balandligi (kadrga nisbatan %);
  - qachon chiqib, qachon yo'qolishi (lahzaga nisbatan);
  - bir yoki ikki qatorligi.
- **Turlarga ajratish.** Har bir yozuv bir turga kiritiladi:
  - *label*: "Iconic.";
  - *teaser*: "Wait for…";
  - *setup → punchline*: "Try to take the ball off…" → "Impossible";
  - *ism tegi*;
  - *sanoq*.
- **Kengaytirish.** Ro'yxat 30 tadan ~80 tagacha kengaytiriladi: o'sha 12 kanaldan, faqat o'yin lahzalari olinadi. Aks holda turlar va so'zlar xilma-xilligi kam bo'ladi.
- **Natija.** `data/references/top/texts.json` fayli va tahlil hujjatining 10-bo'limi.

**T2. Faktlar varag'i: har bir lahza uchun tekshirilgan ma'lumot.**
- **Jamoa tarkibi.** Match uchun ikkala jamoaning tarkibi (ism, raqam, pozitsiya) olinadi. Manba Wikipedia, natija `data/matches/<id>.lineups.json` ga yoziladi.
- **Ismlarni tekshirish.** Sharhdagi ism tarkib bilan fuzzy solishtiriladi. Tarkibda topilmagan ism matnga yozilmaydi.
- **Rollarni tekshirish.** "Save" faqat darvozabonga, "scores" faqat gol muallifiga yoziladi. Gol muallifi hisob o'zgarishi va sharhdagi "scored by" bilan tasdiqlanadi.
- **Kontekst.** Qo'shimcha faktlar hisoblanadi:
  - o'yinchining shu matchdagi nechanchi goli ("again" faqat 2-golda);
  - tenglashtirdimi, oldinga chiqardimi;
  - kech gol (80+ daqiqa);
  - masofa (to'p modelidan, keyinchalik).

**T3. Yangi matn yozuvchi.**
- **Matn turi.** Lahza turi bo'yicha tanlanadi:
  - gol: label yoki teaser;
  - seyv: "X foot save 🤯" uslubi;
  - skill: setup → punchline.
- **Prompt.** Unga faqat faktlar varag'i va T1'dan shu turdagi 8–10 ta haqiqiy namuna beriladi.
- **Tekshiruv.** Model 4 ta variant yozadi va har biri qoidalardan o'tkaziladi:
  - ≤ 6 so'z, 1 emoji;
  - ism tarkibda bor;
  - natija oldindan aytilmaydi;
  - "again" va "last gasp" faqat fakt bo'lsa.

  Qoidadan o'tgan eng yaxshi variant tanlanadi.
- **Ikki bosqichli matn.** Ikkinchi qator lahza paytida chiqadi.

**T4. Yangi ko'rinish.**
- **Olib tashlanadi:** hisob paneli va katta lahza belgisi (GOAL!, WHAT A SAVE).
- **Matn uslubi.** Matn video ustiga, ~60% balandlikka tushadi. Shrift kichikroq va qalin, rangi oq, ostida yumshoq soya. Ko'rinish vaqti T1'dagi o'lchovlardan olinadi.
- **Hisob.** Kerak bo'lsa, hisob matnning ichida bo'ladi: "1-1 in the 88th 😮". Bu sozlamada yoqib-o'chiriladi.
- **Kanal belgisi.** Burchakka kichik logotip qo'yish ixtiyoriy, logotip bo'lsa qo'yiladi.

**T5. Videodagi tuzatishlar (baholardan).**
- **Gol takrori.** Gol klipidan keyin eng yaxshi burchakdagi bitta takror qo'shiladi, sekinlashtirilgan holda. Takror topish (`replay_events`) allaqachon bor.
- **Gol oxiri.** Gol tugaganidan keyin quvonishdan keyingi kadr almashguncha davom ettiriladi. Hozir esa qat'iy 8 soniya.
- **Kenglik.** Kadr ~15% kengroq olinadi, chunki "ozgina wide kerak" degan izoh 5 ta bo'lgan.
- **Xavfli vaziyatlar.** Kamroq va kuchliroqlari qoladi: faqat takrori bor zarba yoki seyvlar. Boshi 2–3 soniya oldinroq olinadi (`starts_late` belgisi).

**T6. Baholash.**
- **Matnni alohida baholash.** Studiyaga matn uchun alohida belgilar qo'shiladi: `wrong_name`, `boring_text`, `text_too_big`, `bad_timing`.
- **A/B solishtirish.** Bir xil Short ikki matn varianti bilan ko'rsatiladi, siz yoqqanini tanlaysiz. Bu matn modeli uchun dataset bo'ladi.
- **Qayta baholash.** Yangi versiyalar qayta render qilinadi va siz ularni yana baholaysiz.

**Tugadi degani:**
- `wrong_text` 0 ta.
- Gollar o'rtacha ≥ 4.5, xavfli vaziyatlar ≥ 3.5.
- A/B'da yangi matn eskisidan ko'p tanlanadi.

**Tartib:** T1 → T2 → T3 → T4. T5 parallel bajariladi, T6 eng oxirida.

### Holat (2026-10-29)

T1–T6 kodi tayyor, 48 Short v2 bo'lib qayta render qilindi. v1 va uning baholari arxivda turibdi:
- videolar `data/outputs/<id>/shorts_v1/`, ro'yxat `shorts_v1.json`;
- baholar `data/labels/human/shorts_v1/`.

**Matn.**
- **Faktlar.** Ismlar endi Wikipedia faktlaridan olinadi (`fshorts facts`).
- **Model.** Qwen3-8B 4 ta variant yozadi, ular `branding/rules.py` qoidalaridan o'tkaziladi. Qoidalar quyidagilarni rad etadi:
  - begona o'yinchi va noma'lum ism;
  - faktda yo'q da'vo;
  - butun qator KATTA harfda;
  - "lead" so'zining boshqa jamoaga berilishi;
  - aut, burchak va daqiqalar;
  - teaser bo'lgan ikkinchi qator;
  - bir matchda qaytarilgan qator.
- **Hammasi rad etilsa.** Model sabablar bilan yana bir marta so'raladi. Bu ham o'tmasa, story asosidagi zaxira qator qo'yiladi: "X hat-trick 🤯", "X levels it 🤯".

**Takror lavha.** Burchak endi sahna kesimlariga emas, wide/goalmouth kadrlarining uzluksiz qatoriga qarab tanlanadi. Takror bor Short'lar soni POR–ESP'da 3/14 dan 10/14 ga chiqdi.

**Studiya.** Matn uchun yangi belgilar qo'shildi: `good_text`, `wrong_name`, `boring_text`, `text_timing`, `text_size`, `good_replay`.

**A/B.** `fshorts compare` v1 va v2 baholarini bir xil klip bo'yicha solishtiradi.

**Qoldi.** Siz v2 ni baholaysiz, so'ng `fshorts compare` natijasi "Tugadi degani" mezonlari bilan solishtiriladi.

## 4. Xatarlar

- **Hisob paneli har telekanalda turlicha.** ROI preset'lar bilan hal qilinadi. Yangi telekanal = yangi preset.
- **Keng kadrlarda to'p juda kichik.** Detektor kadrni bo'laklarga bo'lib qidiradi (`InferenceSlicer`). To'p baribir topilmasa, xiralashtirilgan fonli zaxira formatga o'tamiz.
- **Windows va 5090 uchun wheel muammolari.** Faqat oldindan tekshirilgan paketlar tanlanadi. PaddleOCR va decord ishlatilmaydi.
- **Huquqiy xavf.** YouTube YPP va Content ID bo'yicha xavflar `docs/research/` hisobotida yozilgan. Ular texnik ishga ta'sir qilmaydi, lekin videolarni joylashdan oldin bilishingiz kerak.

## 5. Sizdan kerak bo'ladi

1. Shu rejaga roziligingiz yoki o'zgartirishlaringiz.
2. 3 ta test match fayli.
3. GitHub repo nomi (masalan `dawrandev/football-shorts`), yoki hozircha faqat lokal git.
