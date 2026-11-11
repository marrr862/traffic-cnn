// Builds the Armenian defense deck thesis/presentation/DEFENSE.pptx from the thesis results.
// Run: NODE_PATH=<folder with node_modules/pptxgenjs> node scripts/build_defense_hy.js [ui-crop.png]
// Numbers come from chapter 5 of thesis/hy (reports/*.json); keep them in sync when results change.
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..');
const R = (p) => path.join(ROOT, p);
const UI = process.argv[2] || R('reports/thesis/ui/e2e-results.png');
const OUT = R('thesis/presentation/DEFENSE.pptx');

// Asphalt and road-marking palette.
const COL = {
  asphalt: '22303A', asphalt2: '33444F', marking: 'F2B705', teal: '17807A',
  ink: '1E2A32', muted: '5B6770', light: 'EEF2F4', white: 'FFFFFF', red: 'C2412D',
};
const FONT = 'Sylfaen';  // ships with Windows and Office for Mac, covers Armenian

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';  // 13.33 x 7.5 in
pres.title = 'Երթևեկության հոսքի վերլուծություն տեսախցիկներով';
pres.author = 'Ղազարյան Մարիամ Սարգիսի';
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: 'CONTENT',
  background: { color: COL.white },
  objects: [
    { placeholder: { options: { name: 'title', type: 'title', x: 0.6, y: 0.35, w: 12.1, h: 0.9,
      fontFace: FONT, fontSize: 32, bold: true, color: COL.ink, valign: 'middle', align: 'left', margin: 0 }, text: '' } },
  ],
  slideNumber: { x: 12.35, y: 6.95, w: 0.6, h: 0.35, fontFace: FONT, fontSize: 11, color: COL.muted, align: 'right' },
});
pres.defineSlideMaster({ title: 'DARK', background: { color: COL.asphalt },
  slideNumber: { x: 12.35, y: 6.95, w: 0.6, h: 0.35, fontFace: FONT, fontSize: 11, color: 'A9B4BB', align: 'right' } });

const text = (slide, value, opts) => slide.addText(value, { fontFace: FONT, isTextBox: true, margin: 0, color: COL.ink, ...opts });
const content = (title) => { const s = pres.addSlide({ masterName: 'CONTENT' }); s.addText(title, { placeholder: 'title' }); return s; };

function card(slide, x, y, w, h, fill = COL.light) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12 });
}
function badge(slide, x, y, label, fill = COL.marking, color = COL.asphalt) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.6, h: 0.6, fill: { color: fill }, line: { color: fill } });
  text(slide, label, { x, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color, align: 'center', valign: 'middle' });
}
function stat(slide, x, y, w, value, label, valueColor = COL.teal) {
  text(slide, value, { x, y, w, h: 0.9, fontSize: 40, bold: true, color: valueColor });
  text(slide, label, { x, y: y + 0.9, w, h: 0.75, fontSize: 15, color: COL.muted, valign: 'top' });
}

// 1. Title
{
  const s = pres.addSlide({ masterName: 'DARK' });
  s.addImage({ path: R('reports/thesis/annotated-v1.jpg'), x: 7.0, y: 0, w: 6.33, h: 7.5,
    sizing: { type: 'cover', w: 6.33, h: 7.5 } });
  text(s, 'ԱՎԱՐՏԱԿԱՆ ԱՇԽԱՏԱՆՔ', { x: 0.7, y: 0.8, w: 5.9, h: 0.4, fontSize: 14, bold: true, color: COL.marking, charSpacing: 2 });
  text(s, 'Տեսախցիկների միջոցով տրանսպորտային միջոցների շարժման և երթևեկության հոսքի վերլուծության ծրագրային միջոցի մշակում',
    { x: 0.7, y: 1.4, w: 5.9, h: 2.9, fontSize: 28, bold: true, color: COL.white, valign: 'top' });
  text(s, [
    { text: 'Ուսանող՝ Ղազարյան Մարիամ Սարգիսի', options: { breakLine: true } },
    { text: 'Գիտական ղեկավար՝ ______________________', options: { breakLine: true } },
    { text: 'Երևան 2026' },
  ], { x: 0.7, y: 4.9, w: 5.9, h: 1.4, fontSize: 16, color: 'D5DCE0', paraSpaceAfter: 6, valign: 'top' });
  s.addNotes('Բարև ձեզ։ Ներկայացնում եմ ավարտական աշխատանքս՝ ծրագրային միջոց, որը սովորական տեսախցիկի տեսանյութից հայտնաբերում է մեքենաները, հաշվում է դրանք և չափում երթևեկության հոսքի հիմնական բնութագրերը։ Նկարում՝ ծրագրի իրական արդյունքը մայրուղու տեսանյութում։');
}

