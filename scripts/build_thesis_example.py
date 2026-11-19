"""Build thesis/DIPLOM.docx: the Armenian thesis restructured to the department sample.

Structure (as in the sample coursework): contents, introduction, problem statement,
chapter 1 (theory), chapter 2 (analysis), chapter 3 (practical part), chapter 4 (economics),
chapter 5 (environment), chapter 6 (life safety), conclusions, references, appendices
(numbered glossary of the terms marked with superscripts in the text).

Sources: thesis/hy/*.md (chapters written earlier) are regrouped by section; the new parts are
in thesis/example/*.md. Tables, figures and section references are renumbered automatically.

    python3 scripts/build_thesis_example.py
"""
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'thesis/hy'
NEW = ROOT / 'thesis/example'
OUTPUT = ROOT / 'thesis/DIPLOM.docx'
MD_OUTPUT = ROOT / 'thesis/example/DIPLOMA_EXAMPLE.md'
TOC_PAGES = ROOT / 'thesis/example/toc_pages.json'  # page numbers for the pre-filled contents
TEXT = ''
FONT = 'Sylfaen'
MONO = 'Courier New'
FIRST_PAGE = 3  # pages 1-2: title page and assignment sheet (department forms)

# ---------------------------------------------------------------- assembling the text

def sections(path, prefix):
    """Split an old chapter file into {'a1.1': (title, body)} by '## N.N Title' headings."""
    out, key = {}, None
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = re.match(r'^## (\d+\.\d+) (.+)$', line)
        if m:
            key = prefix + m.group(1)
            out[key] = [m.group(2).strip(), []]
            continue
        if line.startswith('# '):
            key = None
            continue
        if key:
            out[key][1].append(line)
    return {k: (t, '\n'.join(b).strip()) for k, (t, b) in out.items()}


def top_blocks(path):
    """{'# Heading': body} for top-level blocks of a file."""
    out, key = {}, None
    for line in path.read_text(encoding='utf-8').split('\n'):
        if line.startswith('# '):
            key = line[2:].strip()
            out[key] = []
            continue
        if key is not None:
            out[key].append(line)
    return {k: '\n'.join(v).strip() for k, v in out.items()}


S = {}
S.update(sections(OLD / '01-analysis.md', 'a'))
S.update(sections(OLD / '02-data.md', 'd'))
S.update(sections(OLD / '03-implementation.md', 'i'))
S.update(sections(OLD / '04-method.md', 'm'))
S.update(sections(OLD / '05-results.md', 'r'))
S.update(sections(OLD / '06-manual.md', 'u'))
FRONT = top_blocks(OLD / '00-front.md')
MANUAL = top_blocks(OLD / '06-manual.md')

YOLO_FIGURE = '![Նկար 1.90. YOLOv8 դետեկտորի կառուցվածքի սխեման](reports/thesis/yolov8-hy.png)'

