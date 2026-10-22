# Muzlatilgan encoder'lar, o'z label'laringiz va lokal VLM yutadi

**Qisqa javob:** sizning holatingizda (bitta RTX 5090, native Windows, hozircha bir necha match, keyin o'sib boradigan dataset, tijoriy foydalanish) eng to'g'ri strategiya **katta modelni o'qitish emas**. Tayyor, tijoriy litsenziyali encoder'larni "muzlatib" ishlatasiz va ularning ustida **kichik "head"** o'qitasiz. Video uchun V-JEPA 2 (MIT), kadrlar uchun SigLIP2 yoki DINOv2 (Apache-2.0), audio uchun BEATs yoki PANNs, matn uchun Whisper. Birinchi ranker sifatida esa ular ustida **LightGBM** (MIT) ishlatasiz: pipeline'ning hozirgi signallari (hisob o'zgarishi, kalit so'zlar, ovoz balandligi) bilan birga. Label'larning asosiy manbai sizning accept/reject UI'ingiz va score OCR'dan chiqadigan bepul "weak label"lar bo'ladi. Reframe uchun ikki model kerak. O'yinchilarni **RF-DETR Medium/Large** (Apache-2.0) topadi. To'pni esa **3 kadrli heatmap modeli** (WASB-SBDT, MIT) topadi: soccer'da u F1 88.3 olgan, box detektor DeepBall esa 44.5. Ikkalasini ham **o'zingiz belgilagan kadrlarda** o'qitasiz, belgilashni SAM2 va Grounding DINO (Apache-2.0) tezlashtiradi. VLM (video tushunadigan til modeli) asosiy detektor bo'lmaydi: zero-shot ular soccer event'larida zaif. Ularning roli **re-ranker, caption yozuvchi va label tayyorlovchi**. Gemini bir match'ni taxminan $0.07–0.41 ga ko'radi, ammo uning "competing models" bandi uning javoblaridan o'z modelingizni o'qitishni huquqiy kulrang zonaga qo'yadi. Shuning uchun **training label'larini lokal Qwen3-VL (Apache-2.0) yaratsin**, Gemini esa faqat runtime'da tartiblash va sarlavha uchun ishlatilsin. Litsenziya tuzoqlari jiddiy: VideoMAE V2 weights non-commercial, DEIMv2 2026-08-24 da non-commercial'ga o'tgan, RF-DETR XL/2XL Roboflow plan'iga bog'langan, Ultralytics AGPL, SoccerNet esa NDA ortida. Bu hisobot oxirida aniq stack va `docs/PLAN.md` ga moslangan yangilangan M1–M6 rejasi bor.

## Beshta atama: encoder, head, fine-tuning, heatmap, distillation

Strategiyani tushunish uchun beshta so'zni bilish yetadi. **Encoder** bu katta, oldindan millionlab video yoki rasmda o'qitilgan model. U kadrni yoki klipni raqamlar vektoriga (embedding, masalan 1024 ta son) aylantiradi. Bu vektor "bu yerda nima bo'lyapti" degan ma'noni siqib saqlaydi. **Head** bu embedding'ni olib, yakuniy javobni ("gol ehtimoli 0.83") beradigan kichik model, odatda bir necha million parametr yoki undan ham kam. **Frozen (muzlatilgan) encoder** degani encoder'ning o'zi o'zgarmaydi, faqat head o'qitiladi. Embedding'larni bir marta hisoblab diskka saqlaysiz, keyin head'ni daqiqalarda qayta-qayta o'qitasiz. Web dasturlashdagi analogiya: og'ir so'rov natijasini cache'ga yozib, ustida tez hisob-kitob qilish. **Fine-tuning** esa encoder'ning o'zini ham sizning ma'lumotingizda qo'shimcha o'qitish. U kuchliroq, lekin ko'p label, ko'p vaqt va ko'p GPU xotira talab qiladi. **Heatmap** modeli obyekt atrofiga to'rtburchak (box) chizmaydi. Uning o'rniga rasm o'lchamidagi "issiqlik xaritasi" chiqaradi, va eng yorqin nuqta to'pning markazi bo'ladi. Bu 5–15 pikselli to'p uchun box'dan ancha mos keladi. **Distillation** (yoki pseudo-labeling) katta "o'qituvchi" model (masalan VLM) ma'lumotga label qo'yib, shu label'lar bilan kichik "o'quvchi" model o'qitilishi. O'quvchi tezroq va arzonroq ishlaydi, lekin o'qituvchining xatolarini ham meros qilib oladi.

Bu beshtasi bitta g'oyaga birlashadi: kam ma'lumot bilan **encoder'larni muzlatib, faqat head o'qitish** kerak. Fine-tuning va distillation esa keyinroq, dataset kattalashganda ishga tushiriladi.

## Highlight modeli: 3–20 match'da muzlatilgan encoder va kichik head yutadi

### Nega end-to-end emas

SoccerNet'dagi eng yaxshi natijalar ikki xil yo'l bilan olingan, va bu farq sizning tanlovingizni hal qiladi. 2024 Ball Action Spotting g'olibi **T-DEED** (mAP@1 73.39) va ikkinchi o'rindagi UniBw end-to-end ishlaydi: kichik 2D backbone yuqori aniqlikdagi kadrlardan pas va zarbalarni ±1 soniya aniqlikda topadi ([SoccerNet 2024 report](https://arxiv.org/html/2409.10587v1)). **ASTRA** esa 3-o'rinni (2023) **oldindan hisoblangan visual va audio embedding'lar** ustidagi transformer bilan olgan, Average-mAP 66.82 natija bilan ([ASTRA](https://arxiv.org/html/2404.01891v1)). Sizning vazifangiz "shu 15–20 soniyalik oyna Short'ga arziydimi" degan savol. Bunga kadr-aniq vaqt kerak emas. Bunday klip darajasidagi savolda muzlatilgan embedding'lar va kichik head label'ni ancha tejaydi, har tajriba esa kunlar emas, daqiqalar oladi. Bundan tashqari, SoccerNet natijalari 300–500 belgilangan o'yin ustida olingan. Hatto 2024 challenge'ida atigi **7 ta belgilangan o'yin** berilganda ham raqobatbardosh jamoalar katta SoccerNet to'plamidan transfer qilgan ([SoccerNet 2024 report](https://arxiv.org/pdf/2409.10587)). Sizda bunday transfer manbai yo'q, chunki SoccerNet'ni tijoriy maqsadda ishlatib bo'lmaydi (pastda batafsil).

### Qaysi encoder'lar tijoriy jihatdan toza

| Modallik | Tavsiya | Litsenziya | Holat | Izoh |
|---|---|---|---|---|
| Video (harakat) | **V-JEPA 2 ViT-L** (`facebook/vjepa2-vitl-fpc64-256`, 0.3B, 64 kadr, 256px) | MIT | Tasdiqlangan ([HF](https://huggingface.co/facebook/vjepa2-vitl-fpc64-256)) | ViT-H/g variantlari ham MIT bo'lishi kutiladi, **tasdiqlanmagan** |
| Kadr (semantika) | SigLIP2 yoki DINOv2, 1–2 fps | Apache-2.0 | **Tasdiqlanmagan** bu sessiyada | replay, close-up, tomosha, grafika kabi sahnalarni ajratadi |
| Kadr (muqobil) | DINOv3 | maxsus "dinov3-license", tijoriy mumkin | Tasdiqlangan ([DINOv3 License](https://ai.meta.com/resources/models-and-libraries/dinov3-license/)) | mahsulotda **"Built with DINOv3"** yozuvi ko'rinib turishi shart |
| Video (muqobil) | InternVideo2 Stage2 1B | apache-2.0, gated | Tasdiqlangan ([HF](https://huggingface.co/OpenGVLab/InternVideo2-Stage2_1B-224p-f4)) | flash-attn kabi bog'liqliklar Windows'da muammo tug'diradi |
| Audio | BEATs (~90M) yoki PANNs CNN14 | MIT (taxminan) | **Tasdiqlanmagan** ([BEATs repo](https://github.com/microsoft/unilm/tree/master/beats)) | BEATs weights HF'da emas, OneDrive'da |
| Matn | faster-whisper transkripti + matn embedding | MIT | yuqori ishonch, qayta tekshirilmagan | sharhlovchi kechikishini hisobga oling |
| **Ishlatmang** | **VideoMAE V2** weights | **CC BY-NC 4.0** | Tasdiqlangan ([HF](https://huggingface.co/OpenGVLab/VideoMAEv2-giant)) | kod MIT, lekin weights non-commercial |

VideoMAE V2 eng tipik tuzoq. Uning kodi MIT ([GitHub](https://github.com/OpenGVLab/VideoMAEv2)), shuning uchun "bepul" deb o'ylash oson. Lekin `VideoMAEv2-giant` weights CC BY-NC 4.0 ostida. Distill qilingan ViT-S/B variantlari ham ehtimol shunday, bu tekshirilmagan. Barcha audio modellar asosan AudioSet'da (YouTube kliplari) o'qitilgan. Weights litsenziyasi ruxsat beradi, lekin training data'ning kelib chiqishi deyarli barcha audio modellarga xos kulrang zona bo'lib qoladi.

Tezlik bo'yicha o'lchangan raqam yo'q, faqat taxmin bor. 90 daqiqalik match'ni 2 fps'da SigLIP2-B yoki DINOv2-B bilan ishlash (~10.8k kadr) FP16'da ~1–2 daqiqa oladi va bu yerda video decode tor joy bo'ladi. V-JEPA 2 ViT-L 1–2 soniya qadam bilan ~5–15 daqiqa/match, audio encoder'lar 1 daqiqadan kam. Amaliy yechim: V-JEPA 2 ni butun match'ga emas, **faqat nomzod oynalarga** (60 ta nomzod × ±30 s ≈ 1 soatdan kam video) ishlating. Shunda PLAN'dagi "bir match 25 daqiqadan kam" chegarasi buzilmaydi.

### Head: avval LightGBM, keyin temporal model

Head'ni uch bosqichda murakkablashtiring. **Birinchi bosqich:** har nomzod oyna uchun embedding'larning o'rtachasi (pooled embedding) va pipeline'ning skalyar signallari bitta jadvalga yoziladi: `score_changed`, `keyword_hits`, `loudness_z`, `replay_detected`, shot soni. Bu jadval ustida **LightGBM** (gradient boosting, MIT) o'qitiladi. Kam ma'lumotda skalyar signallar ustun bo'ladi, LightGBM esa yuzlab namunada ham ishlaydi va qaysi belgi muhimligini ko'rsatadi. **Ikkinchi bosqich**, taxminan 20+ match to'planganda: 1–2 fps'dagi embedding ketma-ketligi ustida **1D temporal-conv yoki BiGRU head**. U har vaqt qadamiga focal/BCE loss beradi, NMS (bir-biriga yaqin takror javoblarni olib tashlash) bilan ishlaydi va butun match bo'ylab "highlight spotting" qiladi. **Uchinchi bosqich** faqat kerak bo'lsa: ASTRA'ga o'xshash transformer head ([ASTRA](https://arxiv.org/html/2404.01891v1)). Kadr-aniq vaqt kerak bo'lsa, **E2E-Spot** (BSD-3-Clause) kod bazasini oling ([jhong93/spot](https://github.com/jhong93/spot)), T-DEED'ni emas. **T-DEED GPL-3.0** ([arturxe2/T-DEED](https://github.com/arturxe2/T-DEED)). GPL faqat kodni tarqatganda ishga tushadi, sof server tomonidagi SaaS'da odatda tushmaydi. Lekin keyinchalik desktop yoki on-prem versiya chiqarsangiz, bu xavfga aylanadi. ASTRA'ning o'z litsenziyasi tekshirilmagan.

### Audio, video, sharh va OCR'ni qanday birlashtirish

Adabiyot bu savolga aniq javob bermaydi. ASTRA audio'ni "ko'rinmaydigan action'larni topish uchun" qo'shgan ([ASTRA](https://arxiv.org/html/2404.01891v1)), lekin 2024 Ball Action Spotting'ning top yechimlari audio ishlatmagan ([SoccerNet 2024 report](https://arxiv.org/html/2409.10587v1)). ASR/sharh matni bo'yicha yangi ishlar (SoccerNet-Echoes, MatchVoice, TimeSoccer) asosan caption va sharh yaratishga qaratilgan, highlight tartiblashga emas ([SoccerNet-Echoes](https://arxiv.org/abs/2405.07354)). Audio vs video vs ASR ablation'ini soccer highlight ranking uchun ko'rsatgan 2025–2026 maqola topilmadi. Shuning uchun amaliy yo'l **late fusion**: har modallik o'z embedding'ini beradi, ular head kirishida birlashtiriladi (concat). Bitta muhim nozik joy bor: **sharhlovchi kechikadi**. SoccerNet-Caption'da sharh va video o'rtasida sezilarli vaqt siljishi qayd etilgan ([arXiv 2504.17365](https://arxiv.org/abs/2504.17365)). Shuning uchun matn oynasini videoga nisbatan bir necha soniya keyinga suring yoki kengaytiring. Qiziq bir natija ham bor: faqat vaqt belgili sharh matnini o'qigan LLM'lar gol, kartochka va almashtirishlarni SOTA video spotter'larga "yaqin" topgan, video hisoblashsiz ([arXiv 2506.17144](https://arxiv.org/html/2506.17144v2)). Demak, sharhli broadcast'larda Whisper matni arzon va kuchli kanal.

### Weak label va active learning: dataset o'zi yig'iladi

**Weak label** (kuchsiz, avtomatik label) sizda deyarli tekin. Score OCR o'zgarishi va match-event API'lari gol uchun yuqori aniqlikdagi pozitiv namuna beradi. Faqat ularning vaqti siljigan: grafika goldan ~5–30 s keyin yangilanadi, undan keyin replay keladi. Shuning uchun ularni kadr label'i emas, **oyna darajasidagi label** sifatida ishlating, siljishni esa o'rganiladigan yoki baholangan offset deb oling. Bu xulosa, manbada sinalmagan.

**Active learning** (model eng ko'p foyda keladigan namunalarni odamga ko'rsatishi) PLAN'dagi accept/reject UI'ning o'zi. UI'da faqat eng ishonchli nomzodlarni emas, model **ikkilanayotgan** (p≈0.5) va bir-biridan farqli nomzodlarni ham ko'rsating. Har bir reject'ni "hard negative" sifatida saqlang. Eng qimmatli negativlar ovozi baland, lekin event bo'lmagan oynalar: tomosha hayqirig'i, ammo zarba yo'q. Bu ham xulosa: soccer highlight'larga active learning qo'llagan manba topilmadi.

Qancha ma'lumot kerakligi bo'yicha ishonchli egri chiziq **yo'q**. Taxmin (manbasiz): gol yoki katta imkoniyat uchun muzlatilgan feature'lar ustida ishlatsa bo'ladigan oyna klassifikatori ~200–500 belgilangan oyna talab qiladi, ya'ni reject'lar bilan ~10–20 match. "Yaxshi hujum" esa sub'ektiv sinf. Unga ancha ko'p ma'lumot va "A klip B'dan yaxshiroq" kabi juftlik (pairwise) label'lari kerak. Natijani har doim **leave-one-match-out** bilan tekshiring, ya'ni bitta match'ni testga ajratib, qolganlarida o'qiting. Aks holda bir match ichidagi o'xshash kadrlar natijani sun'iy oshiradi.

### SoccerNet: nega uni pretraining uchun ishlatmaysiz

SoccerNet videolari HF'da **NDA qabul qilib, qo'lda tasdiqlangandan keyin** ochiladi ([soccer-net.org/data](https://www.soccer-net.org/data); [SN-BAS-2025](https://huggingface.co/datasets/SoccerNet/SN-BAS-2025)). SoccerNet'dan olingan SoccerChat dataseti faqat ilmiy/ta'lim maqsadida, non-commercial va hosila videoni tarqatmaslik sharti bilan beriladi ([SoccerChat README](https://huggingface.co/datasets/SimulaMet/SoccerChat/blob/refs%2Fpr%2F2/README.md)). NDA matnining o'zi (Google Drive hujjati) o'qilmadi, shuning uchun uning trained model'larni tijoriy ishlatishni aniq taqiqlashi **tasdiqlanmagan**. Lekin xulosa amaliy jihatdan aniq: SoccerNet videolari yoki ulardan olingan feature'lar ustida production weights o'qitmang. **T-DEED va E2E-Spot'ning ochiq checkpoint'lari ham shu muammoni meros qiladi.** Kerak bo'lsa SoccerNet jamoasidan yozma tijoriy ruxsat so'rang.

## To'p va o'yinchi: ikki modelli tizim va o'zingizning label'laringiz

### O'yinchilar uchun RF-DETR, lekin faqat Apache o'lchamlari

RF-DETR'ning hamma o'lchami bir xil litsenziyada emas, va bu eng oson yo'l qo'yiladigan xato. **Nano, Small, Medium va Large Apache-2.0**: Medium 576px'da 54.7 AP va T4'da 4.4 ms, Large 704px'da 56.5 AP va 33.9M parametr. **Atto, Femto, Pico hamda XLarge va 2XLarge esa PML 1.0** ostida ([RF-DETR GitHub](https://github.com/roboflow/rf-detr)). Roboflow forumidagi javobga ko'ra, PML modellar "Roboflow Platform plan shartlari bo'yicha" ishlatiladi, Roboflow akkaunti talab qilinadi va credit sarflanadi ([Roboflow forum](https://discuss.roboflow.com/t/plan-required-for-new-rfdetrlarge-sizes/11827)). Bu litsenziya matni emas, ikkilamchi tavsif. Repo faol yangilanib turadi va `pip install rfdetr` bilan o'rnatiladi. Lekin README'da Windows yoki sm_120 bo'yicha hech narsa yo'q, buni o'zingiz sinashingiz kerak.

Zaxira variantlar **D-FINE** va **RT-DETR/RT-DETRv2** (ikkalasi Apache-2.0, faol) ([D-FINE](https://github.com/Peterande/D-FINE); [RT-DETR](https://github.com/lyuwenyu/RT-DETR)). Ularning `torchrun`'ga asoslangan training skriptlari Windows'da `--nproc_per_node=1` va gloo backend talab qilishi mumkin (**tasdiqlanmagan**). Shuning uchun pip paketli RF-DETR Windows'da qulayroq.

**DEIMv2 endi tijoriy ishlatib bo'lmaydi.** Uning LICENSE.md fayli 2026-08-24 da almashtirilgan: endi "solely for Non-Commercial Purposes" deydi va weights'ni ham faqat non-commercial maqsadda fine-tune qilishga ruxsat beradi ([DEIMv2 LICENSE](https://github.com/Intellindust-AI-Lab/DEIMv2/blob/main/LICENSE.md); [commit tarixi](https://api.github.com/repos/Intellindust-AI-Lab/DEIMv2/commits?path=LICENSE.md)). Gitee mirror'larida hali ham Apache-2.0 turibdi, lekin ular eskirgan ([Gitee](https://gitee.com/gengumeng/DEIMv2)). DEIM v1 esa Apache-2.0 bo'lib qolgan ([DEIM](https://github.com/Intellindust-AI-Lab/DEIM/blob/main/LICENSE)). Ultralytics, YOLOv10, YOLOv12 va YOLOv13 AGPL-3.0, multi-tracker o'rami **boxmot ham AGPL** ([ultralytics](https://github.com/ultralytics/ultralytics); [boxmot](https://github.com/mikel-brostrom/boxmot)).

### To'p uchun heatmap modeli box detektordan ikki barobar yaxshi

Broadcast'da to'p uzoq kadrlarda ~8–20 px bo'ladi va tana qismlari bilan oson adashtiriladi ([FootAndBall](https://ar5iv.arxiv.org/html/1912.05445)). U kadr maydonining taxminan 2×10⁻⁵ qismini egallaydi ([arXiv 2302.00123](https://arxiv.org/pdf/2302.00123)). Roboflow'ning o'z soccer pipeline'i ham to'p uchun alohida model, 640×640 tiling va buferli `BallTracker` ishlatadi, va README'da to'pni kuzatish "extremely difficult" deb yozilgan ([roboflow/sports](https://github.com/roboflow/sports)).

Raqamlar heatmap modellar tomonida. **WASB-SBDT** (BMVC 2023, MIT) kichik HRNet'ga **3 ta ketma-ket kadrni** kanal o'qi bo'ylab birlashtirib beradi (288×512 o'lchamda). Shu tarzda model to'pning harakatini ham "ko'radi" ([arXiv 2311.05237](https://arxiv.org/html/2311.05237v2)). Soccer to'plamidagi natijalar (τ=4 px):

| Usul | F1 | AP | FPS (eski GPU) |
|---|---|---|---|
| DeepBall (box/segment) | 44.5 | 26.3 | 44.6 |
| TrackNetV2 (heatmap) | 86.6 | 77.2 | 66.0 |
| WASB step=3 | **88.3** | 83.6 | 55.7 |
| WASB step=1 | 88.2 | **86.2** | 23.6 |

([arXiv 2311.05237](https://arxiv.org/html/2311.05237v2))

Ikkita cheklovni bilish kerak. Birinchisi, WASB'ning soccer weights'i ISSIA/D'Orazio to'plamida o'qitilgan. Bu oltita qo'zg'almas kamerali to'plam, broadcast PTZ emas, va uning litsenziyasi noma'lum. Shuning uchun tijoriy maqsad uchun **arxitekturani oling, weights'ni o'z label'laringizda qayta o'qiting**. Ikkinchisi, repo 2023-11 dan beri yangilanmagan ([GitHub](https://github.com/nttcom/WASB-SBDT)), shuning uchun PyTorch cu130'ga moslash kerak bo'lishi mumkin (xulosa). Muqobil **TrackNetV3** ning MIT litsenziyasi aniq **"pretrained model checkpoints"ni ham qamraydi** va repo faol ([TrackNetV3 LICENSE](https://github.com/qaz812345/TrackNetV3/blob/master/LICENSE)). Lekin u shuttlecock uchun yaratilgan. TrackNetV4 kodi litsenziyasi tasdiqlanmagan.

O'lcham bo'yicha muhim hisob: 1080p kadrni 288×512 ga kichraytirsangiz, 8–20 px to'p ~2–5 px'ga tushadi. RTX 5090'da **576×1024** kirish bilan o'qitish mantiqliroq (xulosa). Offline highlight uchun bu real vaqtdan ancha tez bo'lishi kutiladi.

### Tiling: oddiy, lekin qimmat

Ball modeli hali tayyor bo'lmasa yoki uni tekshirish kerak bo'lsa, **tiling** (kadrni bo'laklarga bo'lib detektordan o'tkazish) eng oddiy yo'l. SAHI ham, supervision'ning `InferenceSlicer`'i ham MIT ([SAHI](https://github.com/obss/sahi); [supervision](https://github.com/roboflow/supervision)). 1920×1080 kadr 640'lik bo'laklar va ~20% overlap bilan 8–12 bo'lakka bo'linadi. Bu kadr boshiga taxminan 30–60 ms degani (**tasdiqlanmagan** taxmin), offline uchun yetadi. Arzonroq gibrid: to'pni kuzatib, faqat oxirgi ma'lum pozitsiya atrofidagi ROI'ni kesib tekshirish, to'p yo'qolganda esa to'liq tiling'ga qaytish.

### Dataset: toza broadcast dataset yo'q, o'zingiz belgilaysiz

Tijoriy model o'qitish uchun aniq ruxsat berilgan broadcast futbol dataseti **topilmadi**. SoccerNet NDA ortida. Roboflow/sports ishlatadigan `football-players-detection` va `football-ball-detection` to'plamlarining litsenziya maydonlarini o'qib bo'lmadi, sahifa 403 qaytardi (**tasdiqlanmagan**). Boshqa Universe to'plamlari qidiruv natijalariga ko'ra CC BY 4.0 ([Futsal set](https://universe.roboflow.com/masters-program/futsal-player-and-ball-detection-ch025/dataset/)). Lekin CC BY faqat yuklovchining huquqini qamraydi, kadrlarning o'zi esa ko'pincha league yoki broadcaster'ga tegishli. SoccerNet-GSR baseline (sn-gamestate) va SportsLabKit GPL-3.0, sn-tracking repo'sida litsenziya umuman yo'q ([sn-gamestate](https://api.github.com/repos/SoccerNet/sn-gamestate)).

Shuning uchun eng xavfsiz yo'l: **huquqiga ega bo'lgan footage'dan kadrlarni o'zingiz belgilash** va bu ishni avtomatik vositalar bilan tezlashtirish. To'rt qadamli bootstrap aylanasi:

1. **Grounding DINO** (Apache-2.0) "soccer ball", "person" so'rovlari bilan keng kadrlarda dastlabki box'larni chiqaradi ([GroundingDINO](https://github.com/IDEA-Research/GroundingDINO)). **SAM2** (Apache-2.0) esa ularni video bo'ylab keyingi kadrlarga tarqatadi ([sam2](https://github.com/facebookresearch/sam2)).
2. Label'lar CVAT'da (MIT) qo'lda tuzatiladi.
3. RF-DETR va heatmap modeli o'qitiladi.
4. Endi RF-DETR o'zi keyingi partiya uchun pre-labeler bo'ladi. Bu active learning'ning o'zi.

SAM3 maxsus "SAM License" ostida: tijoriy foydalanishga ruxsat beradi, lekin harbiy/ITAR cheklovlari bor va Meta'ni sudga bersangiz bekor bo'ladi ([SAM3 LICENSE](https://github.com/facebookresearch/sam3/blob/main/LICENSE)). Heatmap modeli uchun label bundan ham arzon: har kadrda faqat to'p markazi nuqtasi va "ko'rinadi/ko'rinmaydi" bayrog'i. Hajm bo'yicha **tasdiqlanmagan** amaliy qoida: o'yinchilar uchun ~1–3k kadr, to'p bilan ~3–5k kadr. Kadrlar turli shot turlari va stadionlardan olinishi, to'p yo'q "hard negative" kadrlar ham bo'lishi kerak.

Universe to'plamlarini tashlab yuborish shart emas. Ularni **prototip va arxitektura tanlash uchun** ishlating. Production weights esa o'z label'laringizda o'qitilsin.

### Reframe: to'p, prognoz, o'yinchilar, keyin kadr markazi

Faqat to'pga qarab crop qilish mo'rt, chunki to'p yo'qoladi, to'siladi yoki kadrdan chiqadi. Tadqiqotlar to'pni o'yinchilar konteksti, "diqqat hududi" va silliqlash bilan birlashtiradi ([AUTH slides](https://icarus.csd.auth.gr/wp-content/uploads/2021/09/Cinematography-Issues-in-Sports-Filming-v2.5-Summary.pdf); [IEICE 2020](https://ken.ieice.org/ken/paper/20200304d1XG/eng/)). Asosiy production misoli **AWS Elemental Inference** (2026-fevral). FOX Sports va NBCU uni sinab ko'rgan, lekin algoritmi ochiq emas ([AWS blog](https://aws.amazon.com/blogs/media/how-aws-built-a-live-ai-powered-vertical-video-capability-for-fox-sports-with-aws-elemental-inference)). Shundan amaliy qoida chiqadi: broadcast kamera operatori allaqachon action'ni kuzatib turibdi, demak kadr markazi kuchli "zaxira javob".

Crop maqsad nuqtasi quyidagi ustuvorlik bilan tanlanadi:

1. Ishonch yuqori bo'lsa, to'pning o'zi.
2. 1 soniyadan qisqa uzilishda Kalman filtri prognoz qilgan to'p pozitsiyasi.
3. Oxirgi to'p pozitsiyasi atrofidagi o'yinchilarning og'irlikli markazi yoki eng zich guruhi.
4. Broadcast kadrning markazi.

Kamera almashganda crop qaytadan boshlanadi. Close-up va replay'larda to'p o'rniga odam yoki saliency bo'yicha kadrlanadi.

Tracker'lar ByteTrack, BoT-SORT va OC-SORT, hammasi MIT, supervision'da esa MIT ByteTrack bor ([ByteTrack](https://github.com/FoundationVision/ByteTrack); [OC_SORT](https://github.com/noahcao/OC_SORT)). PLAN'dagi One-Euro filtri "live" uchun yaratilgan. **Sizning ishingiz offline**, ya'ni kelajakdagi kadrlarni ham ko'rish mumkin. Shuning uchun ikki o'tishli silliqlash (Rauch–Tung–Striebel smoother yoki x-yo'liga Savitzky–Golay filtri) yaxshiroq natija beradi (xulosa). Pan tezligi va tezlanishini cheklang, markaziy ~30% hududda dead-zone qoldiring. Tijoriy ishga tushirishdan oldin real vaqtli to'p kuzatish bilan reframe qilish bo'yicha **USPTO 12505671** patentining da'volarini tekshirtiring ([USPTO 12505671](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12505671)). Patent da'volari o'qilmagan.

## VLM: asosiy detektor emas, re-ranker va label yozuvchi

### Zero-shot VLM'lar soccer'da zaif

Dalillar bir tomonga ishora qiladi. SoccerChat'da oddiy Qwen2-VL-7B SoccerNet'ning 6 sinfli event klassifikatsiyasida **weighted F1 0.17** olgan. Soccer ma'lumotida LoRA bilan fine-tune qilingandan keyin esa 0.57 ga chiqqan ([SoccerChat](https://arxiv.org/pdf/2505.16630)). Mustaqil VideoHEDGE tekshiruvida hatto fine-tune qilingan SoccerChat ham 1,035 ta tasdiqlangan javobga qarshi 1,885 ta "gallyutsinatsiya" (to'qib chiqarilgan javob) bergan ([VideoHEDGE](https://arxiv.org/pdf/2601.08557)). Uzun broadcast'larda highlight topish esa hammasi uchun qiyin. SVHighlights benchmark'ida (320 ta to'liq broadcast) eng yaxshi baseline mAP 23.14 olgan, Qwen2.5-VL-7B captioner sifatida 13.54 ([SVHighlights](https://www.alphaxiv.org/abs/2606.06926.md)). Gemini va GPT u yerda baholanmagan. Gemini 3.x/4 ning SoccerNet action spotting bo'yicha mustaqil natijasi ham topilmadi. Xulosa: VLM nomzodlarni **topmaydi**, balki arzon signallar topgan nomzodni **tekshiradi**. U event turini aniqlaydi, hayajonni baholaydi va caption yozadi.

### Gemini: arzon, butun match'ni ko'radi, lekin shartlari bor

Gemini yagona yirik cloud API bo'lib, uzun videoni native qabul qilishi hujjatlashtirilgan. 1M context'da low resolution bilan **3 soatgacha** video qabul qiladi. Standart 1 fps, ammo `fps` ni o'zgartirish mumkin (faqat "static" rejimda). Narx: low res'da ~100 token/s (kadr boshiga 66), default'da ~300 token/s (258), ustiga audio uchun 32 token/s ([Gemini video docs](https://ai.google.dev/gemini-api/docs/video-understanding)). 2026-oktabr holatiga pricing sahifasidagi qatorlar quyidagicha ([Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)). Hisoblar mening arifmetikam, asosi hujjatdagi token stavkalari:

| Model | Kirish, $/1M | 90 daq match (low res, ~540k token) | 20 s klip, 5 fps (~26k token) |
|---|---|---|---|
| gemini-3.1-flash-lite | $0.25 (batch $0.125) | **~$0.135** (batch ~$0.07) | ~$0.0066 |
| gemini-3.5-flash-lite | $0.30 | ~$0.16 | ~$0.008 |
| gemini-3.8-flash | $0.75 → 2027-01-01 dan $1.50 | ~$0.41 → ~$0.81 | ~$0.02 |
| gemini-4-argon | $2.00 → 2026-12-01 dan $4.00 | ~$1.08 → ~$2.16 | ~$0.05 |

Default resolution'da match ~1.62M token bo'ladi, bu 1M context'dan oshib ketadi. Shuning uchun to'liq match low res'da yoki ikkita taym sifatida yuboriladi. Eng arzon va aniq sxema: butun match'ni qo'pol ko'rib chiqish, keyin qisqa nomzod kliplarni yuqori fps'da qayta tekshirish. 30–50 nomzodni qayta tartiblash match boshiga ~$0.05–1 turadi. 1 fps'da tez event'lar (zarba → gol) bir necha soniya xato bilan belgilanadi. Shuning uchun Gemini bergan vaqtni ±10 s oyna deb qabul qiling va aniq chegarani lokal signal bilan toping.

Shartlarda uch narsa muhim ([Gemini API terms](https://ai.google.dev/gemini-api/terms)). Birinchisi, **bepul tier'da** kiritilgan kontent mahsulotlarni yaxshilashga ishlatiladi va uni odamlar o'qishi mumkin. Pullik tier'da prompt va javoblar o'qitishga ishlatilmaydi. Match footage'i uchun **faqat paid tier**. Ikkinchisi, Google javoblarga egalik da'vo qilmaydi, ya'ni sarlavha va caption'larni tijoriy ishlatish mumkin. Uchinchisi, eng muhimi: **"You may not use the Services to develop models that compete with the Services."** Faqat football highlight topadigan kichik model umumiy AI API bilan "raqobat" qilmaydi deb bahslashish mumkin. Lekin band keng yozilgan, va bu huquqiy baho, men uni tasdiqlay olmayman. Eng toza yechim: Gemini'ni **runtime'da** ishlating (tartiblash, caption, sarlavha). Uning javoblarini esa o'z modelingiz uchun training label sifatida saqlamang, yoki saqlashdan oldin yuristga ko'rsating. Yana bir eslatma: EEA, Shveytsariya yoki UK foydalanuvchilariga xizmat ko'rsatsangiz, faqat Paid Services ishlatilishi shart.

OpenAI API'da native video kiritish tasdiqlanmagan, kadrlarni rasm sifatida yuborasiz ([openai-node #1778](https://github.com/openai/openai-node/issues/1778)). Claude API ham bu sessiyada tekshirilmagan, mening bilishimcha u rasmlarni qabul qiladi, videoni emas (**tasdiqlanmagan**).

### Lokal Qwen3-VL: label uchun toza yo'l, native Windows'da ham ishlaydi

**Qwen3-VL** Apache-2.0 litsenziyasida. Uning model kartasida aniq "Text–Timestamp Alignment ... timestamp-grounded event localization" deb yozilgan. 8B varianti BF16'da ~9B parametr, native context 256K ([Qwen3-VL-8B](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct)). Oilada 2B, 4B, 8B, 32B, 30B-A3B MoE va 235B bor ([30B-A3B AWQ](https://huggingface.co/QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ/blob/main/README.md)). Har o'lchamning litsenziyasi rasmiy repo'da alohida tekshirilmagan. **Gemma 4** ham Apache-2.0, lekin u videoni **maksimal 60 soniya, 1 fps** qabul qiladi. Demak u to'liq match skaneri emas, klip re-ranker yoki captioner bo'la oladi ([Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)). Qwen3-VL-2B'dan fine-tune qilingan TimeLens2 temporal grounding'da kuchli ([TimeLens2](https://arxiv.org/pdf/2607.17423)). Uning litsenziyasini alohida tekshirish kerak.

32 GB'da 8B BF16 (~18 GB weights, ~10 GB video KV cache uchun qoladi), 30B-A3B AWQ (~17 GB, tez, chunki faqat 3B parametr faol) yoki 32B 4-bit (~20 GB) sig'adi. Bu **tasdiqlanmagan** taxmin. 20 soniyalik klip 2–4 fps'da bemalol sig'adi, to'liq match esa sig'maydi va sliding window kerak bo'ladi. **Windows uchun eng muhim fakt:** vLLM'da rasmiy Windows qo'llovi yo'q. Tavsiya etilgan yo'l WSL2 yoki Docker, community wheel'lar esa norasmiy ([Docker blog](https://www.docker.com/blog/docker-model-runner-vllm-windows); [dev.to](https://dev.to/aivrar/running-vllm-natively-on-windows-4ahm)). Siz WSL2'siz ishlashni afzal ko'rasiz, shuning uchun **oddiy `transformers`** bilan Qwen3-VL ishlating. U native ishlaydi, sekinroq, lekin offline label yaratish uchun yetadi. SoccerChat 7B video VLM'ni bitta workstation'da LoRA bilan o'qitish mumkinligini ko'rsatgan ([SoccerChat](https://arxiv.org/pdf/2505.16630)). Bu keyinchalik Qwen3-VL'ni o'z label'laringizda moslash yo'li ochiqligini bildiradi.

InternVL3.5, LLaVA-Video, VideoLLaMA3 va MiniCPM-V'ning litsenziyalari tekshirilmagan. MiniCPM tarixan tijoriy ro'yxatdan o'tishni talab qilgan.

### VLM label'larini qanday "tozalash" kerak

VLM label'i shovqinli. Pseudo-label xatolarining uch turi bor: **chegaralar noaniq, ba'zi event'lar tushib qoladi, qo'shni event'lar bittaga birlashadi** ([NoCo](https://arxiv.org/html/2501.11124v1)). Hatto SoccerNet-Caption'dagi odam qo'ygan vaqtlar ham siljigan. MatchTime mualliflari 49 match'ni qo'lda to'g'rilashga majbur bo'lgan ([MatchTime](https://www.arxiv.org/abs/2406.18530)). Soccer uchun maxsus "VLM label'idan o'quvchi model" natijasi topilmadi. Lekin umumiy weak-supervision amaliyotidan quyidagi retsept chiqadi:

1. VLM'dan qat'iy JSON so'rang: event turi, boshlanish/tugash, confidence va dalil ("replay ko'rsatildi", "hisob o'zgardi"). Confidence'ni namuna og'irligi sifatida saqlang.
2. Kamida ikki manba kelishgan event'larni qoldiring, masalan Qwen3-VL + audio peak yoki + OCR o'zgarishi. Kelishmaganlari UI'ga, odamga boradi.
3. 10–20 match'dan iborat qo'lda belgilangan **gold set** yarating. U hech qachon training'ga kirmaydi va faqat VLM va model aniqligini o'lchaydi.
4. O'quvchini soft label va Gaussian bilan silliqlangan vaqt maqsadlari bilan o'qiting, shunda vaqt titrashi "yutiladi".
5. Aylanani takrorlang: o'quvchi bashorat qiladi, VLM kelishmovchiliklarni qayta tekshiradi, label'lar yaxshilanadi.

Bu soddalashtirilgan sintez, bitta manbadan olinmagan.

### O'zbekcha sarlavhalar

VLM'larning o'zbek tilidagi sifati bo'yicha hech qanday benchmark topilmadi. Gemma 4 35+ qo'llanadigan va 140+ pretraining tilini e'lon qiladi, lekin o'zbek tilini nomlamaydi ([Gemma 4](https://ai.google.dev/gemma/docs/core/model_card_4)). Ikki bosqichli dizayn xavfsiz. Avval VLM inglizcha yoki JSON ko'rinishida faktlarni beradi (kim, nima, daqiqa, hisob). Keyin kuchli cloud LLM o'zbekcha (lotin) sarlavhani yozadi. O'yinchi va jamoa nomlari VLM'ning "tanishidan" emas, **qat'iy glossariy yoki match metadata'sidan** olinadi.

## Litsenziya tuzoqlari bir jadvalda

| Narsa | Muammo | Holat | Nima qilish kerak |
|---|---|---|---|
| **VideoMAE V2 weights** | CC BY-NC 4.0, kodi esa MIT | Tasdiqlangan ([HF](https://huggingface.co/OpenGVLab/VideoMAEv2-giant)) | V-JEPA 2 (MIT) ishlating |
| **DEIMv2** | 2026-08-24 dan non-commercial, Gitee mirror'lari eskirgan | Tasdiqlangan ([LICENSE](https://github.com/Intellindust-AI-Lab/DEIMv2/blob/main/LICENSE.md)) | DEIM v1, D-FINE yoki RF-DETR ishlating |
| **RF-DETR XL/2XL va Atto/Femto/Pico** | PML 1.0, Roboflow plan va credit'larga bog'langan | Tasdiqlangan README, shartlar ikkilamchi manbadan ([forum](https://discuss.roboflow.com/t/plan-required-for-new-rfdetrlarge-sizes/11827)) | Faqat Nano/S/M/L |
| **Ultralytics, YOLOv10/12/13, boxmot** | AGPL-3.0 | Tasdiqlangan ([ultralytics](https://github.com/ultralytics/ultralytics)) | Ishlatmang yoki Enterprise litsenziya sotib oling |
| **SoccerNet** (va undan o'qitilgan checkpoint'lar) | NDA, hosila datasetlar non-commercial | NDA matni **tasdiqlanmagan** ([data](https://www.soccer-net.org/data)) | Production weights'ga qo'shmang |
| **Gemini "competing models"** | Javoblardan model o'qitish huquqiy jihatdan noaniq | Band tasdiqlangan, uni talqin qilish **tasdiqlanmagan** ([terms](https://ai.google.dev/gemini-api/terms)) | Training label'larini Qwen3-VL bilan yarating |
| **Gemini free tier** | Kontentni odamlar o'qiydi, o'qitishga ishlatiladi | Tasdiqlangan | Faqat paid |
| **T-DEED, sn-gamestate, SportsLabKit** | GPL-3.0 | Tasdiqlangan ([T-DEED](https://github.com/arturxe2/T-DEED)) | E2E-Spot (BSD-3) yoki o'z kodingiz |
| **DINOv3** | Tijoriy mumkin, lekin "Built with DINOv3" yozuvi majburiy | Tasdiqlangan ([license](https://ai.meta.com/resources/models-and-libraries/dinov3-license/)) | DINOv2/SigLIP2 yoki yozuvni qabul qiling |
| **WASB soccer weights** | ISSIA to'plamining litsenziyasi noma'lum | **Tasdiqlanmagan** | Arxitektura MIT, weights'ni qayta o'qiting |
| **Roboflow Universe to'plamlari** | Litsenziya maydoni o'qilmadi, kadrlar broadcaster'ga tegishli | **Tasdiqlanmagan** | Faqat prototip uchun |
| **SoccerChat dataset** | CC BY-NC 4.0 | Tasdiqlangan ([dataset](https://datasets.simula.no/soccerchat/)) | Ishlatmang |
| **USPTO 12505671** | Real vaqtli to'p kuzatish bilan reframe patenti | Da'volari o'qilmagan | Tijoriy ishga tushirishdan oldin FTO tekshiruvi |

## Tavsiya etilgan stack va yangilangan M1–M6

### Stack

| Qatlam | Tanlov | Litsenziya |
|---|---|---|
| Nomzodlar | librosa RMS/flux, faster-whisper large-v3, EasyOCR score-bug, PySceneDetect | ISC/MIT/Apache/BSD |
| Feature cache | V-JEPA 2 ViT-L (nomzod oynalarda), SigLIP2-B yoki DINOv2-B (1–2 fps), BEATs/PANNs, Whisper matni | MIT / Apache / MIT* |
| Highlight ranker v1 | LightGBM: pooled embedding'lar + skalyar signallar | MIT |
| Highlight ranker v2 | 1D-conv/BiGRU temporal head (PyTorch), keyin ixtiyoriy E2E-Spot | o'z kodingiz / BSD-3 |
| O'yinchi detektori | RF-DETR Medium yoki Large (`rfdetr` pip) | Apache-2.0 |
| To'p detektori | WASB-uslubidagi 3 kadrli HRNet heatmap, 576×1024, o'z label'laringizda | MIT (kod) |
| Tracking va silliqlash | supervision ByteTrack, Kalman + RTS/Savitzky–Golay, dead-zone | MIT |
| Label bootstrap | Grounding DINO + SAM2 → CVAT | Apache / Apache / MIT |
| Lokal VLM (labeler) | Qwen3-VL-8B (BF16) yoki 30B-A3B AWQ, `transformers` orqali | Apache-2.0 |
| Cloud VLM (runtime) | gemini-3.1-flash-lite (batch) yoki 3.8-flash, faqat paid tier | Proprietary, shartlar bilan |
| Sarlavha | cloud LLM + jamoa/o'yinchi glossariysi | — |

\* BEATs/PANNs litsenziyasi bu sessiyada tasdiqlanmagan.

### PLAN.md ga nisbatan yangilangan milestone'lar

Asosiy o'zgarish shu: **dataset yig'ish M6'da emas, M1'dan boshlanadi**. Har bir ishlangan match keyingi modelni o'qitish uchun xom ashyo qoldiradi. Muddatlar sizning PLAN'ingizdagi bahoga qo'shimcha sifatida berilgan va taxmin.

| M | PLAN'dagi mazmun | Nima o'zgaradi / qo'shiladi | Tayyor mezoni (qo'shimcha) |
|---|---|---|---|
| **M1** Nomzodlar (2–3 kun → 3–4 kun) | Audio peak, Whisper kalit so'zlari, `candidates.json` | Har nomzodga skalyar feature'lar (`loudness_z`, `keyword_hits`, davomiylik) yoziladi. `data/features/` cache sxemasi (har match uchun parquet/npz) yaratiladi. Whisper transkripti to'liq saqlanadi | `candidates.json` + `features/<match>.parquet`, ≥90% gol recall (avvalgidek) |
| **M2** Gol tasdiqlash (o'zgarishsiz) | Score OCR, debounce, VAR, match soati | OCR natijasi **weak label** sifatida saqlanadi (`labels/weak/<match>.json`, offset bilan) | 100% gol, 0 soxta gol (avvalgidek) |
| **M3** Avtomatik kesish (1–2 kun → 2–3 kun) | Oynalar, scene snap, replay | Qo'shiladi: **oddiy review CLI/UI** (accept/reject + sabab: "gol", "xavfli", "zerikarli", "replay xato"). Bu PLAN'da M6'da edi. Natija `labels/human/` ga yoziladi | Har match uchun barcha nomzodlar belgilanadi va dataset o'sa boshlaydi |
| **M4** Reframe + birinchi o'z modelimiz (3–5 kun → 6–9 kun) | RF-DETR fine-tune, BallTracker, One-Euro, blur fallback | **M4a:** Universe to'plamida RF-DETR-M bilan prototip (litsenziyasi tekshirilmagani hujjatga yoziladi). **M4b:** o'z footage'ingizdan 1–3k kadr, Grounding DINO + SAM2 + CVAT bilan belgilanadi va RF-DETR qayta o'qitiladi. **M4c:** WASB-uslubidagi to'p heatmap modeli to'p markazlarida o'qitiladi. **M4d:** ustuvorlik zanjiri to'p → Kalman → o'yinchilar markazi → kadr markazi, offline RTS silliqlash. One-Euro faqat zaxira | 10 klipda silliq kadr (avvalgidek) + to'p detektorining o'z test kadrlarida F1'i o'lchanadi. Production weights'da Universe/ISSIA/SoccerNet ma'lumoti yo'q |
| **M5** Brending va eksport (2–3 kun) | GOAL, logo, hisob, subtitr, NVENC | O'zbekcha sarlavha: JSON faktlar → cloud LLM + glossariy (ixtiyoriy, paid tier). 25 daqiqa/match byudjetiga V-JEPA 2 feature cache ham kiritiladi (faqat nomzod oynalarda) | `fshorts run` < 25 daqiqa, feature cache bilan birga |
| **M6** Highlight modeli va VLM (yangi mazmun, bosqichma-bosqich) | PLAN'da: Gemini tartiblash, UI, dataset, sayt | **M6a** (~10 match'dan keyin): LightGBM ranker v1, leave-one-match-out baholanadi. Qoidalarga asoslangan tartiblash bilan solishtiriladi. **M6b:** Qwen3-VL lokal labeler (`transformers`, Windows native): nomzodlarga JSON label, agreement filtri, 10 match'lik gold set. **M6c:** Gemini faqat runtime re-ranker/caption sifatida, uning javoblari training'ga kirmaydi. **M6d** (~20+ match): temporal head (1D-conv/BiGRU), butun match bo'ylab spotting. **M6e:** sayt (API, navbat), avvalgidek | M6a: ranker qoidalardan yaxshiroq top-5 precision beradi. M6b: VLM label'ining gold set'dagi precision/recall'i hujjatlashtiriladi |

M1–M5 ga qo'shilgan ish taxminan **4–6 kun** qo'shadi (asosan M4b/M4c dagi label'lash). Evaziga M6 boshlanganda sizda allaqachon weak label, odam label'lari va feature cache bo'ladi, nol emas.

## Xulosa

Bu tadqiqotning asosiy burilishi shu: loyihaning raqobatdagi ustunligi model arxitekturasida emas, **litsenziyasi toza, o'zi o'sib boradigan dataset**da. Ommaviy ma'lumotlarning deyarli hammasi tijoriy maqsadga yopiq: SoccerNet NDA, SoccerChat NC, VideoMAE V2 NC, DEIMv2 endi NC. Shuning uchun SoccerNet'da yaxshi natija bergan raqobatchilarning tayyor checkpoint'lari sizga yaramaydi. Sizning pipeline'ingiz esa har match'da bepul weak label (OCR), arzon odam label'i (accept/reject) va lokal VLM label'ini chiqaradi. Bu aynan raqobatchilar qonuniy ololmaydigan narsa. Demak M1'dan boshlab feature cache va label sxemasini to'g'ri qurish M4'dagi detektor tanlovidan ham muhimroq qaror.

Ikkinchi xulosa xarajatga oid. Gemini bilan match boshiga bir necha sent turadigan "aqlli" tartiblash allaqachon mavjud. Shunday ekan, o'z highlight modelingizni qurishning sababi pul tejash emas: **API shartlariga bog'liq bo'lmaslik va football'ga xos sifat**. Bu ikki maqsad faqat training label'lari lokal Apache modeli va odamdan kelgandagina birga erishiladi. Ochiq qolgan savollar ham bor, va ular faqat o'z o'lchovingiz bilan yopiladi. V-JEPA 2, WASB va Qwen3-VL'ning RTX 5090 + cu130 + Windows'dagi real tezligi va moslashuvi, o'z ma'lumotingizda qancha match'dan keyin LightGBM qoidalardan o'tib ketishi, va SoccerNet hamda Gemini shartlarining yuridik talqini hali noma'lum. Uchinchisi texnik emas: uni tijoriy ishga tushirishdan oldin yurist hal qilishi kerak.