// 2. Problem and goal
{
  const s = content('Խնդիրը և նպատակը');
  text(s, [
    { text: 'Երթևեկության չափումը անհրաժեշտ է ճանապարհների պլանավորման և կառավարման համար։', options: { breakLine: true } },
    { text: 'Ձեռքով հաշվարկը թանկ է, իսկ ռադարներն ու ինդուկտիվ օղակները չափում են միայն մեկ կետում։', options: { breakLine: true } },
    { text: 'Տեսախցիկներն արդեն տեղադրված են, և դրանցից կարելի է ստանալ ավելի շատ տեղեկություն։' },
  ], { x: 0.6, y: 1.6, w: 5.2, h: 3.6, fontSize: 18, paraSpaceAfter: 14, valign: 'top' });
  card(s, 0.6, 5.45, 5.2, 1.25, 'FFF6D6');
  text(s, 'Նպատակ՝ տեսանյութից ավտոմատ ստանալ մեքենաների քանակը, արագությունը, խտությունը և սպասարկման մակարդակը',
    { x: 0.85, y: 5.55, w: 4.75, h: 1.05, fontSize: 16, bold: true, valign: 'middle' });
  const steps = [
    ['1', 'Մուտք', 'Տեսանյութի ֆայլ կամ ուղիղ հոսք (RTSP, HLS, YouTube)'],
    ['2', 'Մշակում', 'CNN հայտնաբերում (YOLOv8), հետագծում (ByteTrack), գծի հատման հաշվարկ'],
    ['3', 'Արդյունք', 'Ինտենսիվություն, արագություն, խտություն, LOS, CSV/JSON հաշվետվություն'],
  ];
  steps.forEach(([n, head, body], i) => {
    const y = 1.6 + i * 1.75;
    card(s, 6.4, y, 6.3, 1.5);
    badge(s, 6.65, y + 0.45, n);
    text(s, head, { x: 7.5, y: y + 0.18, w: 5.0, h: 0.45, fontSize: 19, bold: true });
    text(s, body, { x: 7.5, y: y + 0.65, w: 5.0, h: 0.7, fontSize: 15, color: COL.muted, valign: 'top' });
  });
  s.addNotes('Երթևեկության մասին տվյալները անհրաժեշտ են ճանապարհների պլանավորման համար, բայց դասական սարքերը չափում են միայն մեկ կետում, իսկ ձեռքով հաշվարկը թանկ է։ Տեսախցիկներն արդեն կան շատ ճանապարհներին։ Աշխատանքի նպատակն է տեսանյութից ավտոմատ ստանալ մեքենաների քանակը, արագությունը, խտությունը և սպասարկման մակարդակը։ Ծրագիրը ընդունում է ֆայլ կամ ուղիղ հոսք և տալիս է պատրաստի հաշվետվություն։');
}

