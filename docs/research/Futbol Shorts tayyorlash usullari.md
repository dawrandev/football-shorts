# Event ro'yxatidan boshlang, AI'ni keyin qo'shing

**Qisqa javob:** to'liq match'dan 9:16 football Shorts yasashning eng amaliy yo'li uch qatlamdan iborat. Birinchisi, moment'larni **event ma'lumotidan** oling (API'dagi gol daqiqasi yoki ekrandagi scoreboard o'zgarishi). Ikkinchisi, clip'larni **ro'yxat bo'yicha ommaviy kesing** (LosslessCut yoki FFmpeg). Uchinchisi, reframe va overlay'ni **bitta qayta ishlatiladigan shablonda** qiling. Creator'lar asosan CapCut + Alight Motion (telefonda) yoki Premiere/After Effects (kompyuterda) ishlatadi. Ular uchta vertical formatdan birini tanlaydi: action'ga ergashuvchi to'liq crop, xiralashtirilgan fon ustida 16:9 clip, yoki tepada va pastda title bar'li 16:9 clip. Oxirgi ikkitasi reframe talab qilmaydi, shuning uchun eng tez tayyorlanadi. Hech bir auto-reframe vositasi (CapCut, Premiere, Resolve, OpusClip) broadcast'dagi kichik to'pni ishonchli kuzatmaydi, shuning uchun keyframe'larni baribir qo'lda tuzatasiz. Bepul API'lar gol vaqtini faqat **daqiqa aniqligida** beradi, shuning uchun har clip'ga 30–60 sekund zaxira qo'shib, aniq nuqtani qo'lda yoki audio peak orqali topasiz. RTX 5090'dagi to'liq avtomat Python pipeline (scoreboard OCR + audio peak + Whisper + RF-DETR bilan ball tracking + FFmpeg/NVENC) bir match'ni taxminan **10–25 daqiqada** qayta ishlaydi. Uni yarim kunlik ishda bir dasturchi taxminan 2–4 haftada MVP darajasiga yetkazadi. Bu raqamlar benchmark emas, taxmin. Bitta eslatma: oldingi hisobotga ko'ra Uzbekistan hozircha YPP ro'yxatida yo'q, broadcast footage'dagi Shorts esa Content ID claim bo'lsa bloklanadi, shuning uchun bu usullarni o'z yoki ruxsat olingan footage'ingizga qo'llang.

## Creator'lar ikki xil: "edit" akkauntlari effekt quvadi, "highlight" akkauntlari tezlik

