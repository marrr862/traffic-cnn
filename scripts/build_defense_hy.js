// Builds the Armenian defense deck thesis/presentation/DEFENSE.pptx (16 slides, one per section of
// thesis/DEFENSE_SPEECH_hy.md; each slide's speaker notes are that section of the speech).
// Run: NODE_PATH=<folder with node_modules/pptxgenjs> node scripts/build_defense_hy.js [ui-crop.png]
// Numbers come from chapter 5 of thesis/hy (reports/*.json); keep them in sync when results change.
const fs = require('fs');
const path = require('path');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '..');
const R = (p) => path.join(ROOT, p);
const UI = process.argv[2] || R('reports/thesis/ui/e2e-results.png');
const OUT = R('thesis/presentation/DEFENSE.pptx');

// Speaker notes: section "## N. Title" of the speech becomes the notes of slide N.
const SPEECH = {};
fs.readFileSync(R('thesis/DEFENSE_SPEECH_hy.md'), 'utf8').split(/^## /m).slice(1).forEach((part) => {
  const match = part.match(/^(\d+)\.[^\n]*\n([\s\S]*)$/);
  if (match) SPEECH[Number(match[1])] = match[2].replace(/\n---[\s\S]*$/, '').trim().replace(/\n{2,}/g, '\n\n');
});
const notes = (slide, n, override) => slide.addNotes(override || SPEECH[n] || '');

// Asphalt and road-marking palette.
const COL = {
  asphalt: '22303A', asphalt2: '33444F', marking: 'F2B705', teal: '17807A',
  ink: '1E2A32', muted: '5B6770', light: 'EEF2F4', white: 'FFFFFF', red: 'C2412D', sand: 'FFF6D6',
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
const bullets = (items) => items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } }));

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
const head = (t) => ({ text: t, options: { bold: true, fontSize: 13, color: COL.white, fill: { color: COL.asphalt } } });
const strong = (t) => ({ text: t, options: { bold: true } });
function table(slide, rows, x, y, w, colW, fontSize = 14) {
  slide.addTable(rows, { x, y, w, colW, fontFace: FONT, fontSize, color: COL.ink,
    border: { type: 'solid', color: 'D5DCE0', pt: 0.75 }, rowH: 0.45, valign: 'middle', align: 'left' });
}

// 1. Title
{
  const s = pres.addSlide({ masterName: 'DARK' });
  s.addImage({ path: R('reports/thesis/annotated-v1.jpg'), x: 7.0, y: 0, w: 6.33, h: 7.5,
    sizing: { type: 'cover', w: 6.33, h: 7.5 } });
  text(s, 'ԱՎԱՐՏԱԿԱՆ ԱՇԽԱՏԱՆՔ', { x: 0.7, y: 0.8, w: 5.9, h: 0.4, fontSize: 14, bold: true, color: COL.marking, charSpacing: 2 });
  text(s, 'Երթևեկության հոսքի վերլուծության ծրագրային միջոցի մշակում՝ փաթույթային նեյրոնային ցանցերի կիրառմամբ',
    { x: 0.7, y: 1.4, w: 5.9, h: 2.9, fontSize: 28, bold: true, color: COL.white, valign: 'top' });
  text(s, [
    { text: 'Ուսանող՝ Ղազարյան Մարիամ Սարգիսի', options: { breakLine: true } },
    { text: 'Գիտական ղեկավար՝ Խաչատրյան Տիգրան Բագրատի, տ.գ.թ., ավագ դասախոս', options: { breakLine: true } },
    { text: 'Հայաստանի ազգային պոլիտեխնիկական համալսարան', options: { breakLine: true } },
    { text: 'Երևան 2026' },
  ], { x: 0.7, y: 4.5, w: 5.9, h: 2.4, fontSize: 15, color: 'D5DCE0', paraSpaceAfter: 6, valign: 'top' });
  notes(s, 1);
}