// 3. Pipeline
{
  const s = content('Համակարգի կառուցվածքը');
  s.addImage({ path: R('reports/thesis/pipeline-hy.png'), x: 0.6, y: 1.55, w: 12.1, h: 12.1 * 748 / 2055 });
  const notes = [
    ['Հայտնաբերում', 'YOLOv8 CNN, 5 դաս՝ car, van, truck, bus, motorcycle'],
    ['Հետագծում և հաշվարկ', 'ByteTrack, գծի հատում հիստերեզիսով, կրկնակի ID-ների զտիչ'],
    ['Չափում', 'Հոմոգրաֆիա 4 կետով՝ պիքսելներից մետրեր, կմ/ժ, մեքենա/կմ'],
  ];
  notes.forEach(([head, body], i) => {
    const x = 0.6 + i * 4.1;
    text(s, head, { x, y: 6.05, w: 3.8, h: 0.4, fontSize: 16, bold: true, color: COL.teal });
    text(s, body, { x, y: 6.45, w: 3.8, h: 0.6, fontSize: 13, color: COL.muted, valign: 'top' });
  });
  s.addNotes('Ծրագրի շղթան հետևյալն է։ Յուրաքանչյուր կադրում YOLOv8 փաթույթային ցանցը հայտնաբերում է մեքենաները և դրանց դասը։ ByteTrack-ը կապում է հայտնաբերումները ժամանակի մեջ, և յուրաքանչյուր մեքենա ստանում է իր ID-ն։ Երբ մեքենան հատում է հաշվման գիծը, գրանցվում է իրադարձություն։ Տրամաչափման դեպքում 4 կետով հոմոգրաֆիան պիքսելները վերածում է մետրերի, և ծրագիրը հաշվում է արագությունը, խտությունը և սպասարկման մակարդակը։');
}

// 4. Data
{
  const s = content('Ուսուցման տվյալները');
  const stats = [
    ['7 493', 'VisDrone պատկեր ուսուցման համար (անօդաչու սարք, վերևից)'],
    ['30 000', 'MIO-TCD պատկեր (անշարժ ճանապարհային տեսախցիկներ)'],
    ['5', 'դաս՝ car, van, truck, bus, motorcycle'],
  ];
  stats.forEach(([v, l], i) => { card(s, 0.6 + i * 4.1, 1.6, 3.8, 2.0); stat(s, 0.9 + i * 4.1, 1.8, 3.3, v, l); });
  text(s, 'Երկու տիրույթ', { x: 0.6, y: 4.0, w: 6, h: 0.45, fontSize: 20, bold: true });
  text(s, [
    { text: 'VisDrone-ում մեքենաները փոքր են և նկարված վերևից, իսկ իրական ճանապարհային տեսախցիկները նկարում են թեք անկյան տակ։', options: { bullet: true, breakLine: true } },
    { text: 'Ուստի ավելացվել է MIO-TCD-ն՝ դասերը համապատասխանեցված են 5 թիրախային դասերին, իսկ անորոշ շրջանակները դիմակավորված են։', options: { bullet: true, breakLine: true } },
    { text: 'Արտաքին ստուգման համար օգտագործվել է UA-DETRAC հավաքածուն, որը ուսուցման մեջ չի մասնակցել։', options: { bullet: true } },
  ], { x: 0.6, y: 4.55, w: 12.1, h: 2.2, fontSize: 16, paraSpaceAfter: 8, valign: 'top' });
  s.addNotes('Դետեկտորը ուսուցանվել է երկու բաց հավաքածուներով։ VisDrone-ը անօդաչու սարքից արված պատկերներ են, որտեղ մեքենաները շատ փոքր են։ Իրական ճանապարհային տեսախցիկները նկարում են այլ անկյունից, ուստի ավելացվել է MIO-TCD-ի 30 հազար պատկեր։ Դրա դասերը համապատասխանեցվել են մեր հինգ դասերին, իսկ անորոշ դասի շրջանակները դիմակավորվել են։ Արտաքին ստուգման համար օգտագործվել է UA-DETRAC հավաքածուն, որը ուսուցման մեջ չի օգտագործվել։');
}

