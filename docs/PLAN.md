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

## 4. Xatarlar

- **Hisob paneli har telekanalda turlicha.** ROI preset'lar bilan hal qilinadi. Yangi telekanal = yangi preset.
- **Keng kadrlarda to'p juda kichik.** Detektor kadrni bo'laklarga bo'lib qidiradi (`InferenceSlicer`). To'p baribir topilmasa, xiralashtirilgan fonli zaxira formatga o'tamiz.
- **Windows va 5090 uchun wheel muammolari.** Faqat oldindan tekshirilgan paketlar tanlanadi. PaddleOCR va decord ishlatilmaydi.
- **Huquqiy xavf.** YouTube YPP va Content ID bo'yicha xavflar `docs/research/` hisobotida yozilgan. Ular texnik ishga ta'sir qilmaydi, lekin videolarni joylashdan oldin bilishingiz kerak.

## 5. Sizdan kerak bo'ladi

1. Shu rejaga roziligingiz yoki o'zgartirishlaringiz.
2. 3 ta test match fayli.
3. GitHub repo nomi (masalan `dawrandev/football-shorts`), yoki hozircha faqat lokal git.
