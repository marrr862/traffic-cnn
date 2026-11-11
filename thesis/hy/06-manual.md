# 6 Օգտագործողի ձեռնարկ

## 6.1 Համակարգային պահանջներ և տեղադրում

Ծրագիրն աշխատում է macOS, Linux և Windows օպերացիոն համակարգերում՝ Python 3.10–3.13 տարբերակներով։ Առաջարկվում է առնվազն 8 ԳԲ օպերատիվ հիշողություն։ Գրաֆիկական արագացուցիչը պարտադիր չէ. Apple Silicon համակարգիչներում օգտագործվում է MPS սարքը, NVIDIA քարտերով համակարգիչներում՝ CUDA, իսկ մնացած դեպքերում՝ CPU (ավելի դանդաղ)։

Տեղադրման համար պետք է կատարել հետևյալ հրամանները.

```
git clone https://github.com/marrr862/traffic-cnn.git
cd traffic-cnn
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/download_assets.py
```

Վերջին հրամանը ներբեռնում է չորս ուսուցանված մոդելները (vehicle-road-yolov8s-long, vehicle-road-yolov8s, vehicle-road-combined, vehicle-hires-960) և երկու ցուցադրական տեսանյութերը՝ ստուգելով դրանց SHA-256 հեշերը։ Ուղիղ հոսքով YouTube-ից աշխատելու համար անհրաժեշտ է լրացուցիչ տեղադրել `pip install -e '.[live]'`։

## 6.2 Միջերեսի գործարկում և տեսանյութի վերլուծություն

Միջերեսը գործարկվում է հրամանով.

```
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

macOS-ում կարելի է պարզապես գործարկել `run_app.command` ֆայլը։ Դիտարկիչում բացվում է http://127.0.0.1:8501 հասցեն։ Տեսանյութի վերլուծության համար.

1. «Տեսանյութի վերլուծություն» ներդիրում ընտրել աղբյուրը՝ ցուցադրական տեսանյութ, սեփական ֆայլ (MP4, AVI, MOV, MKV) կամ ուղիղ հոսք (տեսախցիկի համար կամ URL).
2. ընտրել մոդելը (լռելյայն՝ առաջարկվողը) և մուտքի չափը.
3. «Հաշվման գծեր» բաժնում կադրի վրա երկու սեղմումով տեղադրել հիմնական գծի A և B կետերը, անհրաժեշտության դեպքում՝ լրացուցիչ գծեր.
4. «Տրամաչափում» բաժնում ընտրել տրամաչափման եղանակը. առանց տրամաչափման (միայն հաշվարկ), պատրաստի JSON ֆայլ կամ ձեռքով չորս կետ։ Ձեռքով եղանակի դեպքում կադրի վրա նշվում են ճանապարհի ուղղանկյան չորս անկյունները (հեռավոր ձախ, հեռավոր աջ, մոտ աջ, մոտ ձախ) և մուտքագրվում են դրա լայնությունը, երկարությունը մետրերով և գոտիների քանակը։ Չափերը կարելի է որոշել գծանշումից (օրինակ, ընդհատվող գծի պարբերությունը) կամ քարտեզից.
5. ընտրել վստահության շեմը (լռելյայն 0,3), սարքը, հետագծման ռեժիմը և վերլուծության միջակայքը.
6. սեղմել «Մշակել տեսանյութը» կոճակը։

Մշակման ընթացքում ցուցադրվում է ընթացիկ կադրը և առաջընթացը, իսկ ուղիղ հոսքի դեպքում մշակումը կարելի է կանգնեցնել ցանկացած պահի՝ արդյունքները պահպանելով։

## 6.3 Արդյունքների մեկնաբանումը

Ավարտից հետո ցուցադրվում են.

- հատումների ընդհանուր քանակը, ըստ ուղղությունների և դասերի, ինտենսիվությունը մեքենա/ժամ.
- տրամաչափման առկայության դեպքում՝ միջին, մեդիան և 85-րդ պերցենտիլ արագությունները, միջին խտությունը, սպասարկման մակարդակը և q = k·v ստուգման արդյունքը.
- գրաֆիկներ ժամանակի ընթացքում՝ տեսանելի մեքենաներ, կուտակային հաշվարկ, ինտենսիվություն և արագություն ըստ միջակայքերի, արագությունների բաշխում.
- ջերմային քարտեզը և հետագծերը.
- նշագրված տեսանյութը և բոլոր ֆայլերի ներբեռնման կոճակները։

Ուղղությունների անվանումները կախված են գծի կետերի հերթականությունից։ Հորիզոնական գծի համար, որը տեղադրված է ձախից աջ, «դեպի կադրի ստորին եզր» նշանակում է դեպի տեսախցիկ շարժվող մեքենաներ, եթե տեսախցիկը ուղղված է ճանապարհի երկայնքով։

Եթե ծրագիրը ցույց է տալիս հավաստիության նախազգուշացում (օրինակ, մեդիան արագությունը գերազանցում է 160 կմ/ժ կամ ինտենսիվությունը գերազանցում է գոտու թողունակությունը), պետք է ստուգել տրամաչափման չափերը, գոտիների քանակը և արդյոք տեսանյութը արագացված չէ։ Արագացված տեսանյութի համար հրամանային տողում տրվում է `--time-scale` գործակիցը։

Կարճ տեսանյութի ինտենսիվությունը (մեքենա/ժամ) հաշվարկային մեծություն է և չի նշանակում, որ ամբողջ ժամվա ընթացքում հոսքը նույնն է։ Արժանահավատ ժամային ինտենսիվության համար անհրաժեշտ է առնվազն 15 րոպե դիտարկում։

## 6.4 Հաշվարկի ստուգումը սեփական տեսանյութում

Սեփական տեսանյութում ծրագրի ճշտությունը ստուգելու համար «Հաշվարկի ստուգում» ներդիրում ընտրվում է ավարտված արդյունքը և «Նշագրում հավելվածում» ռեժիմը։ Ցուցադրվում են սկզբնական կադրերը առանց CNN-ի նշագրման, որպեսզի օգտագործողի նշագրումը անկախ լինի ծրագրի կանխատեսումներից։ Կադրերով շարժվելով՝ յուրաքանչյուր իրական մեքենայի համար նշվում են հատման կադրերի միջակայքը, դասը և ուղղությունը։ Նշագրումը պահպանվում է `manual-reference.json` ֆայլում։ Համեմատման արդյունքում ցուցադրվում են համընկած, բաց թողնված և ավելորդ իրադարձությունները, դասի սխալները և precision, recall, F1 ցուցանիշները։

## 6.5 Հրամանային տող

Բոլոր հնարավորությունները հասանելի են նաև հրամանային տողից, ինչը հարմար է մեծ քանակությամբ տեսանյութերի մշակման համար.

```
traffic-cnn analyze --video data/video/vehicles.mp4 \
  --weights runs/experiments/vehicle-road-yolov8s-long/weights/best.pt \
  --output outputs/my-run --line 0 1296 3839 1296 \
  --extra-line 0 1700 3839 1700 \
  --calibration configs/calibration-vehicles.json \
  --imgsz 960 --device mps