// 5. Experiments: what improves the model
{
  const s = content('Ի՞նչն է բարելավում մոդելը՝ 10 փորձ');
  const items = [
    ['Ուսուցման փոխանցում', '2,6% → 13,8%', 'COCO կշիռներ՝ զրոյից ուսուցման փոխարեն (VisDrone, 1024 պատկեր)'],
    ['Մուտքի չափ 960 պքս', '34,7% → 45,9%', 'Փոքր մեքենաները պահպանում են մանրամասները (VisDrone թեստ)'],
    ['Ճանապարհային տվյալներ', '15,1% → 83,7%', 'MIO-TCD թեստ՝ տիրույթի տեղաշարժը վերացված է'],
    ['YOLOv8s + 12 դարաշրջան', '43,0% → 51,4%', 'Ավելի մեծ մոդել և երկարացված ուսուցում (VisDrone, 960)'],
  ];
  items.forEach(([head, value, body], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.35;
    card(s, x, y, 5.95, 2.1);
    text(s, head, { x: x + 0.3, y: y + 0.2, w: 5.4, h: 0.45, fontSize: 18, bold: true });
    text(s, value, { x: x + 0.3, y: y + 0.65, w: 5.4, h: 0.75, fontSize: 34, bold: true, color: COL.teal });
    text(s, body, { x: x + 0.3, y: y + 1.4, w: 5.4, h: 0.55, fontSize: 14, color: COL.muted, valign: 'top' });
  });
  text(s, 'mAP50 թեստային ընտրանքում։ Պարզ ընդլայնումը (augmentation) էական օգուտ չի տվել՝ ±0,1 կետ։',
    { x: 0.6, y: 6.35, w: 11.5, h: 0.45, fontSize: 14, color: COL.muted, italic: true });
  s.addNotes('Կատարվել է տասը ուսուցման փորձ, և յուրաքանչյուրը փոխում էր մեկ գործոն։ Ամենակարևոր եզրակացությունները չորսն են։ Առաջին՝ զրոյից ուսուցանված մոդելը գրեթե չի սովորում, իսկ COCO կշիռներից սկսելը տալիս է հինգ անգամ լավ արդյունք։ Երկրորդ՝ 960 պիքսել մուտքը փոքր մեքենաների համար ավելացնում է 11 կետ։ Երրորդ՝ ճանապարհային տվյալների ավելացումը MIO-TCD-ում 15-ից հասցնում է 84 տոկոսի։ Չորրորդ՝ ավելի մեծ YOLOv8s մոդելը և ուսուցման երկարացումը ևս 12 դարաշրջանով տվել են վերջնական բարելավումը։ Պարզ ընդլայնումը օգուտ չի տվել։');
}

