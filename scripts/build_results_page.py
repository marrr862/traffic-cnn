"""Build docs/site/results.html: every result of the thesis on one page, for showing at the defense.

The page is generated from chapter 5 of the Armenian thesis (thesis/hy/05-results.md), so its tables,
figures and conclusions always match the text; a summary, the two demo videos (docs/site/media) and
navigation are added on top. Figures are copied, resized, to docs/site/img/r/.

    python scripts/build_results_page.py              # docs/site/results.html (GitHub Pages)
    python scripts/build_results_page.py --fragment X # also a copy without <!doctype>/<html> for claude.ai
"""
import argparse
import html
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'thesis/hy/05-results.md'
SITE = ROOT / 'docs/site'
IMAGES = SITE / 'img/r'

SUMMARY = [
    ('90,2%', 'mAP50 ճանապարհային տեսախցիկներում (MIO-TCD թեստ)'),
    ('51,4%', 'mAP50 անօդաչու սարքի պատկերներում (VisDrone թեստ, 960 պքս)'),
    ('0,911', 'հաշվարկի F1 UA-DETRAC-ի 20 անկախ տեսանյութում'),
    ('94,8%', 'գտնված հատումներ, ընդհանուր քանակի սխալ +8,2%'),
    ('12', 'ուսուցման փորձ, 3 YOLO ճարտարապետություն'),
    ('6', 'հետագծման ալգորիթմ, F1-ի տարբերություն < 0,011'),
    ('3,0%', 'արագության երկու անկախ եղանակների միջին տարբերություն'),
    ('87', 'ավտոմատ թեստ'),
]

CSS = """
/* Layout: one reading column with a sticky section index; asphalt header band; lane-line dividers. */
:root {
  --asphalt: #1f2a31; --marking: #f2b705; --teal: #14807a; --red: #c2412d;
  --bg: #fbfcfc; --surface: #eef2f3; --fg: #1b252b; --muted: #56636b; --line: #d7dfe2; --row: #f6f8f9;
  --hero-fg: #f4f7f8; --hero-muted: #b9c5cb;
  --display: "Overpass", "Noto Sans Armenian", "Arial", sans-serif;
  --body: "Noto Sans Armenian", "Overpass", "Segoe UI", "Arial", sans-serif;
  --mono: "Overpass Mono", "SFMono-Regular", "Menlo", monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #131b20; --surface: #1c262d; --fg: #e6edf0; --muted: #9fb0b8; --line: #2e3b44; --row: #172128; --teal: #3fb3aa; --red: #e5735f; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #131b20; --surface: #1c262d; --fg: #e6edf0; --muted: #9fb0b8; --line: #2e3b44; --row: #172128; --teal: #3fb3aa; --red: #e5735f; color-scheme: dark }
* { box-sizing: border-box; }
img, video { max-width: 100%; height: auto; }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 16.5px; line-height: 1.65; }
.wrap { max-width: 1180px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1, h2, h3 { font-family: var(--display); line-height: 1.2; text-wrap: balance; margin: 0; }
a { color: var(--teal); text-underline-offset: 3px; }
a:focus-visible { outline: 3px solid var(--marking); outline-offset: 2px; }
header.hero { background: var(--asphalt); color: var(--hero-fg); }
header.hero .wrap { padding-block: 22px 40px; display: grid; gap: 26px; }
.top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; font-family: var(--display); }
.brand { font-weight: 800; letter-spacing: .02em; }
.brand span { color: var(--marking); }
.top a { color: var(--hero-muted); }
.eyebrow { font-family: var(--mono); font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; color: var(--marking); }
header h1 { font-size: clamp(1.7rem, 3.6vw, 2.6rem); font-weight: 800; max-width: 30ch; }
header p { color: var(--hero-muted); max-width: 70ch; margin: 0; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px 22px; border-top: 2px dashed #4a5a64; padding-top: 22px; }
.stats div { display: grid; gap: 2px; min-width: 0; }
.stats b { font-family: var(--display); font-size: clamp(1.5rem, 2.8vw, 2.1rem); font-variant-numeric: tabular-nums; }
.stats span { color: var(--hero-muted); font-size: .88rem; line-height: 1.4; }
.layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 40px; padding-block: 36px 64px; }
nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 16px); align-self: start; font-size: .9rem; }
nav.toc ol { list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; border-left: 2px dashed var(--line); }
nav.toc a { display: block; padding: 2px 0 2px 12px; color: var(--muted); text-decoration: none; line-height: 1.35; }
nav.toc a:hover { color: var(--fg); }
nav.toc .num { font-family: var(--mono); color: var(--teal); margin-right: 4px; }
main { min-width: 0; }
section { padding-block: 26px; scroll-margin-top: 16px; }
section + section { border-top: 2px dashed var(--line); }
section h2 { font-size: clamp(1.3rem, 2.4vw, 1.7rem); font-weight: 800; margin-bottom: 14px; }
section h2 .num { color: var(--teal); font-family: var(--mono); font-weight: 600; margin-right: 8px; }
main p { margin: 0 0 12px; max-width: 75ch; }
main ul { margin: 0 0 12px; padding-left: 22px; max-width: 75ch; }
code { font-family: var(--mono); font-size: .88em; background: var(--surface); padding: 1px 5px; border-radius: 4px; }
.videos { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
figure { margin: 0 0 16px; }
figure video, figure img { display: block; width: 100%; border-radius: 8px; border: 1px solid var(--line); background: #000; }
figure img { background: #fff; }
figcaption { font-size: .86rem; color: var(--muted); margin-top: 8px; line-height: 1.45; }
.table { margin: 6px 0 18px; }
.table .cap { font-weight: 700; font-size: .92rem; margin-bottom: 6px; }
.scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; font-variant-numeric: tabular-nums; }
th, td { padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--asphalt); color: #f4f7f8; font-weight: 600; white-space: nowrap; }
td.n, th.n { text-align: right; white-space: nowrap; }
tr:nth-child(even) td { background: var(--row); }
tr.best td { font-weight: 700; }
.note { font-size: .84rem; color: var(--muted); }
footer { background: var(--asphalt); color: var(--hero-muted); font-size: .9rem; }
footer .wrap { padding-block: 24px; display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
footer a { color: var(--marking); }
@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; gap: 10px; }
  nav.toc { position: static; }
  .stats { grid-template-columns: 1fr 1fr; }
  .videos { grid-template-columns: 1fr; }
}
"""


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def copy_image(path):
    source = ROOT / path
    IMAGES.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9.-]+', '-', str(path).replace('reports/', '').replace('runs/experiments/', ''))
    target = IMAGES / (Path(name).stem + ('.png' if source.suffix == '.png' else '.jpg'))
    image = Image.open(source)
    if image.width > 1400:
        image = image.resize((1400, round(image.height * 1400 / image.width)), Image.LANCZOS)
    if target.suffix == '.png':
        image.save(target, optimize=True)
    else:
        image.convert('RGB').save(target, quality=82, optimize=True, progressive=True)
    return f'img/r/{target.name}', image.size