```

Հիմնական պարամետրերն են՝ `--line` (հիմնական գիծ), `--extra-line` (լրացուցիչ գիծ, կարելի է կրկնել), `--calibration` (տրամաչափման JSON), `--conf` (վստահության շեմ), `--imgsz` (մուտքի չափ), `--device` (cpu, mps, cuda), `--tile 640` (սալիկային հայտնաբերում), `--time-scale` (արագացված տեսանյութի գործակից), `--interval-seconds` (վերլուծության միջակայք), `--max-seconds` (ուղիղ հոսքի տևողություն)։ Ուղիղ հոսքի համար `--video` պարամետրին տրվում է տեսախցիկի համարը կամ `rtsp://…` հասցեն։

Տրամաչափման JSON ֆայլը ունի հետևյալ կառուցվածքը.

```
{
  "image_points": [[1252, 787], [2298, 803], [5039, 2159], [-550, 2159]],
  "width_m": 25,
  "length_m": 250,
  "lanes": 4
}
```

## 6.6 Մոդելի ուսուցումը սեփական տվյալներով

Թիրախային տեսախցիկի պատկերներով լրացուցիչ ուսուցումը կբարձրացնի ճշտությունը։ Դրա համար անհրաժեշտ է պատրաստել YOLO ձևաչափի հավաքածու նույն հինգ դասերով (`configs/vehicles.yaml` ձևանմուշ), ստուգել այն `scripts/audit_dataset.py` սկրիպտով և գործարկել ուսուցումը.

```
python scripts/run_experiment.py --name my-camera \
  --data configs/my-camera.yaml --epochs 15 --imgsz 960 --device mps
```

Բոլոր պատկերները, այդ թվում՝ առանց մեքենաների, պետք է ունենան նշագրման ֆայլ, իսկ թիրախային դասի չնշագրված մեքենաներ չպետք է լինեն։ Train, val և test ընտրանքները պետք է բաժանել ըստ տեսախցիկների կամ տեսահաջորդականությունների, այլ ոչ թե հարևան կադրերով, հակառակ դեպքում թեստային արդյունքները կլինեն լավատեսական։ Ավարտված փորձը ավտոմատ կհայտնվի միջերեսի մոդելների ցանկում։