// 6. Model comparison chart
{
  const s = content('Մոդելների համեմատությունը');
  const labels = ['VisDrone թեստ, 960 պքս', 'MIO-TCD թեստ, 640 պքս'];
  const data = [
    { name: 'hires-960 (YOLOv8n, VisDrone)', labels, values: [45.9, 15.1] },
    { name: 'road-combined (YOLOv8n)', labels, values: [43.0, 83.7] },
    { name: 'road-yolov8s (YOLOv8s)', labels, values: [48.0, 86.8] },
    { name: 'road-yolov8s-long (առաջարկվող)', labels, values: [51.4, 90.2] },
  ];
  s.addChart(pres.charts.BAR, data, {
    x: 0.6, y: 1.45, w: 8.2, h: 5.4, barDir: 'col', barGapWidthPct: 60,
    chartColors: ['C9D3D9', '8FA3AE', '4F7F8C', COL.teal],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 11, dataLabelFontFace: FONT, dataLabelColor: COL.ink,
    dataLabelFormatCode: '0.0',
    catAxisLabelFontFace: FONT, catAxisLabelFontSize: 13, catAxisLabelColor: COL.ink,
    valAxisLabelFontFace: FONT, valAxisLabelFontSize: 11, valAxisLabelColor: COL.muted, valAxisMaxVal: 100, valAxisMinVal: 0,
    valAxisTitle: 'mAP50, %', showValAxisTitle: true, valAxisTitleFontFace: FONT, valAxisTitleFontSize: 12, valAxisTitleColor: COL.muted,
    valGridLine: { color: 'E1E6E9', size: 0.5 }, catGridLine: { style: 'none' },
    showLegend: true, legendPos: 'b', legendFontFace: FONT, legendFontSize: 11, legendColor: COL.ink,
  });
  card(s, 9.2, 1.6, 3.5, 5.1, COL.asphalt);
  text(s, 'Առաջարկվող մոդել', { x: 9.45, y: 1.8, w: 3.0, h: 0.4, fontSize: 15, bold: true, color: COL.marking });
  text(s, 'vehicle-road-yolov8s-long', { x: 9.45, y: 2.2, w: 3.0, h: 0.4, fontSize: 14, color: 'D5DCE0' });
  [['51,4%', 'VisDrone mAP50'], ['90,2%', 'MIO-TCD mAP50'], ['+3–5', 'կետ՝ երկարացված ուսուցումից']].forEach(([v, l], i) => {
    text(s, v, { x: 9.45, y: 2.85 + i * 1.25, w: 3.0, h: 0.65, fontSize: 32, bold: true, color: COL.white });
    text(s, l, { x: 9.45, y: 3.5 + i * 1.25, w: 3.0, h: 0.4, fontSize: 13, color: 'D5DCE0' });
  });
  s.addNotes('Գրաֆիկում վերջին չորս մոդելներն են երկու տիրույթներում։ Միայն VisDrone-ով ուսուցանված մոդելը ճանապարհային տեսախցիկներում ունի ընդամենը 15 տոկոս, սա տիրույթի տեղաշարժն է։ Ճանապարհային տվյալների ավելացումը լուծում է այս խնդիրը, իսկ ավելի մեծ YOLOv8s մոդելը բարելավում է երկու տիրույթներն էլ։ Առաջարկվող մոդելը՝ երկարացված ուսուցմամբ, լավագույնն է երկու տիրույթներում՝ 51,4 և 90,2 տոկոս։ Արագությամբ այն չի տարբերվում նախորդից, քանի որ ճարտարապետությունը նույնն է։');
}

// 7. Counting on the highway video
{
  const s = content('Հաշվարկ. ընդհանուր թիվը թաքցնում է սխալները');
  const head = (t) => ({ text: t, options: { bold: true, fontSize: 13, color: COL.white, fill: { color: COL.asphalt } } });
  const rows = [
    [head('Մոդել, կարգավորում'), head('Հաշվված'), head('Ճիշտ'), head('Ավելորդ')],
    ['scratch-pilot, սկզբնական', '11', '10', '1'],
    ['finetune-full, սկզբնական', '10', '9', '1'],
    ['road-yolov8s, class-agnostic NMS', '9', '9', '0'],
    [{ text: 'road-yolov8s-long, վերջնական', options: { bold: true } }, { text: '10', options: { bold: true } },
      { text: '10', options: { bold: true } }, { text: '0', options: { bold: true } }],
  ];
  s.addTable(rows, { x: 0.6, y: 1.55, w: 6.3, colW: [2.85, 1.15, 1.15, 1.15], fontFace: FONT, fontSize: 14, color: COL.ink,
    border: { type: 'solid', color: 'D5DCE0', pt: 0.75 }, rowH: 0.5, valign: 'middle', align: 'left' });
  text(s, [
    { text: 'Էտալոն՝ 10 հատում (8 car, 2 truck), 4K, 21,5 վ', options: { bullet: true, breakLine: true } },
    { text: '10 = 10 կարող է նշանակել 1 բաց թողնված + 1 կրկնակի', options: { bullet: true, breakLine: true } },
    { text: 'Լուծումներ՝ հիստերեզիս, class-agnostic NMS, կրկնակի ID-ների զտիչ, գծից արդեն անցած մեքենաներ', options: { bullet: true } },
  ], { x: 0.6, y: 4.65, w: 6.3, h: 2.2, fontSize: 15, paraSpaceAfter: 8, valign: 'top' });
  s.addImage({ path: R('reports/thesis/annotated-v1.jpg'), x: 7.3, y: 1.55, w: 5.4, h: 5.4 * 1080 / 1920 });
  text(s, 'Վերջնական տարբերակ՝ 10/10, F1 = 100%, 8 թեթև և 2 ծանր։ Եվրոպական բեռնատարները նշվել են որպես bus (թեստում truck/bus շփոթումը մոտ 2% է)։',
    { x: 7.3, y: 4.75, w: 5.4, h: 1.0, fontSize: 13, color: COL.muted, valign: 'top' });
  s.addNotes('Հաշվարկը ստուգվել է իրադարձությունների մակարդակում։ Աղյուսակը ցույց է տալիս, որ ընդհանուր թիվը կարող է խաբել։ Օրինակ, մոդելը հաշվել է 10 մեքենա, բայց միայն 9-ն էին իրական. մեկը բաց է թողնվել, իսկ մեկը հաշվվել է կրկնակի։ Դրա համար մշակվել են մի քանի կանոններ՝ հիստերեզիս գծի մոտ, առանց դասերի տարբերակման NMS, կրկնակի ID-ների զտիչ և գծից արդեն անցած մեքենաների կանոն։ Վերջնական տարբերակը ճիշտ հաշվել է բոլոր 10 մեքենաները։ Եվրոպական բեռնատարները մոդելը նշել է որպես ավտոբուս, բայց թեստային ընտրանքում այդ շփոթումը մոտ 2 տոկոս է, իսկ ծանր տրանսպորտի քանակը ճիշտ է։ Նշեմ, որ այս տեսանյութն օգտագործվել է նաև կանոնների մշակման համար։');
}