// 2. Problem and goal
{
  const s = content('Խնդիրը և նպատակը');
  text(s, [
    { text: 'Երթևեկության չափումը անհրաժեշտ է ճանապարհների պլանավորման և կառավարման համար։', options: { breakLine: true } },
    { text: 'Ձեռքով հաշվարկը թանկ է, իսկ ռադարներն ու ինդուկտիվ օղակները չափում են միայն մեկ կետում։', options: { breakLine: true } },
    { text: 'Տեսախցիկներն արդեն տեղադրված են, և դրանցից կարելի է ստանալ ավելի շատ տեղեկություն։' },
  ], { x: 0.6, y: 1.6, w: 5.2, h: 3.6, fontSize: 18, paraSpaceAfter: 14, valign: 'top' });
  card(s, 0.6, 5.45, 5.2, 1.25, COL.sand);
  text(s, 'Նպատակ՝ տեսանյութից ավտոմատ ստանալ մեքենաների քանակը, արագությունը, խտությունը և սպասարկման մակարդակը',
    { x: 0.85, y: 5.55, w: 4.75, h: 1.05, fontSize: 16, bold: true, valign: 'middle' });
  [
    ['1', 'Մուտք', 'Տեսանյութի ֆայլ կամ ուղիղ հոսք (RTSP, HLS, YouTube)'],
    ['2', 'Մշակում', 'CNN հայտնաբերում (YOLOv8), հետագծում (ByteTrack), գծի հատման հաշվարկ'],
    ['3', 'Արդյունք', 'Ինտենսիվություն, արագություն, խտություն, LOS, CSV/JSON հաշվետվություն'],
  ].forEach(([n, title, body], i) => {
    const y = 1.6 + i * 1.75;
    card(s, 6.4, y, 6.3, 1.5);
    badge(s, 6.65, y + 0.45, n);
    text(s, title, { x: 7.5, y: y + 0.18, w: 5.0, h: 0.45, fontSize: 19, bold: true });
    text(s, body, { x: 7.5, y: y + 0.65, w: 5.0, h: 0.7, fontSize: 15, color: COL.muted, valign: 'top' });
  });
  notes(s, 2);
}

// 3. Pipeline
{
  const s = content('Համակարգի կառուցվածքը');
  s.addImage({ path: R('reports/thesis/pipeline-hy.png'), x: 0.6, y: 1.55, w: 12.1, h: 12.1 * 748 / 2055 });
  [
    ['Հայտնաբերում', 'YOLOv8 CNN, 5 դաս՝ car, van, truck, bus, motorcycle'],
    ['Հետագծում և հաշվարկ', 'ByteTrack (կամ 5 այլ ալգորիթմ), գծի հատում, դաս՝ ամբողջ հետագծով'],
    ['Չափում', 'Հոմոգրաֆիա 4 կետով՝ պիքսելներից մետրեր, կմ/ժ, մեքենա/կմ'],
  ].forEach(([title, body], i) => {
    const x = 0.6 + i * 4.1;
    text(s, title, { x, y: 6.05, w: 3.8, h: 0.4, fontSize: 16, bold: true, color: COL.teal });
    text(s, body, { x, y: 6.45, w: 3.8, h: 0.6, fontSize: 13, color: COL.muted, valign: 'top' });
  });
  notes(s, 3);
}

// 4. Data
{
  const s = content('Տվյալներ');
  [
    ['7 493', 'VisDrone պատկեր ուսուցման համար (անօդաչու սարք, վերևից)'],
    ['30 000', 'MIO-TCD պատկեր (անշարժ ճանապարհային տեսախցիկներ)'],
    ['40', 'UA-DETRAC տեսանյութ՝ միայն անկախ ստուգման համար'],
  ].forEach(([v, l], i) => { card(s, 0.6 + i * 4.1, 1.6, 3.8, 2.0); stat(s, 0.9 + i * 4.1, 1.8, 3.3, v, l); });
  text(s, 'Երեք տիրույթ', { x: 0.6, y: 4.0, w: 6, h: 0.45, fontSize: 20, bold: true });
  text(s, bullets([
    'VisDrone-ում մեքենաները փոքր են և նկարված վերևից, իսկ իրական ճանապարհային տեսախցիկները նկարում են թեք անկյան տակ։',
    'MIO-TCD-ի դասերը համապատասխանեցված են 5 թիրախային դասերին (car, van, truck, bus, motorcycle), անորոշ շրջանակները դիմակավորված են։',
    'UA-DETRAC-ը ուսուցման մեջ չի մասնակցել. մոդելը գնահատվում է այն տեսախցիկներով, որոնք երբեք չի տեսել։',
  ]), { x: 0.6, y: 4.55, w: 12.1, h: 2.2, fontSize: 16, paraSpaceAfter: 8, valign: 'top' });
  notes(s, 4);
}