def table(lines, caption):
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    head, align, body = rows[0], rows[1], rows[2:]
    numeric = [a.endswith(':') for a in align]
    out = ['<div class="table">']
    if caption:
        out.append(f'<div class="cap">{inline(caption)}</div>')
    out.append('<div class="scroll"><table><thead><tr>')
    out += [f'<th{" class=n" if numeric[i] else ""}>{inline(h)}</th>' for i, h in enumerate(head)]
    out.append('</tr></thead><tbody>')
    for row in body:
        best = row[0].startswith('**')
        out.append(f'<tr{" class=best" if best else ""}>')
        out += [f'<td{" class=n" if i < len(numeric) and numeric[i] else ""}>{inline(c.replace("**", ""))}</td>' for i, c in enumerate(row)]
        out.append('</tr>')
    out.append('</tbody></table></div></div>')
    return '\n'.join(out)


def render(markdown):
    sections, current, lines, caption = [], None, markdown.split('\n'), None
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith('# '):
            i += 1
            continue
        m = re.match(r'^## (\d+\.\d+) (.+)$', line)
        if m:
            current = dict(num=m.group(1), title=m.group(2), body=[])
            sections.append(current)
        elif line.startswith('|'):
            block = []
            while i < len(lines) and lines[i].startswith('|'):
                block.append(lines[i])
                i += 1
            current['body'].append(table(block, caption))
            caption = None
            continue
        elif line.startswith('Աղյուսակ '):
            caption = line
        elif line.startswith('!['):
            m = re.match(r'!\[(.*)\]\((.*)\)', line)
            src, (w, h) = copy_image(m.group(2))
            current['body'].append(f'<figure><img src="{src}" width="{w}" height="{h}" alt="{html.escape(m.group(1))}" loading="lazy">'
                                   f'<figcaption>{inline(m.group(1))}</figcaption></figure>')
        elif line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append(f'<li>{inline(lines[i][2:])}</li>')
                i += 1
            current['body'].append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif line and line[0] in '¹²³⁴⁵':
            current['body'].append(f'<p class="note">{inline(line)}</p>')
        elif line.strip() and current is not None:
            current['body'].append(f'<p>{inline(line)}</p>')
        i += 1
    return sections