CHAPTERS = [
    ('ԳԼՈՒԽ 1. ԵՐԹԵՎԵԿՈՒԹՅԱՆ ՀՈՍՔԻ ՎԵՐԼՈՒԾՈՒԹՅԱՆ ՏԵԽՆՈԼՈԳԻԱՆԵՐԸ', [
        ('1.1. ԵՐԹԵՎԵԿՈՒԹՅԱՆ ՀՈՍՔԻ ԲՆՈՒԹԱԳՐԵՐԸ ԵՎ ՏՎՅԱԼՆԵՐԻ ՀԱՎԱՔՄԱՆ ԵՂԱՆԱԿՆԵՐԸ', ['a1.1', 'a1.2']),
        ('1.2. ՓԱԹՈՒՅԹԱՅԻՆ ՆԵՅՐՈՆԱՅԻՆ ՑԱՆՑԵՐԸ ԵՎ YOLOv8 ԴԵՏԵԿՏՈՐԸ', ['a1.3', 'a1.4', 'a1.5']),
        ('1.3. ՀԵՏԱԳԾՄԱՆ ԵՎ ՏՐԱՄԱՉԱՓՄԱՆ ՄԵԹՈԴՆԵՐԸ', ['a1.6', 'a1.7']),
    ]),
    ('ԳԼՈՒԽ 2. ՏՎՅԱԼՆԵՐԻ ՊԱՏՐԱՍՏՈՒՄԸ ԵՎ CNN-Ի ՈՒՍՈՒՑՄԱՆ ՓՈՐՁԵՐԻ ՎԵՐԼՈՒԾՈՒԹՅՈՒՆԸ', [
        ('2.1. ՈՒՍՈՒՑՄԱՆ ՏՎՅԱԼՆԵՐԻ ՊԱՏՐԱՍՏՈՒՄԸ', ['d2.1', 'd2.2', 'd2.3', 'd2.4']),
        ('2.2. ՍՏՈՒԳՄԱՆ ՏՎՅԱԼՆԵՐԸ ԵՎ ԳՆԱՀԱՏՄԱՆ ՄԵԹՈԴԻԿԱՆ', ['d2.5', 'd2.6', 'm4.1', 'm4.2', 'm4.3', 'm4.4', 'm4.5']),
        ('2.3. CNN-Ի ՈՒՍՈՒՑՄԱՆ ՓՈՐՁԵՐԸ ԵՎ ՄՈԴԵԼՆԵՐԻ ՀԱՄԵՄԱՏՈՒԹՅՈՒՆԸ', ['r5.1', 'r5.2', 'r5.3', 'r5.10']),
    ]),
    ('ԳԼՈՒԽ 3. ԾՐԱԳՐԱՅԻՆ ՄԻՋՈՑԻ ՆԱԽԱԳԾՈՒՄԸ ԵՎ ՓՈՐՁԱՐԿՈՒՄԸ', [
        ('3.1. ԾՐԱԳՐԻ ՃԱՐՏԱՐԱՊԵՏՈՒԹՅՈՒՆԸ ԵՎ ԱԼԳՈՐԻԹՄՆԵՐԸ', ['i3.1', 'i3.2', 'i3.3', 'i3.4', 'i3.5', 'i3.6', 'i3.7', 'i3.8', 'i3.9']),
        ('3.2. ՕԳՏԱԳՈՐԾՈՂԻ ՄԻՋԵՐԵՍԸ ԵՎ ԾՐԱԳՐԻ ՍՏՈՒԳՈՒՄԸ', ['i3.10', 'u6.1', 'u6.2', 'u6.3', 'u6.4', 'i3.11']),
        ('3.3. ՏԵՍԱՆՅՈՒԹԵՐԻ ՎԵՐԼՈՒԾՈՒԹՅԱՆ ԱՐԴՅՈՒՆՔՆԵՐԸ', ['r5.4', 'r5.5', 'r5.9', 'r5.6', 'r5.7', 'r5.8', 'r5.11']),
    ]),
]

# old section number -> new section number (for "N.N բաժին" references)
SECTION_MAP = {}
for chapter_title, parts in CHAPTERS:
    for title, keys in parts:
        for key in keys:
            SECTION_MAP[key] = title.split('. ')[0]
OLD_SECTION = {}  # bare old number -> new, by the file the reference points to
for key, new in SECTION_MAP.items():
    OLD_SECTION.setdefault(key[1:], new)
# the old files reuse numbers 2.x (data) / 3.x (implementation) / 4.x (method) / 5.x (results) / 6.x (manual)
for prefix in 'dimru':
    for key, new in SECTION_MAP.items():
        if key[0] == prefix:
            OLD_SECTION[key[1:]] = new


def chapter_markdown():
    out = []
    for chapter_title, parts in CHAPTERS:
        out.append('# ' + chapter_title)
        for title, keys in parts:
            out.append('## ' + title)
            for key in keys:
                sub_title, body = S[key]
                out.append('### ' + sub_title)
                out.append(body)
                if key == 'a1.4':
                    out.append(YOLO_FIGURE)
    return '\n\n'.join(out)


def intro_markdown():
    keep = []
    for block in re.split(r'\n\s*\n', FRONT['Ներածություն']):
        b = block.strip()
        if not b or b.startswith('**Աշխատանքի նպատակն**') or b.startswith('Նպատակին հասնելու') \
                or re.match(r'^\d+\. ', b) or b.startswith('Աշխատանքը բաղկացած'):
            continue
        keep.append(b)
    tail = (NEW / 'intro_tail.md').read_text(encoding='utf-8').strip()
    return '# ՆԵՐԱԾՈՒԹՅՈՒՆ\n\n' + '\n\n'.join(keep) + '\n\n' + tail