// 5. Experiments: what improves the model
{
  const s = content('Ուսուցման փորձեր՝ ինչն է բարելավում մոդելը');
  [
    ['Փոխանցմամբ ուսուցում', '2,6% → 13,8%', 'COCO կշիռներ՝ զրոյից ուսուցման փոխարեն (VisDrone, 1024 պատկեր)'],
    ['Մուտքի չափ 960 պքս', '34,7% → 45,9%', 'Փոքր մեքենաները պահպանում են մանրամասները (VisDrone թեստ)'],
    ['Ճանապարհային տվյալներ', '15,1% → 83,7%', 'MIO-TCD թեստ՝ տիրույթի տեղաշարժը վերացված է'],
    ['YOLOv8s + 12 դարաշրջան', '43,0% → 51,4%', 'Ավելի մեծ մոդել և երկարացված ուսուցում (VisDrone, 960)'],
  ].forEach(([title, value, body], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.35;
    card(s, x, y, 5.95, 2.1);
    text(s, title, { x: x + 0.3, y: y + 0.2, w: 5.4, h: 0.45, fontSize: 18, bold: true });
    text(s, value, { x: x + 0.3, y: y + 0.65, w: 5.4, h: 0.75, fontSize: 34, bold: true, color: COL.teal });
    text(s, body, { x: x + 0.3, y: y + 1.4, w: 5.4, h: 0.55, fontSize: 14, color: COL.muted, valign: 'top' });
  });
  text(s, '12 փորձ, mAP50 թեստային ընտրանքում։ Պարզ ընդլայնումը (augmentation) էական օգուտ չի տվել՝ ±0,1 կետ։',
    { x: 0.6, y: 6.35, w: 11.5, h: 0.45, fontSize: 14, color: COL.muted, italic: true });
  notes(s, 5);
}

// 6. Model selection on validation (and the architecture comparison)
{
  const s = content('Մոդելի ընտրությունը');
  const labels = ['road-combined\nYOLOv8n', 'road-yolov8s', 'road-yolo11s', 'road-yolo26s', 'road-yolov8s-long'];
  s.addChart(pres.charts.BAR, [{ name: 'Val mAP50–95', labels, values: [41.1, 44.3, 44.1, 45.5, 47.2] }], {
    x: 0.6, y: 1.45, w: 8.2, h: 5.3, barDir: 'col', barGapWidthPct: 55,
    chartColors: [COL.teal],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 12, dataLabelFontFace: FONT, dataLabelColor: COL.ink,
    dataLabelFormatCode: '0.0',
    catAxisLabelFontFace: FONT, catAxisLabelFontSize: 12, catAxisLabelColor: COL.ink,
    valAxisLabelFontFace: FONT, valAxisLabelFontSize: 11, valAxisLabelColor: COL.muted, valAxisMinVal: 30, valAxisMaxVal: 50,
    valAxisTitle: 'Val mAP50–95, %', showValAxisTitle: true, valAxisTitleFontFace: FONT, valAxisTitleFontSize: 12, valAxisTitleColor: COL.muted,
    valGridLine: { color: 'E1E6E9', size: 0.5 }, catGridLine: { style: 'none' }, showLegend: false,
  });
  text(s, 'Ընտրությունը՝ միայն ստուգողական ընտրանքով (val mAP50–95)։ Առանցքը սկսվում է 30-ից։ YOLO11s և YOLO26s՝ նույն 8 դարաշրջանով, ինչ YOLOv8s-ը։',
    { x: 0.6, y: 6.8, w: 8.2, h: 0.35, fontSize: 12, color: COL.muted, italic: true });
  card(s, 9.2, 1.6, 3.5, 5.1, COL.asphalt);
  text(s, 'Առաջարկվող մոդել', { x: 9.45, y: 1.8, w: 3.0, h: 0.4, fontSize: 15, bold: true, color: COL.marking });
  text(s, 'vehicle-road-yolov8s-long', { x: 9.45, y: 2.2, w: 3.0, h: 0.4, fontSize: 14, color: 'D5DCE0' });
  [['51,4%', 'VisDrone mAP50 (թեստ)'], ['90,2%', 'MIO-TCD mAP50 (թեստ)'], ['45,5%', 'YOLO26s՝ լավագույնը հավասար պայմաններում']].forEach(([v, l], i) => {
    text(s, v, { x: 9.45, y: 2.85 + i * 1.25, w: 3.0, h: 0.65, fontSize: 32, bold: true, color: COL.white });
    text(s, l, { x: 9.45, y: 3.5 + i * 1.25, w: 3.0, h: 0.55, fontSize: 13, color: 'D5DCE0', valign: 'top' });
  });
  notes(s, 6);
}