// 8. External UA-DETRAC check
{
  const s = content('Արտաքին ստուգում UA-DETRAC հավաքածուով');
  s.addImage({ path: R('reports/detrac-check-preview.jpg'), x: 0.6, y: 1.55, w: 6.6, h: 6.6 * 540 / 960 });
  text(s, 'MVI_39031, 300 կադր, 523 շրջանակ, ուսուցման մեջ չի օգտագործվել', { x: 0.6, y: 5.35, w: 6.6, h: 0.4, fontSize: 13, color: COL.muted });
  [['99,0%', 'հայտնաբերված մեքենաներ (recall)'], ['97,0%', 'AP50 (մեքենա՝ առանց դասերի)'], ['5 / 5', 'ճիշտ հատում, 0 ավելորդ']]
    .forEach(([v, l], i) => { card(s, 7.6, 1.55 + i * 1.45, 5.1, 1.25); stat(s, 7.85, 1.6 + i * 1.45, 4.6, v, l); });
  text(s, 'Սահմանափակում՝ 12 վայրկյան, մեկ տեսախցիկ, ցերեկ', { x: 7.6, y: 6.05, w: 5.1, h: 0.4, fontSize: 14, italic: true, color: COL.muted });
  s.addNotes('Որպեսզի ստուգումը անկախ լինի, մոդելը գնահատվել է UA-DETRAC հավաքածուի տեսանյութում, որը ուսուցման կամ պարամետրերի ընտրության մեջ չի օգտագործվել, իսկ հաշվման գիծը ֆիքսվել է նախապես։ Մոդելը հայտնաբերել է մեքենաների 99 տոկոսը և ճիշտ հաշվել բոլոր 5 հատումները։ Սակայն ստուգման ծավալը փոքր է՝ 12 վայրկյան և մեկ տեսախցիկ, ուստի դա ընդհանուր ճշտության գնահատական չէ։');
}