def renumber(text):
    """Renumber tables and figures per new chapter and rewrite references."""
    tables, figures = {}, {}
    chapter, t_count, f_count = 0, 0, 0
    for line in text.split('\n'):
        m = re.match(r'^# ԳԼՈՒԽ (\d+)', line)
        if m:
            chapter, t_count, f_count = int(m.group(1)), 0, 0
            continue
        m = re.match(r'^Աղյուսակ (\d+\.\d+)\.', line)
        if m and chapter:
            t_count += 1
            tables[m.group(1)] = f'{chapter}.{t_count}'
        m = re.match(r'^!\[Նկար (\d+\.\d+)\.', line)
        if m and chapter:
            f_count += 1
            figures[m.group(1)] = f'{chapter}.{f_count}'
    text = re.sub(r'^Աղյուսակ (\d+\.\d+)\.\s*', lambda m: f'Աղյուսակ {tables[m.group(1)]} ', text, flags=re.M)
    text = re.sub(r'^!\[Նկար (\d+\.\d+)\.\s*', lambda m: f'![Նկ. {figures[m.group(1)]}. ', text, flags=re.M)
    text = re.sub(r'([Աա]ղյուսակ) (\d+\.\d+)', lambda m: f'{m.group(1)} {tables.get(m.group(2), m.group(2))}', text)
    text = re.sub(r'(Ն|ն)կար (\d+\.\d+)', lambda m: f'{m.group(1)}կ. {figures.get(m.group(2), m.group(2))}', text)
    text = re.sub(r'(\d+\.\d+)( բաժ)', lambda m: OLD_SECTION.get(m.group(1), m.group(1)) + m.group(2), text)
    text = text.replace('5-րդ գլխում', '2-րդ գլխում').replace('(5-րդ գլուխ)', '(2-րդ և 3-րդ գլուխներ)')
    return text


def references_markdown():
    old = MANUAL['Օգտագործված գրականություն'].strip()
    extra = (NEW / 'refs_extra.md').read_text(encoding='utf-8').strip()
    return '# ԳՐԱԿԱՆՈՒԹՅԱՆ ՑԱՆԿ\n\n' + old + '\n' + extra


def appendix_markdown():
    a = MANUAL['Հավելված Ա. Վերարտադրման հրամաններ']
    b = MANUAL['Հավելված Բ. Հաշվման կանոնի ելակետային կոդը']
    b = re.sub(r'(\d+\.\d+)( բաժ)', lambda m: OLD_SECTION.get(m.group(1), m.group(1)) + m.group(2), b)
    return ('# ՀԱՎԵԼՎԱԾՆԵՐ\n\n[[GLOSSARY]]\n\n### Հավելված Ա. Վերարտադրման հրամաններ\n\n' + a +
            '\n\n### Հավելված Բ. Հաշվման կանոնի ելակետային կոդը\n\n' + b)


def assemble():
    body = renumber(intro_markdown() + '\n\n' + (NEW / '05_problem.md').read_text(encoding='utf-8') +
                    '\n\n' + chapter_markdown())
    rest = [(NEW / name).read_text(encoding='utf-8') for name in
            ('40_economics.md', '50_ecology.md', '60_safety.md', '70_end.md')]
    return '\n\n'.join([body] + rest + [references_markdown(), appendix_markdown()])

# ---------------------------------------------------------------- glossary (superscript numbers)

GLOSSARY = []
for line in (NEW / 'glossary.tsv').read_text(encoding='utf-8').splitlines():
    if line.strip():
        pattern, term, definition = line.split('\t')
        GLOSSARY.append(dict(pattern=re.compile(pattern), term=term, definition=definition, number=None))
USED = []


def mark_terms(text):
    """Insert {^n} before the first occurrence of each glossary term (outside code spans)."""
    hits = []
    for entry in GLOSSARY:
        if entry['number'] is not None:
            continue
        for m in entry['pattern'].finditer(text):
            if text[:m.start()].count('`') % 2 == 0 and 'http' not in text[max(0, m.start()-40):m.start()]:
                hits.append((m.start(), entry))
                break
    hits.sort(key=lambda h: h[0])
    taken = set()
    for position, entry in hits:
        if position in taken:
            continue
        taken.add(position)
        USED.append(entry)
        entry['number'] = len(USED)
    for position, entry in sorted(hits, key=lambda h: -h[0]):
        if entry['number'] is not None and entry in USED and f'{{^{entry["number"]}}}' not in text:
            text = text[:position] + f'{{^{entry["number"]}}}' + text[position:]
    return text

# ---------------------------------------------------------------- docx helpers