// 7. Counting rule and calibration
{
  const s = content('Հաշվման կանոնը և տրամաչափումը');
  s.addImage({ path: R('reports/thesis/annotated-v1.jpg'), x: 0.6, y: 1.55, w: 6.6, h: 6.6 * 1080 / 1920 });
  text(s, 'Դեղին՝ հաշվման գիծ, մանուշակագույն՝ լրացուցիչ գիծ, երկնագույն՝ տրամաչափված գոտի 25 × 250 մ',
    { x: 0.6, y: 5.35, w: 6.6, h: 0.6, fontSize: 13, color: COL.muted, valign: 'top' });
  text(s, bullets([
    'Հենակետ՝ շրջանակի ստորին կողմի միջնակետը',
    'Հիստերեզիս 4 պքս՝ դողը կրկնակի հաշվարկ չի տալիս',
    'Մեկ ID՝ մեկ հատում, կրկնակի ID-ների զտիչ',
    'Հետագիծը հաշվվում է առնվազն 10 կադրից հետո',
    'Դասը՝ վստահությամբ կշռված քվեարկություն ամբողջ հետագծով',
    'Տրամաչափում՝ 4 կետ և իրական չափեր → հոմոգրաֆիա',
  ]), { x: 7.6, y: 1.6, w: 5.1, h: 5.0, fontSize: 16, paraSpaceAfter: 10, valign: 'top' });
  notes(s, 7);
}

// 8. Traffic characteristics
{
  const s = content('Երթևեկության բնութագրերը');
  s.addImage({ path: R('reports/thesis/calibration-zones.jpg'), x: 0.6, y: 1.45, w: 12.1, h: 12.1 * 540 / 1920 });
  [['1506', 'մեքենա/ժամ ինտենսիվություն'], ['117,5', 'կմ/ժ տարածական միջին արագություն'],
    ['A', 'LOS ըստ ուղղությունների, 5,1 pc/կմ/գոտի'], ['14%', 'q-ի և k·v-ի տարբերություն']]
    .forEach(([v, l], i) => stat(s, 0.6 + i * 3.1, 5.05, 2.9, v, l));
  notes(s, 8);
}

// 9. The application
{
  const s = content('Օգտագործողի միջերեսը');
  s.addImage({ path: UI, x: 0.6, y: 1.45, w: 5.3 * 1280 / 1150, h: 5.3 });
  text(s, bullets([
    'Հայերեն միջերես (Streamlit) և հրամանային տող',
    'Ֆայլ կամ ուղիղ հոսք՝ RTSP, HLS, YouTube',
    'Հաշվման գծեր և տրամաչափում կադրի վրա',
    'Սալիկային ռեժիմ փոքր մեքենաների համար (VisDrone 52,2%)',
    'CSV/JSON, ջերմային քարտեզ, հետագծեր, LOS ըստ ուղղությունների',
    'Հաշվարկի ստուգման գործիք էտալոնային նշագրմամբ',
    '87 ավտոմատ թեստ (GitHub Actions)',
  ]), { x: 7.0, y: 1.6, w: 5.7, h: 5.0, fontSize: 17, paraSpaceAfter: 10, valign: 'top' });
  notes(s, 9);
}