Football Shorts creator'larini ikki turga bo'lish mumkin. **"Edit" akkauntlari** o'yinchi haqida stilize qilingan video yasaydi: velocity (speed ramp, ya'ni tezlikni sekinlatib-tezlatish), camera shake, glow, colour grading va musiqaga sinxron kesimlar. **"Highlight/news" akkauntlari** esa gol clip'larini jamoa nomi va hisob bilan imkon qadar tez joylaydi. Bu bo'linish manbalardagi vosita tavsiflaridan chiqarilgan xulosa, so'rovnoma emas. Eng keng tarqalgan mobil stack shunday: rough cut, shablon va beat-sync uchun **CapCut**, keyin keyframe bilan shake, glow va grade uchun **Alight Motion**. Kompyuterda "professional standart" **Premiere Pro + After Effects** (time remapping, Lumetri, ReelSmart Motion Blur plugin'i). Bepul muqobillar **DaVinci Resolve** va **VN** ([FluxNote](https://fluxnote.io/guides/best-football-edit-apps-2026)). FluxNote o'z AI vositasini sotadigan vendor, shuning uchun bu ro'yxatni bozor ulushi statistikasi deb emas, umumiy manzara deb qabul qiling. Alight Motion'ning bepul versiyasi watermark qo'yadi, uni pullik a'zolik olib tashlaydi ([Apptopia](https://apptopia.com/ios/app/1459833443/about)). Creator'lar football colour-correction ("CC") preset'larini QR kod sifatida Reddit va Discord'da ulashadi, pullik paketlarini esa Gumroad'da sotadi ([Gumroad misoli](https://szxyoedits.gumroad.com/l/Footballcoldcc)).

**Auto reframe** (16:9 videoni avtomatik 9:16 ga kesib, harakatlanuvchi obyektga ergashish) hamma joyda bor, lekin hech qayerda football uchun maxsus qilinmagan. Premiere'da sequence'ni o'ng tugma bilan bosib "Auto Reframe Sequence" tanlanadi va Vertical 9:16 belgilanadi. Sport uchun **"Faster Motion"** preset'i tavsiya qilinadi. Natija tahrirlanadigan Position keyframe'lar ko'rinishida chiqadi, ya'ni yo'qolgan tracking'ni qo'lda tuzatish mumkin ([Adobe Help](https://helpx.adobe.com/dk/premiere/desktop/add-video-effects/commonly-used-effects/add-auto-reframe-effect-to-a-sequence.html); [Adobe user guide](https://learn.adobe.com/premiere-pro/using/auto-reframe.html)). CapCut'da Auto Reframe 2026-yil apreldan beri **faqat Pro'da** mavjud ([CapCut Help](https://www.capcut.com/help/why-do-i-have-to-pay-for-auto-reframe)). Rasmiy bo'lmagan forumdagi foydalanuvchi uning tez harakatda "bir joyda qotib qolishi"dan shikoyat qilgan ([capeditcut forum](https://www.capeditcut.com/community/capcut-pro/auto-reframe-not-working-desktop/)). DaVinci Resolve'ning Smart Reframe funksiyasi **faqat Studio versiyasida** bor, u bir martalik ~$295 turadi. Unda subject ustiga qo'lda **reference point** qo'yib, kuzatishni yo'naltirish mumkin ([Storyblocks](https://www.storyblocks.com/resources/tutorials/davinci-resolve-free-vs-studio); [elephorm](https://www.elephorm.com/formation/davinci-resolve-18-atelier-montage-neural-engine-et-ia/guide-sur-le-smart-reframe-dans-davinci-resolve)). Eng muhim maslahatni CapCut'ning o'zi beradi: butun timeline'ga bitta avtomatik crop qo'llamang, **har bir asosiy shot'ni alohida joylashtiring** ([CapCut tips](https://www.capcut.com/create/football-video-editing-tips-for-beginners)).

Uchta vertical format bor, va ular orasidagi tanlov aslida mehnat bilan ko'rinish o'rtasidagi kelishuv. **To'liq crop** ekranni to'ldiradi va "native" ko'rinadi, lekin har bir shot'ga keyframe qo'yish yoki pullik auto-reframe kerak. **Blurred background** formatida clip ikkinchi track'ga nusxalanadi, pastki nusxaga Blur qo'yiladi va o'tkir clip ustiga markazga joylashtiriladi ([CapCut blur guide](https://www.capcut.com/resource/how-to-blur-background-in-capcut)). Blur intensivligi taxminan 15–25 atrofida bo'lgani yaxshi, standart qiymat odatda juda kuchli ([Shotkit](https://shotkit.com/blur-capcut/)). **Title bar** formatida 16:9 clip tepadagi va pastdagi panel orasida turadi. Tepadagi panel sarlavha vazifasini o'taydi ("Team A 2-1 Team B"), pastdagisi caption yoki chaqiriq uchun. Oxirgi ikki format butun maydonni ko'rsatadi, bu gol'ning qanday qurilganini kuzatishga yordam beradi, va reframe ishini butunlay olib tashlaydi. Qaysi format ko'proq ishlatilishi yoki retention'da yaxshiroq ekani bo'yicha hech qanday o'lchov topilmadi. Bir freelance buyurtmada avval 16:9 master, keyin undan "9:16 vertical remix" so'ralgan, bu gorizontal kesib, keyin vertical'ga o'tkazish odatiy amaliyot ekanini ko'rsatadi ([Freelancer.de](https://www.freelancer.de/projects/video-production/dynamic-football-highlight-reel)). Tayyor 9:16 football ramkalari alpha kanal bilan Motion Array'da sotiladi ([Motion Array frames](https://motionarray.com/stock-motion-graphics/animated-football-frames-pack-4247033/)).

## Yaxshi Short 3–5 moment, birinchi sekundda hook va bitta effekt qoidasiga tayanadi

Tuzilma oddiy: **3–5 ta o'zi tushunarli moment**, eng kuchli kadr (gol, sejv yoki bayram) birinchi kadrda, oxirida aniq natija (hisob, reaksiya yoki keyingi o'yin). CapCut tavsiya qiladigan montaj tartibi hook → action → kontekst matni → ovoz → yakun → export ([CapCut tips](https://www.capcut.com/create/football-video-editing-tips-for-beginners)). Swipe lentasida tomoshabin taxminan 1 sekundda qaror qiladi ([Virvid](https://virvid.ai/blog/first-3-seconds-hook-faceless-shorts-2026)). vidIQ birinchi 2 sekundda hook'i bor Shorts **19% ko'proq tomoshabinni ushlab qolishini** keltiradi, lekin bu Zebracat ma'lumotiga tayangan marketing raqami ([vidIQ](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/)). Har gol oldidan bir necha sekund build-up va keyin bayramni qoldirish, slow-motion replay qo'shish odatiy amaliyot ([HeyEddie](https://www.heyeddie.ai/how-to/edit-sports-highlights)). Shorts 2024-yil 15-oktabrdan beri **3 daqiqagacha** bo'lishi mumkin ([Engadget](https://engadget.com/entertainment/youtube/youtube-shorts-can-now-run-up-to-three-minutes-160002081.html)), ammo football Shorts uchun "eng yaxshi uzunlik" bo'yicha ma'lumot topilmadi. Shuning uchun clip uzunligini o'zingiz sozlanadigan parametr qiling va A/B test qiling. Export spec: **1080×1920, MP4, H.264, AAC**. TikTok uchun 23–60 fps ([CapCut tips](https://www.capcut.com/create/football-video-editing-tips-for-beginners)).

Overlay'larda bitta qoida eng muhim: **har bir moment uchun bitta emphasis** (urg'u beruvchi effekt). Oxirgi zarbaga slow-motion, taktik bo'shliqni ko'rsatish uchun qisqa freeze frame yoki zoom bo'lishi mumkin, lekin slow-mo, zoom, freeze, matn va replay'ni bir joyga yig'mang. Kontekst matni (jamoalar, turnir, o'yinchi, hisob, vaqt) to'pdan, darvoza og'zidan va o'yinchilar oyog'idan uzoqda tursin. Ovozni oxirida qo'shing: stadion ovozi (hushtak, tomoshabin, zarba) yaxshi ishlaydi, musiqa esa litsenziyali bo'lishi shart ([CapCut tips](https://www.capcut.com/create/football-video-editing-tips-for-beginners)). "GOAL" animatsiyasini odatda noldan yasamaydilar. U CapCut matn shablonidan yoki After Effects kinetic-type shablonidan olinadi. Manbalar: CapCut'ning "Football edits" galereyalari ([CapCut](https://www.capcut.com/explore/Football-edits/7520687136966952968)), Motion Array'dagi 17 ta 4K football lower third ([Motion Array](https://motionarray.com/after-effects-templates/football-lower-thirds-2686780/)), scoreboard va lineup'li Envato Resolve paketi ([Envato](https://elements.envato.com/cyber-games-lower-thirds-davinci-resolve-X532TQ3)) va Videobolt'ning vertical "team versus" shabloni ([Videobolt](https://videobolt.net/author/kalinichev/football-team-versus-screen-vertical)). Club logotiplari uchun GitHub'dagi **FCLOGO** tashkiloti bepul SVG/PNG beradi, lekin uning litsenziyasi tekshirilmagan ([FCLOGO](https://github.com/FCLOGO)). Club gerblari trademark hisoblanadi, internetdagi "bepul" Videohive yuklamalari esa ko'pincha pirat nusxa, ulardan qoching.

Tezlikning siri shablonda. Qayta ishlatiladigan loyiha shabloni (tayyor title bar'lar, score bug, shriftlar, CC preset, export preset) va kunlik batch ishlash creator'larning asosiy tezlashtirish usuli. Bir talaba football akkaunti yoz davomida kuniga ~5 ta post joylagan va ularni "ijodiy portlashlar"da oldindan tayyorlab qo'ygan ([LHS Epic](https://lhsepic.com/53833/features/53833/)). Boshqa manba esa chastota emas, saqlash, ulashish va qayta ko'rish muhimroq ekanini, kuniga 1–5 post "yetarlidan ortiq" ekanini aytadi ([Planoly](https://www.planoly.com/blog/is-posting-consistently-enough-to-grow-on-instagram.md)). Video oxirini boshidagi kadr yoki ovoz bilan tugatish (loop) qayta ko'rishni rag'batlantiradi. Bu mantiqiy xulosa, football'ga xos manbada tasdiqlanmagan.

## Yarim-avtomat yo'l: API daqiqasi, sinxron formula va LosslessCut

Yarim-avtomat jarayonda kompyuter moment'larni topadi va kesadi, siz esa faqat tekshirasiz va shablonga tashlaysiz. Qadamlar to'rtta: (1) event ro'yxati → (2) clip'larni kesish → (3) bitta NLE'da (video muharrir) reframe va overlay shabloni → (4) render navbati.

**Event ma'lumoti manbai.** Eng arzon ishonchli variant **API-Football**: bepul plan kuniga ~100 so'rov, daqiqasiga 10 ta. Bitta match uchun 1–3 so'rov (fixture'ni topish va events) yetadi. Pullik tariflar $19/oydan boshlanadi ([API-Football guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide)). `fixtures/events` endpoint'i gol, kartochka, almashtirish va VAR event'larini daqiqasi bilan qaytaradi ([Educative](https://www.educative.io/courses/getting-soccer-data-with-api-football-in-javascript/events)). Bu endpoint bepul plan'da ochiqligi rasmiy sahifadan tasdiqlanmagan (sahifa 403 qaytardi), shuning uchun ro'yxatdan o'tib o'zingiz tekshiring. **football-data.org**'ning bepul tarifi bu ish uchun yaramaydi: unda gol urganlar va kartochkalar yo'q, ular €29/oylik "Free + Deep Data"dan boshlanadi ([football-data.org](https://www.football-data.org/pricing)). **StatsBomb open data** GitHub'da bepul, lekin faqat tanlangan tarixiy turnirlarni qamraydi va nashr qilinganda StatsBomb'ni ko'rsatish talab qilinadi ([statsbomb/open-data](https://github.com/statsbomb/open-data)). FotMob va SofaScore'ning rasmiy API'si yo'q. Norasmiy scraper'lar (masalan, `mobfot` Python client yoki Apify actor'lari) ishlaydi, ammo endpoint'lar ogohlantirishsiz o'zgarishi mumkin va foydalanish shartlarini tekshirish kerak ([mobfot](https://pypi.python.org/pypi/mobfot/); [Apify FotMob](https://apify.com/abotapi/fotmob-scraper.md)).

**Daqiqani video vaqtiga aylantirish.** API "57-daqiqa" deydi, video faylda esa bu nuqta boshqa joyda, chunki yozuv studiya ko'rsatuvi bilan boshlanadi va tanaffusni ham o'z ichiga oladi. Shuning uchun videoda har bir taym boshlanish hushtagini bir marta topib, ikki "offset" yozib qo'yasiz. Formula (manbalardagi ma'lumotlardan tuzilgan xulosa):

```text
video_time = kickoff_offset_half + (minute - half_start_minute) * 60
# half_start_minute: 1-taym uchun 0, 2-taym uchun 45
# 45+2 kabi qo'shimcha daqiqalar shu taymning 45:00 / 90:00 nuqtasidan hisoblanadi
# clip: hisoblangan vaqtdan ~45-60 s oldin boshlanib, keyingi daqiqa chegarasidan ~30 s keyin tugaydi
```

Laravel tili bilan aytsak, bu oddiy "timezone conversion": API ma'lumoti match vaqtida, sizga esa fayl vaqti kerak. Ekrandagi broadcast soatini bir marta o'qib, natijani tasdiqlab olish mumkin.

**Kesish.** **LosslessCut** (bepul, open-source) segment ro'yxatini CSV yoki matn faylidan import qiladi va faylning barcha segmentlarini bir urinishda, qayta encode qilmasdan (lossless) eksport qiladi. U segmentlarni DaVinci Resolve yoki Final Cut uchun XML qilib ham chiqaradi, ya'ni clip'lar to'g'ridan-to'g'ri timeline'ga tushadi. Cheklovlari: bir nechta faylni birdaniga batch eksport qilib bo'lmaydi, frame-aniq "smart cut" esa hali eksperimental ([mifi/lossless-cut](https://github.com/mifi/lossless-cut)). Import uchun aniq CSV ustun formati README'dan olinmagan, shuning uchun avval qo'lda bitta segment eksport qilib, formatini ko'rib oling. Lossless kesim keyframe'larga "yopishadi", shuning uchun zaxira joy qoldiring va frame-aniq trimni NLE'da qiling. FFmpeg ekvivalenti (umumiy bilim, bu sessiyada manba bilan tasdiqlanmagan):

```bash
# [tasdiqlanmagan] tez, lekin keyframe bo'yicha kesadi
ffmpeg -ss 3410 -to 3470 -i match.mp4 -c copy goal1.mp4
# [tasdiqlanmagan] frame-aniq, RTX 5090 NVENC bilan qayta encode
ffmpeg -ss 3410 -to 3470 -i match.mp4 -c:v h264_nvenc -cq 19 -c:a aac goal1.mp4
```

`-ss` ni `-i` dan oldin qo'yish faylni tez "sakrab" o'qishni bildiradi.

**Overlay'ni avtomatlashtirish.** Eng kuchli variant **After Effects**: u JSON va CSV import qiladi va expression'lar orqali matnni ma'lumotga bog'laydi ([Adobe help](https://helpx.adobe.com/cn/after-effects/desktop/animate-in-after-effects/data-driven-animation/data-driven-animations.html)). ExtendScript skripti har CSV qatori uchun shablon comp'ni nusxalaydi va `aerender` CLI uni interfeyssiz render qiladi. Bu uchinchi tomon qo'llanmasi, tekshirilmagan ([skills.sh](https://skills.sh/terminalskills/skills/after-effects)). Premiere'ning data-driven MOGRT'lari CSV'ni Essential Graphics'dagi "Spreadsheet" maydoniga tashlash orqali qabul qiladi, lekin ular jadval va diagrammalar uchun mo'ljallangan, ko'p clip'ga har xil hisob yozish uchun emas ([Adobe help](https://helpx.adobe.com/cz/premiere/desktop/add-text-images/use-motion-graphics-templates/use-data-driven-motion-graphics-templates.html)). Yolg'iz creator uchun eng sodda yechim bu: har match uchun bitta 1080×1920 shaffof scoreboard shabloni (logo va jamoa nomlari bilan) yasab, har clip'da faqat hisob va daqiqa matnini o'zgartirish. Buni CapCut shablon loyihasi, Premiere MOGRT yoki Resolve Fusion Text+ makrosi bilan qilish mumkin.

**Reframe vositasini tanlash.** OpusClip o'z sahifasida "sportdagi to'p kabi harakatlanuvchi obyektlarni kuzatadi" deydi, lekin mustaqil test topilmadi ([OpusClip](https://www.opus.pro/ai-reframe)). Bepul plan oyiga 60 daqiqa beradi, Klap Starter esa maksimal 45 daqiqalik video qabul qiladi ([Softwarefinder](https://softwarefinder.com/artificial-intelligence/opus-clip); [Dupple](https://dupple.com/reviews/klap-ai)). Ikkalasi ham butun match fayli uchun yaramaydi. Avval clip'larni kesib, keyin qisqa clip'larni yuklang. Moment'ni esa ularning "virality" algoritmi emas, event ma'lumoti tanlasin. 5090'li kompyuterda narx va sifat nisbati bo'yicha eng yaxshi variant **Resolve Studio** (bir martalik, Smart Reframe + qo'lda tuzatish) yoki subscription bilan Premiere Faster Motion. Keng taktik kadrlar uchun esa ko'pincha eng yaxshisi umuman tracking qilmaslik: markaziy crop'ga 1–2 ta qo'lda pan qo'shing yoki blurred-background formatini ishlating.

## To'liq avtomat pipeline: score-bug, ovoz, Whisper, to'p va FFmpeg

To'liq avtomat "broadcast → vertical Shorts" qiladigan tayyor open-source loyiha **mavjud emas**. Bor narsalar umumiy shorts generatorlari (LLM + Whisper + 9:16 crop, masalan [AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator)) va Roboflow'ning soccer prototiplari ([roboflow/sports](https://github.com/roboflow/sports)). Shuning uchun crop va caption kodini birinchilaridan, detection va tracking kodini roboflow/sports'dan olasiz, event'larni birlashtirish mantig'ini esa o'zingiz yozasiz. Pastdagi kod bloklarida **[tasdiqlangan]** belgisi kod rasmiy manbadan olinganini, **[tasdiqlanmagan]** esa umumiy bilim asosidagi eskiz ekanini va sinab ko'rilishi kerakligini bildiradi.

### Gol'ni score-bug o'zgarishi aniqlaydi, xavfli moment'ni ovoz

**Scoreboard OCR** (rasmdagi raqamni o'qish) eng ishonchli gol signali. YOLO bilan scoreboard'ni topib, OCR va qoidaga asoslangan algoritm qo'llagan maqola Bundesliga va Premier League'ni o'z ichiga olgan sport turlarida o'rtacha **F1 = 0.979** olgan ([ELCVIA, Guntuboina et al.](https://elcvia.cvc.uab.cat/article/download/v20-n1-guntuboina/589/4064)). F1 bu topilganlar aniqligi va to'liqligining birlashgan bahosi, 1.0 mukammal natija. Bu raqam qidiruv xulosasidan olingan, to'liq PDF ochilmadi. Bizning holatda score-bug ekranda doim bir joyda turadi, shuning uchun YOLO shart emas: ROI'ni (region of interest, ya'ni tasvirning kerakli to'rtburchagi) bir marta qo'lda belgilaysiz. Windows + RTX 5090'da PaddleOCR'ning sm_120 wheel'lari kechikishi mumkin, shuning uchun mavjud cu130 venv'ingizda ishlaydigan **EasyOCR** (PyTorch asosida) qulayroq.

```bash
# [tasdiqlanmagan] score-bug hududini sekundiga 1 kadr qilib oldindan chiqarish (OpenCV seek'dan tezroq)
ffmpeg -i match.mp4 -vf "fps=1,crop=220:40:60:40" roi/roi_%05d.png
```

```python
# [tasdiqlanmagan] hisob o'zgarishini "debounce" bilan aniqlash
import re, glob, easyocr
reader = easyocr.Reader(["en"], gpu=True)
hist, last, events = [], None, []
for t, path in enumerate(sorted(glob.glob("roi/*.png"))):
    text = " ".join(reader.readtext(path, detail=0))
    m = re.search(r"(\d)\s*[-:–]\s*(\d)", text)
    if not m:
        continue
    score = (int(m[1]), int(m[2])); hist.append(score)
    # ketma-ket 3 marta bir xil o'qilsa, yangi hisob deb qabul qilamiz
    if len(hist) >= 3 and hist[-1] == hist[-2] == hist[-3] and score != last:
        if last and sum(score) == sum(last) + 1:
            events.append(("goal", t))   # haqiqiy gol ~10-40 s oldinroq bo'lgan
        last = score
```

"Debounce" (Laravel'dagi rate limiting'ga o'xshash) OCR'ning bir martalik xatosi soxta gol yaratmasligi uchun kerak. Hisob kamaysa (VAR gol'ni bekor qilsa), event'ni o'chiring. Score-bug'da faqat ikki raqam bor, shuning uchun ~50 ta namunada o'qitilgan kichik raqam klassifikatori yoki template matching ko'pincha umumiy OCR'dan barqarorroq ishlaydi. Xuddi shu score-bug'dan match soatini (MM:SS) ham o'qisangiz, API daqiqalarini video vaqtiga aniq bog'laysiz va yarim-avtomat bo'limdagi qo'lda offset yozish ehtiyoji yo'qoladi.

**Gol bo'lmagan xavfli moment'lar** (zarba, sejv, ustunga tegish) uchun hisob o'zgarmaydi. Bu yerda ovoz yordam beradi: tomosha hayqirig'i va commentator ovozi balandlashadi. Oddiy baza yondashuvi audio'ni bo'laklarga bo'lib, har bo'lakning energiyasini hisoblash va yuqori chegaradan oshganlarini qoldirishdan iborat ([Analytics Vidhya](https://www.analyticsvidhya.com/blog/2019/09/guide-automatic-highlight-generation-python-without-machine-learning/)).

```python
# [tasdiqlanmagan] audio "hayajon" peak'lari; avval: ffmpeg -i match.mp4 -ac 1 -ar 16000 match.wav
import librosa, numpy as np, scipy.signal as ss
y, sr = librosa.load("match.wav", sr=16000, mono=True)
hop = sr // 2                                   # 0.5 s qadam
rms = librosa.feature.rms(y=y, frame_length=sr, hop_length=hop)[0]
flux = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
z = lambda v: (v - np.median(v)) / (np.percentile(v, 90) - np.median(v) + 1e-9)
score = ss.medfilt(0.7 * z(rms) + 0.3 * z(flux[:len(rms)]), 5)
peaks, _ = ss.find_peaks(score, height=np.percentile(score, 98), distance=int(60 / 0.5))
times = peaks * 0.5                             # nomzod sekundlar, kamida 60 s oraliq
```

Normallashtirishni har taym uchun alohida qiling, chunki tomosha shovqini o'zgarib turadi. Gol'lar 10–30 sekund davom etadigan baland ovoz beradi, shuning uchun peak'larni "balandlik × davomiylik" bo'yicha tartiblang.

**Whisper** (nutqni matnga aylantiruvchi model) commentator'ning "goal", "golazo", "what a save", "penalty", "гол" kabi so'zlarini vaqti bilan topadi. faster-whisper MIT litsenziyali, large-v3 o'zbek va rus tillarini qo'llaydi ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)):

```python
# [tasdiqlangan] so'z darajasidagi timestamp'lar
from faster_whisper import WhisperModel
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, _ = model.transcribe("audio.wav", word_timestamps=True,
                               vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))
for s in segments:
    for w in s.words:
        print(w.start, w.end, w.word)
```

Windows'da GPU uchun cuBLAS (CUDA 12) va cuDNN 9 DLL'lari kerak. README Purfview'ning whisper-standalone-win arxivini PATH'ga qo'shishni tavsiya qiladi, chunki NVIDIA kutubxonalarini pip orqali o'rnatish faqat Linux'da ishlaydi ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)).

**Birlashtirish qoidasi** (fusion) oddiy if-else. *Gol* = OCR'dagi hisob o'zgarishi + API'dagi gol daqiqasi + ±60 s ichida Whisper "goal" so'zi + audio peak. *Xavfli moment* = audio peak + kalit so'z, lekin hisob o'zgarmagan. Ixtiyoriy ravishda, **Gemini** 2–3 daqiqalik nomzod oynalarini ko'rib, event turini va caption'ni JSON qilib qaytarishi mumkin. Video File API orqali yuklanadi va javob sxemasi Pydantic modeli bilan beriladi ([Gemini video docs](https://ai.google.dev/gemini-api/docs/video-understanding); [structured output](https://ai.google.dev/gemini-api/docs/structured-output)). Butun match emas, faqat oynalar yuboriladi, bu ham vaqtni aniqroq qiladi, ham arzonroq. Gemini'ning gol aniqlash aniqligi bo'yicha benchmark topilmadi.

### Clip chegarasini kadr almashishiga yopishtiring

**PySceneDetect** (0.7.1, docs `scenedetect<0.8` ga pin qilishni maslahat beradi) kamera almashgan nuqtalarni topadi. Broadcast'dagi tez kesimlar uchun `AdaptiveDetector` ishlatiladi ([PySceneDetect docs](https://www.scenedetect.com/docs/latest/api.html)). Clip boshi va oxirini eng yaqin shot chegarasiga "yopishtirsangiz", clip kadr o'rtasidan uzilmaydi. Replay'ni topishning amaliy belgisi ham bor: gol'dan keyin broadcaster logo "wipe" ko'rsatadi, keyin 3–8 sekundlik 1–3 burchakdan replay beradi. Gol'dan keyingi 5–40 sekund ichidagi zich kesimlar to'plami replay demak. Replay'ni qo'shish uchun clip oxirini shu to'plamning oxirgi kesimigacha cho'zasiz. Ilmiy ishlar ham replay'ni logo-o'tish orqali aniqlaydi ([Simula](https://web-backend.simula.no/bibcite/export/bibtex/bibcite_reference/16398)).

```python
# [tasdiqlanmagan] faqat nomzod oynalarda ishlating
from scenedetect import detect, AdaptiveDetector
cuts = detect("window.mp4", AdaptiveDetector())
boundaries = [s.get_seconds() for s, _ in cuts]
snap = lambda t: min(boundaries, key=lambda b: abs(b - t))
```

Foydalanuvchi tanlagan uzunlik shu yerda kiradi. Masalan, event'dan 12 s oldin va 6 s keyin, replay to'plami bo'lsa uning oxirigacha. Bu qiymatlarni config parametri qiling.

### Crop markazi to'pga, to'p yo'qolsa o'yinchilarga ergashadi

Vertical crop uchun to'p va o'yinchilarni topish kerak. Roboflow tutorial'ida YOLOv8x 2×2 bo'laklarda (tile) o'qitilib **mAP@0.50 = 0.925** olgan, lekin muallifning o'zi u to'pni hali ham tez-tez o'tkazib yuborishini aytgan ([Roboflow ball tracking](https://roboflow.com/blog/tracking-ball-sports-computer-vision)). mAP bu detektor sifatining standart o'lchovi, 1.0 mukammal. Tutorial kodida xatolar bor: callback `patch` o'rniga `frame` uzatadi, `interpolated_radius` esa aniqlanmagan. YOLO AGPL litsenziyasini olib kiradi, shuning uchun o'sha Roboflow Universe datasetlarini ([ball](https://universe.roboflow.com/roboflow-jvuqo/football-ball-detection-rejhg), [players](https://universe.roboflow.com/roboflow-jvuqo/football-players-detection-3zvbc)) **RF-DETR** (Apache 2.0) bilan qayta o'qiting. Datasetlarning o'z litsenziyasini (ko'pincha CC BY 4.0) qo'lda tekshiring. Kichik to'pni topish uchun `supervision`'ning `InferenceSlicer`'i ishlatiladi. To'satdan sakrashlarni rad etish uchun oxirgi 10 ta to'p markazining o'rtachasiga eng yaqin detection olinadi (`BallTracker` g'oyasi). Silliqlash uchun **One-Euro filter** qo'llanadi. Uning `min_cutoff` parametri titrashni kamaytiradi, lekin kechikish qo'shadi. `beta` esa tez harakatdagi kechikishni kamaytiradi. Sozlash `beta=0`, `min_cutoff=1 Hz` dan boshlanadi, keyin beta ~0.001 dan 10 barobarlab oshiriladi ([1€ filter](https://gery.casiez.net/1euro/)).

```python
# [tasdiqlanmagan] to'pga ergashuvchi crop x koordinatalari
import supervision as sv, numpy as np
from rfdetr import RFDETRBase
from OneEuroFilter import OneEuroFilter

model = RFDETRBase(pretrain_weights="ball_players.pth")
slicer = sv.InferenceSlicer(callback=lambda patch: model.predict(patch, threshold=0.3),
                            slice_wh=(1060, 640), overlap_wh=(100, 100))
W, H, CW = 1920, 1080, 608                     # 1080p'dan 9:16 crop kengligi
f = OneEuroFilter(freq=25, mincutoff=0.3, beta=0.005)
xs, last_x, miss = [], W / 2, 0
for i, frame in enumerate(sv.get_video_frames_generator("clip.mp4")):
    det = slicer(frame)
    ball, players = det[det.class_id == BALL], det[det.class_id == PLAYER]
    if len(ball):
        target = ball.get_anchors_coordinates(sv.Position.CENTER)[0][0]; miss = 0
    elif len(players):
        target = np.median(players.get_anchors_coordinates(sv.Position.CENTER)[:, 0]); miss += 1
    else:
        target = last_x
    if abs(target - last_x) > 400 and miss == 0:          # sakrash chegarasi
        target = last_x + np.sign(target - last_x) * 400
    x = f(target, i / 25); last_x = x
    xs.append(int(np.clip(x - CW / 2, 0, W - CW)))
```

Uchta qo'shimcha qoida natijani "inson operator"ga yaqinlashtiradi. Birinchisi, **dead-zone**: to'p oynaning o'rtadagi 40% qismida tursa, crop'ni qimirlatmang. Ikkinchisi, kamera almashganda (PySceneDetect kesimi) filtrni qayta ishga tushiring, aks holda crop ekran bo'ylab "suzib" o'tadi. Uchinchisi, to'p N kadrdan ko'p yo'qolsa yoki o'yinchilar crop'dan kengroq tarqalsa, ularni quvmang, **blurred-background "fit" formatiga** o'ting. Bu ayniqsa gol paytidagi keng kadrlarda muhim. Slicing'ni faqat to'liq kadrli RF-DETR to'pni juda ko'p o'tkazib yuborsagina yoqing, chunki 2×2 bo'lak taxminan 4 barobar ko'proq hisob talab qiladi.

### FFmpeg kesadi, bezaydi va NVENC bilan encode qiladi

Dinamik crop'ni ikki yo'l bilan qilish mumkin. Birinchisi, har kadr uchun x qiymatlarini `sendcmd` fayliga yozish. FFmpeg crop filtri runtime buyruqlarini qabul qiladi, lekin **kenglik va balandlik o'zgarmas bo'lishi shart**, aks holda output to'xtaydi ([ffmpeg-user](https://ffmpeg.org/pipermail/ffmpeg-user/2023-June/056471.html); [trac #10984](https://ffmpeg.org/pipermail/ffmpeg-trac/2024-April/069133.html)). Ikkinchi yo'l Windows'da soddaroq: crop'ni Python'da numpy kesimi bilan qilib, xom kadrlarni FFmpeg'ga pipe qilish. Bu `sendcmd` ichidagi escaping muammolarini chetlab o'tadi.

```python
# [tasdiqlanmagan] Python'da crop, FFmpeg h264_nvenc bilan encode
import subprocess, cv2
p = subprocess.Popen(["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1080x1920", "-r", "25",
                      "-i", "-", "-i", "clip.mp4", "-map", "0:v", "-map", "1:a",
                      "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "12M",
                      "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", "out.mp4"], stdin=subprocess.PIPE)
for frame, x in zip(frames, xs):
    p.stdin.write(cv2.resize(frame[:, x:x + 608], (1080, 1920), interpolation=cv2.INTER_LANCZOS4).tobytes())
p.stdin.close(); p.wait()
```

```bash
# [tasdiqlanmagan] blurred-background 9:16 layout (keng gol kadrlari uchun)
-filter_complex "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:2[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"

# [tasdiqlanmagan] GOAL animatsiyasi (alpha'li .mov/.webm), logo va hisob matni
"[v][1:v]overlay=0:300:enable='between(t,3.2,5.2)'[v1];[v1][2:v]overlay=W-w-40:60[v2];[v2]drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='GOAL! 1-0':fontsize=96:fontcolor=white:borderw=6:bordercolor=black:x=(w-tw)/2:y=1500:enable='gte(t,3.2)',subtitles=caps.ass"
```

Windows'da filtr ichidagi yo'llarda disk harfidan keyingi ikki nuqtani escape qiling (`C\:/...`). `enable='between(t,3.2,5.2)'` "GOAL" animatsiyasini faqat gol lahzasida ko'rsatadi. Bu vaqtni OCR yoki audio peak'dan avtomatik hisoblaysiz. Hisob matni (`1-0`) OCR natijasidan, jamoa nomlari va logotiplar esa API javobidan olinadi. Whisper'dan chiqqan so'zlarni `.ass` subtitle fayliga aylantirib, caption'larni ham qo'shasiz. Upload spec'lari bo'yicha manbalar MP4/H.264/AAC va 1080×1920 da kelishadi, lekin bitrate tavsiyalari bir-biriga zid (4–6 Mbps dan 40–50 Mbps gacha) va hech biri YouTube'ning rasmiy sahifasi emas ([clipspeed](https://www.clipspeed.ai/blog/video-resolution-guide-shorts-reels-tiktok.html)). YouTube baribir qayta encode qiladi, shuning uchun 12–16 Mbps VBR, CQ ~19 xavfsiz boshlang'ich qiymat.

Shablon kodda emas, chiroyli animatsiyada bo'lishini xohlasangiz, **Remotion** (React/TSX bilan video) score kartalari va o'yinchi ismlari uchun eng kuchli variant. U individual foydalanuvchilar va 3 tagacha xodimli kompaniyalar uchun bepul, undan kattalarga Company License kerak ([Remotion LICENSE](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)). Siz Laravel + Inertia/Vue tajribasiga egasiz, shuning uchun komponent asosidagi shablon sizga tanish tuyuladi. MoviePy v2 prototip uchun qulay, lekin 1080×1920 da sof FFmpeg'dan ancha sekin, va v1 API'si buzilgan (`set_*` o'rniga `with_*`).

## Tavsiya etilgan yo'l: oddiydan to'liq avtomatgacha besh bosqich

Eng katta xato birdaniga to'liq avtomat tizim qurishga urinish bo'ladi. Har bosqich o'zi ishlaydigan natija beradi va keyingisining "ground truth"ini (tekshirish uchun to'g'ri javoblarni) tayyorlaydi. 1–2-bosqichda qo'lda topgan gol vaqtlaringiz 4-bosqichdagi OCR detektorining test ma'lumoti bo'ladi.

| Bosqich | Nima qilasiz | Vositalar | Natija / tekshiruv |
|---|---|---|---|
| **0. Qo'lda (1–2 kun)** | Bitta match'dan 3–5 ta Short'ni to'liq qo'lda yasang: title bar yoki blurred-background format, bitta emphasis, stadion ovozi | CapCut desktop yoki DaVinci Resolve (bepul) | Shablon loyihasi: title bar'lar, score bug, shrift, export preset (1080×1920) |
| **1. Yarim-avtomat (2–3 kun)** | API-Football'dan event'larni olish, ikki kickoff offset'ni yozish, formula bilan CSV, LosslessCut'da ommaviy kesish | API-Football free, kichik Python skript, LosslessCut | Match boshiga clip'lar ~10 daqiqada tayyor, siz faqat shablonga tashlaysiz |
| **2. Audio va Whisper nomzodlari (M1, 2–3 kun)** | `ffmpeg` audio extract, RMS peak, faster-whisper kalit so'zlari, nomzodlar CSV'si | ffmpeg, librosa, faster-whisper | Bitta ma'lum match bilan qo'lda solishtirish |
| **3. Gol tasdiqlash (M2, 2–3 kun)** | `cv2.selectROI` bilan score-bug ROI, 1 fps OCR, debounce, match soatini OCR qilish, API bilan solishtirish | EasyOCR, OpenCV | 3 ta test match'da gol'larning **100%** topilishi |
| **4. Avtomat kesish (M3, 1–2 kun)** | Foydalanuvchi tanlagan oldin/keyin oyna (masalan −12/+6 s), replay to'plamigacha cho'zish, shot chegarasiga yopishtirish | PySceneDetect, FFmpeg | 16:9 clip'lar, uzilishsiz |
| **5. 9:16 reframe (M4, 3–5 kun)** | RF-DETR'ni Universe ball/player datasetida fine-tune qilish, BallTracker, One-Euro, dead-zone, kesimda reset, blurred-fit fallback | rfdetr, supervision, OneEuroFilter | Silliq, to'pni ushlab turuvchi vertical clip |
| **6. Brending (M5, 2–3 kun)** | GOAL animatsiyasi, logo, hisob `drawtext`, Whisper'dan ASS caption'lar, NVENC encode | FFmpeg (keyinchalik Remotion) | Joylashga tayyor Short'lar |
| **7. Ixtiyoriy (M6)** | Gemini Flash-Lite nomzodlarni tartiblaydi va sarlavha yozadi, folder watcher, nashrdan oldin ko'rib chiqish UI'si | Gemini API, Laravel admin | "Match yukla → Shorts ol" oqimi |

M1–M5 to'plami yarim kunlik ishda taxminan **2–4 hafta** oladi. Bitta match uchun taxminiy vaqt quyidagicha: Whisper ~2–6 daqiqa, OCR ~2–5 daqiqa, ~10 ta clip ustida tracking ~3–8 daqiqa, render ~1–2 daqiqa. Jami **~10–25 daqiqa**, lekin RTX 5090'da bu stack uchun hech qanday o'lchangan benchmark topilmadi. Taqqoslash uchun, Roboflow'ning 60 sekundlik prototipi M-series Mac'da ~15 daqiqa ishlagan ([Roboflow](https://roboflow.com/blog/make-automatic-highlight-reels-from-soccer-games)). Asosiy xatarlar uchta. Birinchisi, score-bug ko'rinishi har broadcaster'da boshqacha, shuning uchun ROI preset'lari kerak bo'ladi. Ikkinchisi, keng kadrlarda to'p yo'qoladi, bu blurred-fit fallback bilan yechiladi. Uchinchisi, Windows'da wheel muammolari bor (paddle, decord, ctranslate2 CUDA DLL'lari). EasyOCR va PyAV/OpenCV'ni tanlab, ularning ko'pidan qochasiz.

## Xulosa

Tadqiqotning kutilmagan xulosasi shu: "AI" bu ishda eng kam kerakli qism. Moment'ni API daqiqasi va score-bug'dagi raqam topadi, kesishni LosslessCut yoki FFmpeg qiladi, vertical format muammosini esa ko'p hollarda blurred-background layout tracking'siz hal qiladi. Ball tracking faqat to'liq crop formatini tanlasangiz kerak bo'ladi, va u ham har doim "to'p yo'qolsa fit formatiga o't" degan zaxira bilan ishlaydi. Shuning uchun haqiqiy qiymat modelda emas, **event fusion mantig'i va qayta ishlatiladigan shablonda** yaratiladi, va bu aynan dasturchi sifatida sizning kuchli tomoningiz.

Bu yondashuvdan bitta amaliy oqibat chiqadi. Pipeline'ni modul-modul qursangiz (event manbai → kesish → layout → overlay), har modulni almashtirish mumkin bo'ladi. API o'rniga OCR, OCR o'rniga keyinchalik action-spotting modeli, FFmpeg overlay o'rniga Remotion qo'yasiz va qolgan qismlar o'zgarmaydi. Laravel'dagi service/interface ajratish qanday ishlasa, bu ham xuddi shunday ishlaydi. Hali ham ochiq savollar bor: football Shorts uchun optimal uzunlik, qaysi vertical format retention'ni yaxshiroq ushlashi va auto-reframe vositalarining to'pni qanchalik aniq kuzatishi bo'yicha hech qanday o'lchov yo'q. Ularni o'z kanalingizda A/B test bilan aniqlaysiz.