def set_font(run, name=FONT, size=None, bold=None, italic=None, superscript=False):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    for key in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
        fonts.set(qn('w:' + key), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if superscript:
        run.font.superscript = True


def add_inline(paragraph, text, size=None, font=FONT, bold=None, italic=None):
    for part in re.split(r'(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)', text):
        if not part:
            continue
        b, i, f, s = bold, italic, font, size
        if part.startswith('**'):
            part, b = part[2:-2], True
        elif part.startswith('`'):
            part, f, s = part[1:-1], MONO, (size or 12) - 1
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            part, i = part[1:-1], True
        for piece in re.split(r'(\{\^\d+\})', part):
            if not piece:
                continue
            sup = re.fullmatch(r'\{\^(\d+)\}', piece)
            if sup:
                set_font(paragraph.add_run(sup.group(1)), f, s, bold=b, italic=i, superscript=True)
            else:
                set_font(paragraph.add_run(piece), f, s, bold=b, italic=i)


def field(paragraph, instruction):
    for kind, text in (('begin', None), (None, instruction), ('separate', None), ('end', None)):
        run = paragraph.add_run()
        if kind:
            node = OxmlElement('w:fldChar')
            node.set(qn('w:fldCharType'), kind)
        else:
            node = OxmlElement('w:instrText')
            node.set(qn('xml:space'), 'preserve')
            node.text = instruction
        run._r.append(node)


def para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, before=0, after=0, spacing=1.5, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.first_line_indent = Cm(1.25) if indent else Cm(0)
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = spacing
    pf.keep_with_next = keep
    return p


def table(doc, lines, title=None):
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    aligns = []
    for r in rows:
        if all(re.fullmatch(r':?-{2,}:?', c) for c in r):
            aligns = ['right' if c.endswith(':') and not c.startswith(':') else 'center' if c.startswith(':') and c.endswith(':') else 'left' for c in r]
    rows = [r for r in rows if not all(re.fullmatch(r':?-{2,}:?', c) for c in r)]
    if title:
        text = title.strip().rstrip('.։') + '։'
        p = para(doc, WD_ALIGN_PARAGRAPH.RIGHT, indent=False, before=6, after=4, spacing=1.15, keep=True)
        add_inline(p, text, size=12)
    columns = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=columns)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    lengths = [min(40, max(4, max(len(r[j].replace('**', '')) if j < len(r) else 0 for r in rows))) for j in range(columns)]
    widths = [16.5 * l / sum(lengths) for l in lengths]
    for j, w in enumerate(widths):  # very narrow columns get at least 1.6 cm
        if w < 1.6:
            widths[j] = 1.6
    scale = 16.5 / sum(widths)
    widths = [Cm(w * scale) for w in widths]
    for index, values in enumerate(rows):
        cells = t.add_row().cells
        for i in range(columns):
            cell = cells[i]
            cell.width = widths[i]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            pf = p.paragraph_format
            pf.first_line_indent, pf.line_spacing = Cm(0), 1.15
            pf.space_after = pf.space_before = Pt(2)
            align = aligns[i] if i < len(aligns) else 'left'
            p.alignment = {'right': WD_ALIGN_PARAGRAPH.RIGHT, 'center': WD_ALIGN_PARAGRAPH.CENTER}.get(align, WD_ALIGN_PARAGRAPH.LEFT)
            text = values[i] if i < len(values) else ''
            if index == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if align == 'left' else p.alignment
                add_inline(p, text.replace('**', ''), size=11)
            else:
                add_inline(p, text, size=11)
    for j, column in enumerate(t.columns):
        column.width = widths[j]
    t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    para(doc, indent=False, spacing=1.0)


def figure(doc, path, text):
    image = ROOT / path
    if not image.exists():
        raise FileNotFoundError(f'Figure not found: {path}')
    p = para(doc, WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=6, after=4, spacing=1.0, keep=True)
    p.add_run().add_picture(str(image), width=Cm(15.5))
    p = para(doc, WD_ALIGN_PARAGRAPH.CENTER, indent=False, after=10, spacing=1.15)
    add_inline(p, text.strip().rstrip('.։') + '։', size=12)


def heading(doc, text, level):
    style = {1: 'Heading 1', 2: 'Heading 2', 3: 'Heading 3'}[level]
    p = doc.add_paragraph(style=style)
    if level == 3:
        add_inline(p, text, size=12, bold=True, italic=True)
    else:
        add_inline(p, text, size=14, bold=True)
    return p


def page_break(doc):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.add_run().add_break(WD_BREAK.PAGE)