// 10. Highway video results
{
  const s = content('Արդյունքները մայրուղու տեսանյութում');
  table(s, [
    [head('Կանոններ'), head('Քանակ'), head('Ճիշտ'), head('Ավելորդ')],
    ['սկզբնական (scratch-pilot)', '11', '10', '1'],
    ['class-agnostic NMS', '9', '9', '0'],
    ['+ գծից անցած մեքենաներ', '10', '10', '0'],
    [strong('լռելյայն (UA-DETRAC-ով)'), strong('9'), strong('9'), strong('0')],
  ], 0.6, 1.55, 6.3, [3.3, 1.0, 1.0, 1.0]);
  text(s, bullets([
    'Էտալոն՝ 10 հատում, 4K, 21,5 վ',
    'Բաց է թողնված բեռնատարը, որը գիծը հատել էր տեսագրության սկզբից առաջ',
    'Արագություն՝ միջինը 122 կմ/ժ, 85-րդ պերցենտիլ՝ 141 կմ/ժ',
  ]), { x: 0.6, y: 4.35, w: 6.3, h: 1.5, fontSize: 14, paraSpaceAfter: 6, valign: 'top' });
  card(s, 0.6, 5.95, 6.3, 0.85, COL.sand);
  text(s, 'Արագացված տեսանյութ՝ 709 կմ/ժ, 37 910 մեք/ժ → ավտոմատ նախազգուշացում',
    { x: 0.8, y: 6.0, w: 5.9, h: 0.75, fontSize: 14, bold: true, valign: 'middle' });
  s.addImage({ path: R('reports/thesis/annotated-v2.jpg'), x: 7.3, y: 1.55, w: 5.4, h: 5.4 * 1080 / 1920 });
  text(s, 'Տեսանյութ 2-ը արագացված է. ծրագիրը դա հայտնաբերում է ֆիզիկական ստուգումներով։',
    { x: 7.3, y: 4.7, w: 5.4, h: 0.7, fontSize: 13, color: COL.muted, valign: 'top' });
  notes(s, 10);
}

// 11. UA-DETRAC protocol
{
  const s = content('Ստուգում UA-DETRAC հավաքածուով');
  s.addImage({ path: R('reports/detrac-check-preview.jpg'), x: 0.6, y: 1.55, w: 6.6, h: 6.6 * 540 / 960 });
  text(s, 'Գիծը ֆիքսված է նախապես՝ կադրի բարձրության 60%-ում', { x: 0.6, y: 5.35, w: 6.6, h: 0.4, fontSize: 13, color: COL.muted });
  card(s, 7.6, 1.55, 5.1, 1.6);
  text(s, '20 տեսանյութ', { x: 7.85, y: 1.7, w: 4.6, h: 0.6, fontSize: 28, bold: true, color: COL.muted });
  text(s, 'միայն հաշվման կանոնների ընտրության համար', { x: 7.85, y: 2.35, w: 4.6, h: 0.6, fontSize: 15, color: COL.muted, valign: 'top' });
  card(s, 7.6, 3.35, 5.1, 1.6, COL.asphalt);
  text(s, '20 տեսանյութ', { x: 7.85, y: 3.5, w: 4.6, h: 0.6, fontSize: 28, bold: true, color: COL.marking });
  text(s, 'միայն վերջնական գնահատման համար՝ 28 885 կադր, 388 հատում', { x: 7.85, y: 4.15, w: 4.6, h: 0.7, fontSize: 15, color: 'D5DCE0', valign: 'top' });
  text(s, 'Էտալոն՝ հրապարակված հետագծերից, նույն հաշվման կանոնով', { x: 7.6, y: 5.2, w: 5.1, h: 0.7, fontSize: 15, italic: true, color: COL.muted, valign: 'top' });
  notes(s, 11);
}