# Եզրակացություն

Ավարտական աշխատանքում մշակվել է Python ծրագրային միջոց, որը տեսախցիկի տեսանյութից ավտոմատ կերպով որոշում է տրանսպորտային միջոցների շարժման և երթևեկության հոսքի հիմնական բնութագրերը։ Աշխատանքի նպատակը իրագործված է, և ստացվել են հետևյալ արդյունքները։

1. Վերլուծվել են երթևեկության հոսքի բնութագրերը (ինտենսիվություն, խտություն, ժամանակային և տարածական միջին արագություն, սպասարկման մակարդակ) և դրանց չափման եղանակները։ Որպես դետեկտոր ընտրվել է YOLOv8 փաթույթային նեյրոնային ցանցը, հետագծման համար՝ ByteTrack ալգորիթմը, իսկ մետրական չափումների համար՝ ճանապարհային հարթության հոմոգրաֆիկ տրամաչափումը։
2. Երկու բաց աղբյուրներից պատրաստվել է հինգ դասի տրանսպորտային միջոցների կորպուս. VisDrone2019-DET (218 242 շրջանակ ուսուցման ընտրանքում) և MIO-TCD (30 000 պատկեր)։ Բոլոր փոխակերպումները ավտոմատացված են և վերարտադրելի, իսկ անորոշ դասի շրջանակները դիմակավորված են։
3. Կատարվել է տասը վերարտադրելի ուսուցման փորձ։ Ցույց է տրվել, որ ուսուցման փոխանցումը սահմանափակ տվյալների պայմաններում անհրաժեշտ է (13,8% ընդդեմ 2,6% mAP50), մուտքի չափի մեծացումը 640-ից 960 պիքսել էապես բարելավում է փոքր օբյեկտների հայտնաբերումը (+11 կետ), իսկ թիրախային տիրույթի տվյալների ավելացումը վերացնում է տիրույթի տեղաշարժը (MIO-TCD-ում 15,1% → 83,7%)։ Ավելի մեծ YOLOv8s մոդելը և նրա ուսուցման երկարացումը ևս 12 դարաշրջանով բարելավել են արդյունքները երկու տիրույթներում. առաջարկվող vehicle-road-yolov8s-long մոդելը ունի 51,4% mAP50 VisDrone-ում և 90,2% MIO-TCD-ում։
4. Իրականացվել է հաշվման գծերի հատման կանոն հիստերեզիսով, գծից արդեն անցած մեքենաների հաշվարկով և նույն մեքենայի կրկնակի ID-ների զտիչով, արագության գնահատում սահող պատուհանով, խտության և LOS-ի հաշվարկ, q = k·v ստուգում և ֆիզիկական հավաստիության ավտոմատ ստուգում։ Մշակվել է սալիկային հայտնաբերման ռեժիմ, որը փոքր օբյեկտների համար բարձրացնում է mAP50-ը մինչև 6,7 կետով։
5. Մշակվել է հայերեն միջերես, հրամանային տող, ուղիղ հոսքի (RTSP, HLS, YouTube) աջակցություն, արդյունքների արտահանում CSV/JSON ձևաչափերով և հաշվարկի ստուգման գործիք։ Ծրագիրը ծածկված է 73 ավտոմատ թեստով։
6. Անկախ UA-DETRAC տեսանյութում առաջարկվող մոդելը հայտնաբերել է մեքենաների 99,0%-ը և ճիշտ հաշվել բոլոր 5 հատումները։ Մայրուղու տեսանյութում վերջնական տարբերակը ճիշտ է հաշվել բոլոր 10 մեքենաները ճիշտ ուղղություններով (երկու բեռնատարները առաջարկվող մոդելը դասակարգել է որպես ավտոբուս)։ Արագության երկու անկախ եղանակները համընկնում են միջինը 2–3%-ի սահմաններում։ Հավաստիության ստուգումը ավտոմատ կերպով հայտնաբերել է արագացված տեսանյութը, որում առանց ստուգման կստացվեր ֆիզիկապես անհնար ինտենսիվություն։

Ստացված արդյունքները ունեն որոշակի սահմանափակումներ. արտաքին ստուգման ծավալը փոքր է, արագության բացարձակ ճշտությունը չի ստուգվել անկախ չափիչով, իսկ բոլոր տեսանյութերը ցերեկային են։ Աշխատանքի զարգացման հիմնական ուղղություններն են.