def page(sections, standalone):
    stats = ''.join(f'<div><b>{v}</b><span>{html.escape(t)}</span></div>' for v, t in SUMMARY)
    toc = ['<li><a href="#video"><span class="num">▶</span>Տեսանյութեր</a></li>']
    toc += [f'<li><a href="#s{s["num"].replace(".", "-")}"><span class="num">{s["num"]}</span>{inline(s["title"])}</a></li>' for s in sections]
    body = [f'<section id="s{s["num"].replace(".", "-")}"><h2><span class="num">{s["num"]}</span>{inline(s["title"])}</h2>'
            + '\n'.join(s['body']) + '</section>' for s in sections]
    videos = """<section id="video"><h2>Ծրագրի աշխատանքը տեսանյութերում</h2>
<div class="videos">
<figure><video src="media/highway.mp4" poster="media/highway-poster.jpg" controls muted loop playsinline preload="metadata" width="1280" height="720"></video>
<figcaption>Մայրուղի, 4K, 21,5 վ. դեղին՝ հաշվման գիծ, մանուշակագույն՝ լրացուցիչ գիծ (արագության ստուգում), երկնագույն՝ տրամաչափված գոտի 25 × 250 մ, մեքենաների տակ՝ արագությունը կմ/ժ (5.4, 5.6 բաժիններ)</figcaption></figure>
<figure><video src="media/timelapse.mp4" poster="media/timelapse-poster.jpg" controls muted loop playsinline preload="metadata" width="1280" height="720"></video>
<figcaption>Արագացված քաղաքային տեսանյութ (առաջին 12 վ). 448 հատում 42 վայրկյանում և 709 կմ/ժ մեդիան արագություն. ծրագիրը նախազգուշացնում է, որ տեսանյութը արագացված է (5.7 բաժին)</figcaption></figure>
</div></section>"""
    head = """<meta charset="utf-8">
<title>Traffic CNN Results</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="Երթևեկության հոսքի վերլուծության ծրագրային միջոցի բոլոր արդյունքները">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Overpass:wght@400;600;800&family=Overpass+Mono:wght@400;600&family=Noto+Sans+Armenian:wght@400;600;700&display=swap">
<style>""" + CSS + "</style>\n"
    if standalone:
        head = ('<!doctype html>\n<html lang="hy">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + head)
    return head + f"""<header class="hero"><div class="wrap">
<div class="top"><div class="brand">TRAFFIC<span>·</span>CNN</div><a href="index.html">← Նախագծի էջ</a></div>
<div class="eyebrow">Ավարտական աշխատանք · արդյունքներ</div>
<h1>Երթևեկության հոսքի վերլուծության ծրագրային միջոցի մշակում՝ փաթույթային նեյրոնային ցանցերի կիրառմամբ</h1>
<p>Ղազարյան Մարիամ Սարգիսի · գիտական ղեկավար՝ Խաչատրյան Տիգրան Բագրատի, տ.գ.թ., ավագ դասախոս · ՀԱՊՀ, 2026։ Էջի աղյուսակները և նկարները վերցված են ատենախոսության 5-րդ գլխից։</p>
<div class="stats">{stats}</div>
</div></header>
<div class="wrap layout">
<nav class="toc" aria-label="Բաժիններ"><ol>{''.join(toc)}</ol></nav>
<main>
{videos}
{''.join(body)}
</main>
</div>
<footer><div class="wrap"><span>Ղազարյան Մարիամ Սարգիսի · Երևան 2026</span>
<a href="https://github.com/marrr862/traffic-cnn" target="_blank" rel="noopener">github.com/marrr862/traffic-cnn</a></div></footer>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fragment', help='also write a copy without the document head (for claude.ai)')
    args = parser.parse_args()
    sections = render(SOURCE.read_text(encoding='utf-8'))
    (SITE / 'results.html').write_text(page(sections, True), encoding='utf-8')
    if args.fragment:
        Path(args.fragment).write_text(page(sections, False), encoding='utf-8')
    print(f'Saved docs/site/results.html: {len(sections)} sections, {len(list(IMAGES.glob("*")))} figures')


if __name__ == '__main__':
    main()