// 12. Tracker comparison
{
  const s = content('Հետագծման ալգորիթմների համեմատությունը');
  table(s, [
    [head('Հետագծիչ'), head('F1'), head('Recall'), head('Կադր/վ')],
    ['ByteTrack', '0,837', '94,8%', '25,7'],
    ['BoT-SORT', '0,835', '94,8%', '26,5'],
    ['BoT-SORT + ReID', '0,835', '95,1%', '16,2'],
    ['OC-SORT', '0,843', '94,6%', '20,8'],
    ['Deep OC-SORT', '0,842', '94,8%', '12,8'],
    ['TrackTrack', '0,832', '94,3%', '13,4'],
  ], 0.6, 1.55, 7.0, [2.8, 1.4, 1.4, 1.4], 15);
  text(s, 'UA-DETRAC, 20 տեսանյութ, սկզբնական կանոններ։ Deep OC-SORT-ի և TrackTrack-ի արագությունը չափվել է համակարգչի այլ բեռնվածության ժամանակ։',
    { x: 0.6, y: 5.0, w: 7.0, h: 0.8, fontSize: 12, color: COL.muted, italic: true, valign: 'top' });
  card(s, 8.1, 1.55, 4.6, 4.9, COL.light);
  stat(s, 8.4, 1.8, 4.0, '0,011', 'F1-ի առավելագույն տարբերությունը վեց ալգորիթմների միջև');
  stat(s, 8.4, 3.55, 4.0, '25%', 'մոտավորապես այդքան ավելորդ հատում բոլորի մոտ', COL.red);
  text(s, 'Սխալների աղբյուրը հետագծիչը չէ, այլ հաշվման կանոնները', { x: 8.4, y: 5.25, w: 4.0, h: 1.0, fontSize: 16, bold: true, valign: 'top' });
  notes(s, 12);
}

// 13. Extra crossings
{
  const s = content('Ավելորդ հատումների վերլուծությունը');
  stat(s, 0.6, 1.5, 3.4, '123', 'ավելորդ հատում (ByteTrack, սկզբնական կանոններ, 20 տեսանյութ)', COL.red);
  table(s, [
    [head('Պատճառ'), head('Քանակ')],
    ['Մոտոցիկլներ (UA-DETRAC-ում նշագրված չեն)', '42'],
    ['Մոտակայքում էտալոնային մեքենա չկա', '34'],
    [strong('«Գծից արդեն անցած մեքենայի» կանոն'), strong('25')],
    ['Նույն մեքենան՝ 6 կադրի թույլատրելի շեղումից դուրս', '17'],
    ['Կրկնակի հաշվարկ և շատ կարճ հետագծեր', '5'],
  ], 4.4, 1.55, 8.3, [6.8, 1.5], 15);
  card(s, 0.6, 3.6, 3.4, 2.4, COL.sand);
  text(s, 'Կանոնից կախված մասը կարելի է ուղղել. դա արվել է հաջորդ քայլում', { x: 0.85, y: 3.75, w: 2.9, h: 2.1, fontSize: 16, bold: true, valign: 'middle' });
  text(s, 'Վերլուծությունը՝ scripts/analyze_extra_crossings.py, հետագծերը վերարտադրված են նույն հաշվման կոդով։',
    { x: 4.4, y: 5.0, w: 8.3, h: 0.6, fontSize: 12, color: COL.muted, italic: true, valign: 'top' });
  notes(s, 13);
}