def setup(doc):
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin, section.right_margin = Cm(3), Cm(1.5)
    section.top_margin, section.bottom_margin = Cm(2), Cm(2)
    pg = OxmlElement('w:pgNumType')
    pg.set(qn('w:start'), str(FIRST_PAGE))
    section._sectPr.append(pg)
    styles = doc.styles

    def style_font(style, size, bold=False, italic=False):
        style.font.name, style.font.size = FONT, Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold, style.font.italic = bold, italic
        rpr = style.element.get_or_add_rPr()
        fonts = rpr.find(qn('w:rFonts'))
        if fonts is None:
            fonts = OxmlElement('w:rFonts')
            rpr.insert(0, fonts)
        for key in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
            fonts.set(qn('w:' + key), FONT)
        for attribute in list(fonts.attrib):
            if 'heme' in attribute:
                del fonts.attrib[attribute]
        return rpr

    rpr = style_font(styles['Normal'], 12)
    fmt = styles['Normal'].paragraph_format
    fmt.line_spacing, fmt.space_after, fmt.space_before = 1.5, Pt(0), Pt(0)
    fmt.first_line_indent = Cm(1.25)
    fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt.widow_control = True
    for name, size, before, after, align in (('Heading 1', 14, 0, 6, WD_ALIGN_PARAGRAPH.CENTER),
                                             ('Heading 2', 14, 0, 18, WD_ALIGN_PARAGRAPH.CENTER),
                                             ('Heading 3', 12, 10, 4, WD_ALIGN_PARAGRAPH.LEFT)):
        style = styles[name]
        style_font(style, size, bold=True, italic=(name == 'Heading 3'))
        pf = style.paragraph_format
        pf.space_before, pf.space_after = Pt(before), Pt(after)
        pf.first_line_indent = Cm(1.25) if name == 'Heading 3' else Cm(0)
        pf.line_spacing = 1.5
        pf.keep_with_next = True
        pf.alignment = align
    for level in (1, 2):
        try:
            style = styles[f'TOC {level}']
        except KeyError:
            style = styles.add_style(f'TOC {level}', 1)
        style_font(style, 12, bold=True, italic=True)
        pf = style.paragraph_format
        pf.first_line_indent, pf.left_indent = Cm(0), Cm(0)
        pf.space_after, pf.line_spacing = Pt(6), 1.15
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.paragraph_format.first_line_indent = Cm(0)
    field(footer, 'PAGE')
    settings = doc.settings.element
    update = OxmlElement('w:updateFields')
    update.set(qn('w:val'), 'true')
    settings.append(update)
    lang = OxmlElement('w:lang')
    lang.set(qn('w:val'), 'hy-AM')
    rpr.append(lang)