// 9. Speed, density, LOS
{
  const s = content('Արագություն, խտություն և LOS');
  s.addImage({ path: R('reports/thesis/calibration-zones.jpg'), x: 0.6, y: 1.45, w: 12.1, h: 12.1 * 540 / 1920 });
  const stats = [['1673', 'մեքենա/ժամ ինտենսիվություն'], ['112,8', 'կմ/ժ տարածական միջին արագություն'],
    ['2,8', 'մեքենա/կմ/գոտի, LOS A'], ['2,8%', 'երկու անկախ եղանակների տարբերություն']];
  stats.forEach(([v, l], i) => stat(s, 0.6 + i * 3.1, 5.05, 2.9, v, l));
  s.addNotes('Տրամաչափման համար օգտագործողը կադրի վրա նշում է 4 կետ և ճանապարհի իրական չափերը։ Դրանից հետո ծրագիրը հաշվում է արագությունը, խտությունը և սպասարկման մակարդակը ըստ HCM-ի։ Մայրուղու տեսանյութում ինտենսիվությունը 1673 մեքենա ժամում է, միջին արագությունը՝ մոտ 113 կմ/ժ, սպասարկման մակարդակը՝ A։ Արագությունը ստուգվել է երկրորդ, անկախ եղանակով՝ երկու գծերի միջև անցման ժամանակով, և միջին տարբերությունը 2,8 տոկոս է։');
}

// 10. Time-lapse detection
{
  const s = content('Ֆիզիկական հավաստիության ստուգում');
  s.addImage({ path: R('reports/thesis/annotated-v2.jpg'), x: 0.6, y: 1.55, w: 6.6, h: 6.6 * 1080 / 1920 });
  text(s, 'Տեսանյութ 2՝ քաղաքային ճանապարհ, 42,5 վ', { x: 0.6, y: 5.35, w: 6.6, h: 0.4, fontSize: 13, color: COL.muted });
  [['449', 'հատում 42 վայրկյանում'], ['37 995', 'մեքենա/ժամ՝ 5 անգամ ավելի, քան թողունակությունը'], ['709', 'կմ/ժ չափումների մեդիան']]
    .forEach(([v, l], i) => stat(s, 7.6, 1.5 + i * 1.45, 5.1, v, l, COL.red));
  card(s, 7.6, 5.85, 5.1, 0.95, 'FFF6D6');
  text(s, 'Ծրագիրը ավտոմատ նախազգուշացնում է՝ տեսանյութը արագացված է', { x: 7.8, y: 5.9, w: 4.7, h: 0.85, fontSize: 15, bold: true, valign: 'middle' });
  s.addNotes('Երկրորդ տեսանյութում ծրագիրը գրանցել է 449 հատում, ինչը համապատասխանում է գրեթե 38 հազար մեքենա ժամում ինտենսիվության, իսկ արագությունների մեդիանը 709 կմ/ժ է։ Դա ֆիզիկապես անհնար է։ Ծրագիրը ստուգում է արագությունները, գոտու թողունակությունը և q = k·v հավասարումը, և ինքնաբերաբար ցույց է տալիս, որ տեսանյութը, ամենայն հավանականությամբ, արագացված է։ Առանց այս ստուգման օգտագործողը կստանար տեխնիկապես ճիշտ, բայց անիմաստ թվեր։');
}

// 11. The application
{
  const s = content('Ծրագրային միջոցը');
  s.addImage({ path: UI, x: 0.6, y: 1.45, w: 5.3 * 1280 / 1150, h: 5.3 });
  text(s, [
    { text: 'Հայերեն միջերես (Streamlit) և հրամանային տող', options: { bullet: true, breakLine: true } },
    { text: 'Ֆայլ կամ ուղիղ հոսք՝ RTSP, HLS, YouTube', options: { bullet: true, breakLine: true } },
    { text: 'Հաշվման գծեր և տրամաչափում կադրի վրա', options: { bullet: true, breakLine: true } },
    { text: 'Սալիկային ռեժիմ փոքր մեքենաների համար (VisDrone 52,2%)', options: { bullet: true, breakLine: true } },
    { text: 'CSV/JSON արտահանում, ջերմային քարտեզ, հետագծեր', options: { bullet: true, breakLine: true } },
    { text: 'Հաշվարկի ստուգման գործիք էտալոնային նշագրմամբ', options: { bullet: true, breakLine: true } },
    { text: '73 ավտոմատ թեստ', options: { bullet: true } },
  ], { x: 7.0, y: 1.6, w: 5.7, h: 5.0, fontSize: 17, paraSpaceAfter: 10, valign: 'top' });
  s.addNotes('Ծրագիրն ունի հայերեն միջերես և հրամանային տող։ Օգտագործողը ընտրում է տեսանյութ կամ ուղիղ հոսքի հասցե, մկնիկով նշում է հաշվման գիծը և տրամաչափման կետերը, ընտրում է մոդելը և սկսում մշակումը։ Ընթացքում ցույց է տրվում ընթացիկ կադրը, իսկ վերջում՝ արդյունքները, գրաֆիկները և ներբեռնվող ֆայլերը։ Վերևից նկարահանված տեսանյութերի համար կա սալիկային ռեժիմ։ Ծրագիրը ծածկված է 73 ավտոմատ թեստով։');
}