// 14. Counting rule tuning
{
  const s = content('Հաշվման կանոնների ճշգրտումը');
  text(s, bullets([
    'Ընտրվել է 20 առանձնացված տեսանյութով',
    '«Գծից արդեն անցած մեքենայի» կանոնն անջատված է',
    'Հետագիծը հաշվվում է առնվազն 10 կադրից հետո',
  ]), { x: 0.6, y: 1.55, w: 12.1, h: 1.3, fontSize: 17, paraSpaceAfter: 6, valign: 'top' });
  [['0,879 → 0,911', 'F1, ByteTrack'], ['15,7% → 8,2%', 'ընդհանուր քանակի սխալ (ավելորդ հատումներ)'], ['94,8%', 'գտնված հատումներ, չի նվազել'], ['98%', 'դասի ճշտություն']]
    .forEach(([v, l], i) => {
      const x = 0.6 + (i % 2) * 6.15, y = 3.05 + Math.floor(i / 2) * 1.75;
      card(s, x, y, 5.95, 1.55);
      text(s, v, { x: x + 0.3, y: y + 0.15, w: 5.4, h: 0.75, fontSize: 32, bold: true, color: COL.teal });
      text(s, l, { x: x + 0.3, y: y + 0.9, w: 5.4, h: 0.5, fontSize: 15, color: COL.muted });
    });
  text(s, 'Գնահատման 20 տեսանյութ, մոտոցիկլներն առանց։ Բարելավումը նույնն է բոլոր վեց հետագծիչների համար։',
    { x: 0.6, y: 6.6, w: 11.5, h: 0.4, fontSize: 13, color: COL.muted, italic: true });
  notes(s, 14);
}

// 15. Limitations and future work
{
  const s = content('Սահմանափակումներ և հետագա աշխատանք');
  card(s, 0.6, 1.55, 5.95, 5.1);
  text(s, 'Սահմանափակումներ', { x: 0.9, y: 1.75, w: 5.4, h: 0.45, fontSize: 19, bold: true });
  text(s, bullets([
    'Արագությունը չի ստուգվել ռադարով կամ GPS-ով, տրամաչափումները մոտավոր են',
    'Մայրուղու տեսանյութի էտալոնը նախնական է',
    'Գիշերը և վատ եղանակին առանձին գնահատում չկա',
    'Մեկ seed, մոտոցիկլները UA-DETRAC-ում նշագրված չեն',
  ]), { x: 0.9, y: 2.35, w: 5.4, h: 4.1, fontSize: 15, paraSpaceAfter: 10, valign: 'top' });
  card(s, 6.75, 1.55, 5.95, 5.1, COL.asphalt);
  text(s, 'Հետագա աշխատանք', { x: 7.05, y: 1.75, w: 5.4, h: 0.45, fontSize: 19, bold: true, color: COL.marking });
  text(s, bullets([
    'YOLO26s-ի երկարացված ուսուցում ավելի մեծ հիշողությամբ',
    'Արագության ստուգում BrnoCompSpeed հավաքածուով',
    'Գիշերային և անձրևային տեսանյութերի գնահատում',
    'Արտահանում Core ML և ONNX ձևաչափերով',
  ]), { x: 7.05, y: 2.35, w: 5.4, h: 4.1, fontSize: 15, paraSpaceAfter: 10, color: 'D5DCE0', valign: 'top' });
  notes(s, 15);
}

// 16. Conclusions
{
  const s = pres.addSlide({ masterName: 'DARK' });
  text(s, 'Եզրակացություններ', { x: 0.7, y: 0.5, w: 12, h: 0.9, fontSize: 34, bold: true, color: COL.white, valign: 'middle' });
  [
    'Ամբողջական և վերարտադրելի համակարգ՝ տվյալներից մինչև ինտենսիվություն, արագություն, խտություն և LOS',
    '90,2% mAP50 ճանապարհային տեսախցիկներում (MIO-TCD), 51,4%՝ VisDrone-ում',
    'Անկախ UA-DETRAC տեսանյութերում՝ 95% գտնված հատումներ, F1 0,911, քանակի սխալ +8%',
    '87 ավտոմատ թեստ, կոդը և մոդելները՝ GitHub-ում',
  ].forEach((r, i) => {
    badge(s, 0.7, 1.75 + i * 1.05, String(i + 1));
    text(s, r, { x: 1.55, y: 1.7 + i * 1.05, w: 10.9, h: 0.75, fontSize: 18, color: COL.white, valign: 'middle' });
  });
  text(s, 'Շնորհակալություն ուշադրության համար', { x: 0.7, y: 6.25, w: 12, h: 0.6, fontSize: 22, bold: true, color: COL.marking });
  notes(s, 16);
}

pres.writeFile({ fileName: OUT }).then(() => console.log('Saved', OUT));