- հաշվարկի ստուգումը տասնյակ նշագրված տեսանյութերով՝ գիշերը, անձրևի ժամանակ և խցանումներում.
- արագության ստուգումը հայտնի արագություններով հավաքածուով (օրինակ, BrnoCompSpeed [20]) կամ ռադարի տվյալներով.
- լրացուցիչ ուսուցումը Հայաստանի ճանապարհների տեսախցիկների պատկերներով.
- մի քանի seed-ով կրկնված ուսուցում՝ արդյունքների վիճակագրական հուսալիությունը գնահատելու համար.
- հաշվարկը ըստ առանձին երթևեկության գոտիների և խտության հաշվարկը մարդատար ավտոմեքենայի համարժեքով.
- այլ հետագծիչների (BoT-SORT, DeepSORT) համեմատություն և ավտոմատ տրամաչափում ճանապարհի գծանշումից։

Մշակված ծրագիրը կարող է օգտագործվել երթևեկության ուսումնասիրությունների, ուսումնական նպատակների և ավելի մեծ ինտելեկտուալ տրանսպորտային համակարգերի նախատիպի համար։

# Օգտագործված գրականություն

1. VisDrone Dataset. Official repository. https://github.com/VisDrone/VisDrone-Dataset
2. Zhu P., Wen L., Du D. et al. Detection and Tracking Meet Drones Challenge // IEEE Transactions on Pattern Analysis and Machine Intelligence. 2022. Vol. 44, No. 11. P. 7380–7399. https://arxiv.org/abs/2001.06303
3. Jocher G., Chaurasia A., Qiu J. Ultralytics YOLOv8. 2023. https://docs.ultralytics.com/models/yolov8/
4. Zhang Y., Sun P., Jiang Y. et al. ByteTrack: Multi-Object Tracking by Associating Every Detection Box // European Conference on Computer Vision (ECCV). 2022. https://arxiv.org/abs/2110.06864
5. Ultralytics. Multi-Object Tracking. https://docs.ultralytics.com/modes/track/
6. Roboflow Supervision. Video assets and speed estimation example. https://github.com/roboflow/supervision
7. Ultralytics. Model Training. https://docs.ultralytics.com/modes/train/
8. Ultralytics. VisDrone Dataset. https://docs.ultralytics.com/datasets/detect/visdrone/
9. Hartley R., Zisserman A. Multiple View Geometry in Computer Vision. 2nd ed. Cambridge University Press, 2004. 655 p.
10. Transportation Research Board. Highway Capacity Manual, 6th Edition: A Guide for Multimodal Mobility Analysis. Washington, DC, 2016.
11. Mannering F., Washburn S. Principles of Highway Engineering and Traffic Analysis. 7th ed. Wiley, 2019.
12. Luo Z., Branchaud-Charron F., Lemaire C. et al. MIO-TCD: A New Benchmark Dataset for Vehicle Classification and Localization // IEEE Transactions on Image Processing. 2018. Vol. 27, No. 10. P. 5129–5141.
13. Wen L., Du D., Cai Z. et al. UA-DETRAC: A New Benchmark and Protocol for Multi-Object Detection and Tracking // Computer Vision and Image Understanding. 2020. Vol. 193. 102907. https://arxiv.org/abs/1511.04136
14. Redmon J., Divvala S., Girshick R., Farhadi A. You Only Look Once: Unified, Real-Time Object Detection // IEEE Conference on Computer Vision and Pattern Recognition (CVPR). 2016. P. 779–788.
15. Ren S., He K., Girshick R., Sun J. Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks // Advances in Neural Information Processing Systems. 2015.
16. Lin T.-Y., Maire M., Belongie S. et al. Microsoft COCO: Common Objects in Context // European Conference on Computer Vision (ECCV). 2014. P. 740–755.
17. Lin T.-Y., Dollár P., Girshick R. et al. Feature Pyramid Networks for Object Detection // IEEE Conference on Computer Vision and Pattern Recognition (CVPR). 2017. P. 2117–2125.
18. Akyon F. C., Altinuc S. O., Temizel A. Slicing Aided Hyper Inference and Fine-Tuning for Small Object Detection // IEEE International Conference on Image Processing (ICIP). 2022. P. 966–970.
19. Bewley A., Ge Z., Ott L. et al. Simple Online and Realtime Tracking // IEEE International Conference on Image Processing (ICIP). 2016. P. 3464–3468.
20. Sochor J., Juránek R., Špaňhel J. et al. Comprehensive Data Set for Automatic Single Camera Visual Speed Measurement // IEEE Transactions on Intelligent Transportation Systems. 2019. Vol. 20, No. 5. P. 1633–1643.
21. Greenshields B. D. A Study of Traffic Capacity // Highway Research Board Proceedings. 1935. Vol. 14. P. 448–477.