// 12. Conclusions
{
  const s = pres.addSlide({ masterName: 'DARK' });
  text(s, 'Եզրակացություններ', { x: 0.7, y: 0.5, w: 12, h: 0.9, fontSize: 34, bold: true, color: COL.white, valign: 'middle' });
  const results = [
    'Մշակվել է ծրագրային միջոց՝ հայտնաբերումից մինչև ինտենսիվություն, արագություն, խտություն և LOS',
    '10 փորձ. առաջարկվող YOLOv8s մոդելը՝ 51,4% VisDrone և 90,2% MIO-TCD mAP50',
    'Անկախ UA-DETRAC տեսանյութում՝ 99% հայտնաբերում և 5/5 ճիշտ հատում',
    'Ֆիզիկական հավաստիության ստուգումը հայտնաբերում է արագացված տեսանյութը',
  ];
  results.forEach((r, i) => {
    badge(s, 0.7, 1.75 + i * 1.05, String(i + 1));
    text(s, r, { x: 1.55, y: 1.7 + i * 1.05, w: 6.6, h: 0.75, fontSize: 17, color: COL.white, valign: 'middle' });
  });
  card(s, 8.6, 1.7, 4.1, 4.15, COL.asphalt2);
  text(s, 'Զարգացման ուղղություններ', { x: 8.85, y: 1.9, w: 3.6, h: 0.8, valign: 'top', fontSize: 17, bold: true, color: COL.marking });
  text(s, [
    { text: 'Գիշերային և վատ եղանակի տեսանյութեր', options: { bullet: true, breakLine: true } },
    { text: 'Հաշվարկ ըստ գոտիների և շրջադարձերի', options: { bullet: true, breakLine: true } },
    { text: 'van/car տարբերակում, եվրոպական բեռնատարներ', options: { bullet: true, breakLine: true } },
    { text: 'Արագության ստուգում ռադարով', options: { bullet: true } },
  ], { x: 8.85, y: 2.8, w: 3.6, h: 2.9, fontSize: 15, color: 'D5DCE0', paraSpaceAfter: 8, valign: 'top' });
  text(s, 'Շնորհակալություն ուշադրության համար', { x: 0.7, y: 6.25, w: 12, h: 0.6, fontSize: 22, bold: true, color: COL.marking });
  s.addNotes('Ամփոփեմ։ Մշակվել է ամբողջական ծրագրային միջոց՝ մեքենաների հայտնաբերումից մինչև երթևեկության հոսքի բնութագրերը։ Տասը փորձերի արդյունքում առաջարկվող մոդելը լավագույնն է երկու տիրույթներում։ Անկախ տեսանյութում այն հայտնաբերել է մեքենաների 99 տոկոսը և ճիշտ հաշվել բոլոր հատումները, իսկ հավաստիության ստուգումը հայտնաբերում է անհավանական արդյունքները։ Հետագա աշխատանքի ուղղություններն են գիշերային պայմանները, հաշվարկը ըստ գոտիների, van և car դասերի տարբերակումը և արագության ստուգումը ռադարով։ Շնորհակալություն։');
}

pres.writeFile({ fileName: OUT }).then(() => console.log('Saved', OUT));
