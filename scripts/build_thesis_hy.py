"""Build the Armenian thesis (thesis/DIPLOMA.docx) from thesis/hy/*.md.

Usage:
    python -m pip install python-docx      # once (or: pip install -e '.[thesis]')
    python scripts/build_thesis_hy.py

Markdown subset understood by this builder (one block per blank-line-separated paragraph):
    # Heading            chapter heading (starts on a new page)
    ## Heading           section, ### Heading subsection
    plain text           justified paragraph with first-line indent; **bold** and *italic* inline
    - item / 1. item     bulleted / numbered list (one item per line)
    | a | b |            pipe table; a preceding line 'Աղյուսակ N. ...' becomes its caption
    ![caption](path)     figure from a project-relative path, caption below
    > formula            centred formula line, optional '(N)' number at the end
    ```                  code block (monospace)
    [[TOC]]              Word table of contents (updated when the document is opened)
    [[PAGEBREAK]]        explicit page break
The title page is generated from TITLE below; fill in the blank fields by hand in Word.
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'thesis/hy'
OUTPUT = ROOT / 'thesis/DIPLOMA.docx'
FONT = 'GHEA Grapalat'
MONO = 'Menlo'

TITLE = dict(
    ministry='ՀԱՅԱՍՏԱՆԻ ՀԱՆՐԱՊԵՏՈՒԹՅԱՆ ԿՐԹՈՒԹՅԱՆ, ԳԻՏՈՒԹՅԱՆ, ՄՇԱԿՈՒՅԹԻ ԵՎ ՍՊՈՐՏԻ ՆԱԽԱՐԱՐՈՒԹՅՈՒՆ',
    university='_______________________________________________ (համալսարան)',
    faculty='_______________________________________________ (ֆակուլտետ / ամբիոն)',
    kind='ԱՎԱՐՏԱԿԱՆ ԱՇԽԱՏԱՆՔ',
    topic='Տեսախցիկների միջոցով տրանսպորտային միջոցների շարժման և երթևեկության հոսքի վերլուծության ծրագրային միջոցի մշակում',
    rows=[('Ուսանող՝', 'Ղազարյան Մարիամ Սարգիսի'),
          ('Մասնագիտություն՝', '_______________________________'),
          ('Գիտական ղեկավար՝', '_______________________________'),
          ('Ամբիոնի վարիչ՝', '_______________________________')],
    city='Երևան 2026',
)


def set_font(run, name=FONT, size=None, bold=None, italic=None):
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


def add_inline(paragraph, text, size=None, font=FONT):
    """Add text with **bold**, *italic* and `code` spans."""
    for part in re.split(r'(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)', text):
        if not part:
            continue
        if part.startswith('**'):
            set_font(paragraph.add_run(part[2:-2]), font, size, bold=True)
        elif part.startswith('`'):
            set_font(paragraph.add_run(part[1:-1]), MONO, (size or 12) - 2)
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            set_font(paragraph.add_run(part[1:-1]), font, size, italic=True)
        else:
            set_font(paragraph.add_run(part), font, size)


def field(paragraph, instruction):
    run = paragraph.add_run()
    for kind, text in (('begin', None), (None, instruction), ('separate', None), ('end', None)):
        if kind:
            node = OxmlElement('w:fldChar')
            node.set(qn('w:fldCharType'), kind)
        else:
            node = OxmlElement('w:instrText')
            node.set(qn('xml:space'), 'preserve')
            node.text = instruction
        run._r.append(node)


def shade(cell, color):
    node = OxmlElement('w:shd')
    node.set(qn('w:val'), 'clear')
    node.set(qn('w:fill'), color)
    cell._tc.get_or_add_tcPr().append(node)


def caption(doc, text, before=False):
    p = doc.add_paragraph(style='Caption')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if not before else WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.keep_with_next = before
    add_inline(p, text, size=11)
    return p


def table(doc, lines, title=None):
    rows = [[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    rows = [r for r in rows if not all(re.fullmatch(r':?-{2,}:?', c) for c in r)]
    aligns = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
            aligns = ['right' if c.endswith(':') and not c.startswith(':') else 'center' if c.startswith(':') and c.endswith(':') else 'left' for c in cells]
    if title:
        caption(doc, title, before=True)
    columns = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=columns)
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, values in enumerate(rows):
        cells = t.add_row().cells
        for i in range(columns):
            cell = cells[i]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            align = aligns[i] if i < len(aligns) else 'left'
            p.alignment = {'right': WD_ALIGN_PARAGRAPH.RIGHT, 'center': WD_ALIGN_PARAGRAPH.CENTER}.get(align, WD_ALIGN_PARAGRAPH.LEFT)
            text = values[i] if i < len(values) else ''
            if index == 0:
                shade(cell, 'E7EDF2')
                set_font(p.add_run(text.replace('**', '')), FONT, 10, bold=True)
            else:
                add_inline(p, text, size=10)
    trpr = t.rows[0]._tr.get_or_add_trPr()
    trpr.append(OxmlElement('w:tblHeader'))
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(0)


def figure(doc, path, text):
    image = ROOT / path
    if not image.exists():
        raise FileNotFoundError(f'Figure not found: {path}')
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(image), width=Cm(15.5))
    caption(doc, text)


def title_page(doc):
    def line(text, size=12, bold=False, before=0, after=6, align=WD_ALIGN_PARAGRAPH.CENTER):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        set_font(p.add_run(text), FONT, size, bold=bold)
        return p
    line(TITLE['ministry'], 11, True)
    line(TITLE['university'], 12, before=12)
    line(TITLE['faculty'], 12)
    line(TITLE['kind'], 18, True, before=90, after=18)
    line('Թեմա՝', 12, before=6, after=2)
    line(TITLE['topic'], 15, True, after=80)
    for label, value in TITLE['rows']:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(7)
        p.paragraph_format.space_after = Pt(8)
        set_font(p.add_run(label + ' '), FONT, 12, bold=True)
        set_font(p.add_run(value), FONT, 12)
    line('Ստորագրություն՝ ______________', 12, before=6, align=WD_ALIGN_PARAGRAPH.RIGHT)
    line(TITLE['city'], 12, before=60)


def setup(doc):
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.left_margin, section.right_margin = Cm(3), Cm(1.5)
    section.top_margin, section.bottom_margin = Cm(2), Cm(2)
    section.different_first_page_header_footer = True
    styles = doc.styles
    normal = styles['Normal']
    normal.font.name, normal.font.size = FONT, Pt(12)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    fmt = normal.paragraph_format
    fmt.line_spacing, fmt.space_after, fmt.space_before = 1.5, Pt(0), Pt(0)
    fmt.first_line_indent = Cm(1.25)
    fmt.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    fmt.widow_control = True
    rpr = normal.element.get_or_add_rPr()
    fonts = rpr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts')
        rpr.insert(0, fonts)
    for key in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
        fonts.set(qn('w:' + key), FONT)
    for attribute in list(fonts.attrib):
        if 'heme' in attribute:
            del fonts.attrib[attribute]
    for name, size, before, after in (('Heading 1', 14, 0, 12), ('Heading 2', 13, 12, 6), ('Heading 3', 12, 10, 4), ('Caption', 11, 4, 8)):
        style = styles[name]
        style.font.name, style.font.size = FONT, Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = name != 'Caption'
        style.font.italic = False
        srpr = style.element.get_or_add_rPr()
        sfonts = srpr.find(qn('w:rFonts'))
        if sfonts is None:
            sfonts = OxmlElement('w:rFonts')
            srpr.insert(0, sfonts)
        for key in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
            sfonts.set(qn('w:' + key), FONT)
        for attribute in list(sfonts.attrib):
            if 'heme' in attribute:
                del sfonts.attrib[attribute]
        pf = style.paragraph_format
        pf.space_before, pf.space_after = Pt(before), Pt(after)
        pf.first_line_indent = Cm(0)
        pf.line_spacing = 1.15 if name != 'Caption' else 1.0
        pf.keep_with_next = name != 'Caption'
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER if name in ('Heading 1', 'Caption') else WD_ALIGN_PARAGRAPH.LEFT
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
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
    pending_caption = None
    first_heading = True
    i = 0
    while i < len(blocks):
        block = blocks[i].strip('\n')
        i += 1
        if not block.strip() or block.lstrip().startswith('<!--'):
            continue
        if block.startswith('```'):
            while not block.rstrip().endswith('```') or block.strip() == '```':
                block += '\n\n' + blocks[i]
                i += 1
            code = block.strip().strip('`').split('\n', 1)[1] if '\n' in block else ''
            for line in code.rstrip('`').rstrip().split('\n'):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.left_indent = Cm(0.8)
                p.paragraph_format.line_spacing = 1.0
                set_font(p.add_run(line), MONO, 9)
            doc.add_paragraph().paragraph_format.space_after = Pt(0)
            continue
        if block.strip() == '[[TOC]]':
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Cm(0)
            field(p, 'TOC \\o "1-3" \\h \\z \\u')
            continue
        if block.strip() == '[[PAGEBREAK]]':
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            continue
        if block.startswith('# '):
            if not first_heading:
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            first_heading = False
            doc.add_heading(block[2:].strip(), level=1)
            continue
        if block.startswith('## '):
            doc.add_heading(block[3:].strip(), level=2)
            continue
        if block.startswith('### '):
            doc.add_heading(block[4:].strip(), level=3)
            continue
        lines = block.split('\n')
        if re.match(r'^Աղյուսակ \d', lines[0]) and len(lines) > 1 and lines[1].lstrip().startswith('|'):
            table(doc, lines[1:], lines[0])
            continue
        if re.match(r'^Աղյուսակ \d', block) and i < len(blocks) and blocks[i].lstrip().startswith('|'):
            pending_caption = block
            continue
        if lines[0].lstrip().startswith('|'):
            table(doc, lines, pending_caption)
            pending_caption = None
            continue
        match = re.fullmatch(r'!\[(.*)\]\((.+)\)', block.strip())
        if match:
            figure(doc, match.group(2), match.group(1))
            continue
        if block.startswith('> '):
            for line in lines:
                p = doc.add_paragraph()
                p.paragraph_format.first_line_indent = Cm(0)
                body = line[2:].strip()
                number = re.search(r'\s+(\(\d+(\.\d+)?\))$', body)
                if number:
                    body = body[:number.start()]
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(8.25), 1)  # centre
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(16.5), 2)  # right
                    set_font(p.add_run('\t'), FONT, 12)
                    add_inline(p, body)
                    set_font(p.add_run('\t' + number.group(1)), FONT, 12)
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    add_inline(p, body)
            continue
        if all(re.match(r'^\s*(- |\d+\. )', line) for line in lines):
            for line in lines:
                numbered = re.match(r'^\s*(\d+)\. ', line)
                if numbered:  # literal numbers: Word's List Number would continue across separate lists
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(1.0)
                    p.paragraph_format.first_line_indent = Cm(-0.75)
                    set_font(p.add_run(numbered.group(1) + '.\t'), FONT, 12)
                    p.paragraph_format.tab_stops.add_tab_stop(Cm(1.0))
                else:
                    p = doc.add_paragraph(style='List Bullet')
                    p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                add_inline(p, re.sub(r'^\s*(- |\d+\. )', '', line))
            continue
        p = doc.add_paragraph()
        add_inline(p, ' '.join(line.strip() for line in lines))


def main():
    doc = Document()
    setup(doc)
    title_page(doc)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    for path in sorted(SOURCE.glob('*.md')):
        render(doc, path.read_text(encoding='utf-8'))
    for style in ('List Bullet',):
        s = doc.styles[style]
        s.font.name, s.font.size = FONT, Pt(12)
        s.paragraph_format.line_spacing = 1.5
    doc.save(OUTPUT)
    print(f'Saved {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