# Հավելված Ա. Վերարտադրման հրամաններ

Բոլոր փորձերը վերարտադրվում են հետևյալ հրամաններով (մանրամասն պարամետրերը պահպանված են `runs/experiments/*/args.yaml` և `reports/vehicle-*.json` ֆայլերում)։

Տվյալների պատրաստում.

```
python scripts/download_data.py
python scripts/prepare_visdrone.py --pilot-size 1024
python scripts/expand_training.py
python scripts/prepare_miotcd.py
```

Ուսուցում (օրինակ՝ առաջարկվող մոդել).

```
python scripts/run_experiment.py --name vehicle-road-yolov8s \
  --data configs/combined-road.yaml --epochs 8 --imgsz 640 --batch 16 --device mps
python scripts/run_experiment.py --name vehicle-road-yolov8s-long \
  --weights runs/experiments/vehicle-road-yolov8s/weights/best.pt \
  --data configs/combined-road.yaml --epochs 12 --imgsz 640 --batch 16 \
  --optimizer AdamW --lr0 0.0005 --device mps
```

Գնահատում և հաշվետվություններ.

```
python scripts/evaluate_road_models.py --models vehicle-road-yolov8s-long
python scripts/evaluate_tiled.py
python scripts/download_detrac.py --sequence MVI_39031
python scripts/evaluate_detrac.py --sequence MVI_39031 --device mps \
  --models vehicle-road-yolov8s:960,vehicle-road-yolov8s-long:960
python scripts/thesis_video_results.py --weights \
  runs/experiments/vehicle-road-yolov8s-long/weights/best.pt --imgsz 960 --tag v8s-long
python scripts/evaluate_counting.py --results outputs/thesis-v1-v8s-long \
  --name thesis-v1-v8s-long --reference reports/video-reference.json --tolerance 6
python -m unittest discover -s tests -v
```

Այս փաստաթղթի կառուցում.

```
python scripts/thesis_figures_hy.py
python scripts/build_thesis_hy.py
```

# Հավելված Բ. Հաշվման կանոնի ելակետային կոդը

Ստորև բերված է `traffic_cnn/counting.py` մոդուլի հիմնական մեթոդը, որը որոշում է հետագծի կողմը հաշվման գծի նկատմամբ և գրանցում է հատումը (3.4 բաժին)։

```
def update(self, identity, point, frame, size=None):
    ax, ay = self.a
    dx, dy = self.b[0]-ax, self.b[1]-ay
    distance = (dx*(point[1]-ay)-dy*(point[0]-ax))/self.length
    side = 1 if distance > self.margin else -1 if distance < -self.margin else 0
    if (identity not in self.previous and identity not in self.started
            and identity not in self.counted and size
            and abs(distance) <= self.start_fraction*size and self._on_segment(point)):
        self.started[identity] = (frame, distance, point, size)
    if not side:
        return None
    if identity in self.started:
        direction = self._started_crossing(identity, distance, side, frame)
        if direction:
            self.previous[identity] = (point, distance, side, frame)
            return direction
    old = self.previous.get(identity)
    self.previous[identity] = (point, distance, side, frame)
    if (old is None or identity in self.counted or side == old[2]
            or frame-old[3] > self.max_gap):
        return None
    t = old[1]/(old[1]-distance)
    cross = tuple(old[0][i]+t*(point[i]-old[0][i]) for i in range(2))
    if not self._on_segment(cross):
        return None
    self.started.pop(identity, None)
    return self._count(identity,
        'negative_to_positive' if side == 1 else 'positive_to_negative')
```

Արագության գնահատիչի հիմնական մեթոդը (`traffic_cnn/calibration.py`, 3.6 բաժին).

```
def update(self, identity, point, frame, t=None):
    if not self.calibration.contains(point):
        return self.current(identity)
    t = frame / self.fps if t is None else t
    world = self.calibration.to_world(point)[0]
    track = self.points.setdefault(identity, deque())
    if track and t - track[-1][0] > self.window:
        track.clear()
    track.append((t, world))
    while track and t - track[0][0] > self.window:
        track.popleft()
    span = t - track[0][0]
    if span >= self.min_span:
        kmh = float(np.linalg.norm(world - track[0][1]) / span * 3.6)
        self.raw.append(kmh)
        if kmh <= self.max_kmh:
            self.accepted += 1
            self.estimates.setdefault(identity, deque(maxlen=self.history)).append(kmh)
            self.all_estimates.setdefault(identity, []).append(kmh)
        else:
            self.rejected += 1
    return self.current(identity)
```