def render(doc, text):
    blocks = re.split(r'\n\s*\n', text)
    first_h1 = True
    in_body = True
    i = 0
    while i < len(blocks):
        block = blocks[i].strip('\n')
        i += 1
        if not block.strip():
            continue
        if block.startswith('```'):
            while not block.rstrip().endswith('```') or block.strip() == '```':
                block += '\n\n' + blocks[i]
                i += 1
            code = block.strip().strip('`').split('\n', 1)[1] if '\n' in block else ''
            for line in code.rstrip('`').rstrip().split('\n'):
                p = para(doc, WD_ALIGN_PARAGRAPH.LEFT, indent=False, spacing=1.0)
                p.paragraph_format.left_indent = Cm(0.8)
                set_font(p.add_run(line), MONO, 9)
            para(doc, indent=False, spacing=1.0)
            continue
        if block.strip() == '[[GLOSSARY]]':
            for entry in USED:
                p = para(doc, indent=False, spacing=1.5)
                set_font(p.add_run(str(entry['number'])), FONT, 12, superscript=True)
                set_font(p.add_run(' ' + entry['term']), FONT, 12, bold=True)
                set_font(p.add_run(' — ' + entry['definition']), FONT, 12)
            continue
        if block.startswith('# '):
            title = block[2:].strip()
            if not first_h1:
                page_break(doc)
            first_h1 = False
            if title in ('ԳՐԱԿԱՆՈՒԹՅԱՆ ՑԱՆԿ', 'ՀԱՎԵԼՎԱԾՆԵՐ'):
                in_body = False
            heading(doc, title, 1)
            continue
        if block.startswith('## '):
            heading(doc, block[3:].strip(), 2)
            continue
        if block.startswith('### '):
            heading(doc, block[4:].strip(), 3)
            continue
        lines = block.split('\n')
        if re.match(r'^Աղյուսակ \d', lines[0]) and len(lines) > 1 and lines[1].lstrip().startswith('|'):
            table(doc, lines[1:], lines[0])
            continue
        if re.match(r'^Աղյուսակ \d', block) and i < len(blocks) and blocks[i].lstrip().startswith('|'):
            table(doc, blocks[i].split('\n'), block)
            i += 1
            continue
        if lines[0].lstrip().startswith('|'):
            table(doc, lines)
            continue
        m = re.fullmatch(r'!\[(.*)\]\((.+)\)', block.strip())
        if m:
            figure(doc, m.group(2), m.group(1))
            continue
        if block.startswith('> '):
            for line in lines:
                body = line[2:].strip()
                number = re.search(r'\s+(\(\d+(\.\d+)?\))$', body)
                p = para(doc, WD_ALIGN_PARAGRAPH.CENTER, indent=False, before=3, after=3)
                if number:
                    body = body[:number.start()]
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(8.25), 1)
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), 2)
                    set_font(p.add_run('\t'), FONT, 12)
                    add_inline(p, body)
                    set_font(p.add_run('\t' + number.group(1)), FONT, 12)
                else:
                    add_inline(p, body)
            continue
        if all(re.match(r'^\s*(- |\d+\. )', line) for line in lines):
            for line in lines:
                level = 1 if re.match(r'^\s{2,}', line) else 0
                item = re.sub(r'^\s*(- |\d+\. )', '', line)
                if in_body:
                    item = mark_terms(item)
                numbered = re.match(r'^\s*(\d+)\. ', line)
                p = para(doc, indent=False)
                pf = p.paragraph_format
                left = 1.25 + 0.75 * (level + 1)
                pf.left_indent, pf.first_line_indent = Cm(left), Cm(-0.75)
                pf.tab_stops.add_tab_stop(Cm(left))
                marker = (numbered.group(1) + '.') if numbered else ('➢' if level else '•')
                if numbered and not in_body:
                    pf.left_indent, pf.first_line_indent = Cm(0.75), Cm(-0.75)
                    pf.tab_stops.add_tab_stop(Cm(0.75))
                set_font(p.add_run(marker + '\t'), FONT, 12)
                add_inline(p, item)
            continue
        text = ' '.join(line.strip() for line in lines)
        if in_body:
            text = mark_terms(text)
        add_inline(para(doc), text)


def toc(doc):
    heading(doc, 'ԲՈՎԱՆԴԱԿՈՒԹՅՈՒՆ', 1).style = doc.styles['Normal']
    p = doc.paragraphs[-1]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(18)
    entries = [(m.group(1), m.group(2).strip()) for m in re.finditer(r'^(#{1,2}) (.+)$', TEXT, flags=re.M)]
    pages = json.loads(TOC_PAGES.read_text(encoding='utf-8')) if TOC_PAGES.exists() else {}
    # A real Word TOC field, pre-filled with entries so it shows even before the fields are updated.
    for index, (level, title) in enumerate(entries):
        p = doc.add_paragraph(style='TOC 1' if level == '#' else 'TOC 2')
        p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        if index == 0:
            for kind, instruction in (('begin', None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ('separate', None)):
                run = p.add_run()
                if kind:
                    node = OxmlElement('w:fldChar'); node.set(qn('w:fldCharType'), kind)
                else:
                    node = OxmlElement('w:instrText'); node.set(qn('xml:space'), 'preserve'); node.text = instruction
                run._r.append(node)
        add_inline(p, title + '\t' + str(pages.get(title, '')), size=12, bold=True, italic=True)
        if index == len(entries) - 1:
            node = OxmlElement('w:fldChar'); node.set(qn('w:fldCharType'), 'end')
            p.add_run()._r.append(node)


def main():
    global TEXT
    text = TEXT = assemble()
    MD_OUTPUT.write_text(text, encoding='utf-8')
    doc = Document()
    setup(doc)
    toc(doc)
    page_break(doc)
    render(doc, text)
    doc.save(OUTPUT)
    captions = set(re.findall(r'^Աղյուսակ (\d+\.\d+) ', text, flags=re.M))
    leftovers = [f'աղյուսակ {n}' for n in re.findall(r'[Աա]ղյուսակ (\d+\.\d+)', text) if n not in captions]
    leftovers += re.findall(r'Նկ\. \d+\.90', text)
    print(f'Saved {OUTPUT.relative_to(ROOT)}; glossary terms: {len(USED)}; unresolved: {leftovers}')


if __name__ == '__main__':
    main()
