"""Build the thesis from prose and measured experiment files.

Run with the Codex bundled document Python runtime, then render and inspect.
"""
import json
import re
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]


def shade(cell,color):
    node = OxmlElement('w:shd')
    node.set(qn('w:fill'),color)
    cell._tc.get_or_add_tcPr().append(node)


def table(doc,headers,rows,widths):
    t = doc.add_table(rows=1,cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i,width in enumerate(widths):
        t.columns[i].width = Inches(width)
    borders = OxmlElement('w:tblBorders')
    for name in ['top','left','bottom','right','insideH','insideV']:
        border = OxmlElement('w:'+name)
        for key,value in [('val','single'),('sz','4'),('color','D9D9D9')]:
            border.set(qn('w:'+key),value)
        borders.append(border)
    t._tbl.tblPr.append(borders)
    repeat = OxmlElement('w:tblHeader')
    t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for i,text in enumerate(headers):
        t.rows[0].cells[i].text = text
        shade(t.rows[0].cells[i],'E7EDF2')
    for values in rows:
        cells = t.add_row().cells
        for i,value in enumerate(values):
            cells[i].text = str(value)
    for row in t.rows:
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        for i,cell in enumerate(row.cells):
            cell.width = Inches(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            margins = OxmlElement('w:tcMar')
            for edge in ['top','bottom','left','right']:
                node = OxmlElement('w:'+edge)
                node.set(qn('w:w'),'100')
                node.set(qn('w:type'),'dxa')
                margins.append(node)
            cell._tc.get_or_add_tcPr().append(margins)
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing = 1.1
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.space_before = Pt(3)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.font.size = Pt(10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure(doc,path,caption):
    path = ROOT/path
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path),width=Inches(5.8))
        p = doc.add_paragraph(caption)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.1
        for r in p.runs:
            r.font.size = Pt(10)


def experiment_section(doc,runs):
    doc.add_heading('5 Экспериментальные результаты',level=1)
    doc.add_heading('5.1 Обучение детектора',level=2)
    doc.add_paragraph('Пилотное сравнение выполнено на 1024 изображениях train при размере входа 416, batch 8 и 15 эпохах. Для обеих инициализаций использованы одинаковые выборки и seed 42. Это сопоставление относится к ограниченному бюджету, а не к полностью сошедшимся моделям.')
    full = [r for r in runs if 'full' in r['name']]
    for r in full:
        doc.add_paragraph(f"Основной запуск {r['name']} использует полный подготовленный train из 6469 изображений. Инициализация: {r['initialization']}. Завершено {r['epochs_completed']} эпох из {r['epochs_requested']}; размер входа {r['imgsz']}, batch {r['batch']}, устройство {r['device']}. Время обучения {r['training_seconds']/60:.1f} минуты. Проверочная и тестовая выборки совпадают с пилотным экспериментом.")
        doc.add_paragraph(f"На test получены mAP50 {r['test']['metrics/mAP50(B)']:.4f} и mAP50–95 {r['test']['metrics/mAP50-95(B)']:.4f}. Precision составляет {r['test']['metrics/precision(B)']:.4f}, recall — {r['test']['metrics/recall(B)']:.4f}. Эти значения характеризуют библиотечную оценку подготовленной задачи и не являются точностью учета физических машин.")
        if r.get('elapsed_time_note'):
            doc.add_paragraph('Зафиксированная длительность основного запуска включает длительные перерывы. Она не характеризует непрерывную вычислительную производительность и не сопоставима напрямую с временем пилотных запусков.')
    if not full:
        doc.add_paragraph('Основной запуск на полном корпусе еще выполняется. Его показатели не включены в таблицу до завершения оценки.')
    labels = {'vehicle-scratch-pilot':'С нуля pilot','vehicle-finetune-pilot':'COCO pilot','vehicle-finetune-full':'COCO full'}
    table(doc,['Запуск','Precision','Recall','mAP50','mAP50–95'],[
        [labels.get(r['name'],r['name']),*['%.4f'%r['test'][k] for k in ['metrics/precision(B)','metrics/recall(B)','metrics/mAP50(B)','metrics/mAP50-95(B)']]] for r in runs],[1.65,1.0,1.0,1.0,1.15])
    doc.add_paragraph('В пилотном эксперименте дообучение дает более высокие mAP50 и mAP50–95, однако абсолютные значения остаются низкими. Один seed и ограниченное число эпох не определяют максимальные возможности архитектуры. Различия основного и пилотного запусков включают объем train и размер входа; изменение качества нельзя приписывать только одному из этих факторов.')
    figure(doc,'reports/model-comparison.png','Рисунок 2 Тестовые метрики завершенных экспериментов')
    if runs:
        best = max(runs,key=lambda r:r['validation']['metrics/mAP50-95(B)'])
        doc.add_paragraph(f"Рекомендуемая модель выбрана по validation mAP50–95: {best['name']}, значение {best['validation']['metrics/mAP50-95(B)']:.4f}. Тестовые значения не используются для выбора. Метрики категорий этой модели приведены ниже.")
        table(doc,['Класс','Precision','Recall','mAP50','mAP50–95'],[[name,*[f'{m[k]:.4f}' for k in ['precision','recall','mAP50','mAP50_95']]] for name,m in best['test_by_class'].items()],[1.65,1.0,1.0,1.0,1.15])
        figure(doc,Path(best['training_directory'])/'results.png','Рисунок 3 Изменение потерь и проверочных метрик рекомендуемой модели')
    doc.add_heading('5.2 Проверка транспортных событий',level=2)
    counting = [json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('counting-*.json'))]
    if counting:
        table(doc,['Запуск','Событий','Совпало','Пропуск','Лишние'],[[c['name'],c['observed_total'],c['temporal_event_check']['matched_events'],len(c['temporal_event_check']['unmatched_reference_events']),len(c['temporal_event_check']['unmatched_predicted_events'])] for c in counting],[2.4,.8,.9,.8,.9])
    doc.add_paragraph('Первый дорожный пример длится 21.52 секунды и содержит предварительный ориентир из десяти пересечений. В исходном пилотном дообучении общий счет десять сопровождался девятью совпадениями, одним пропуском и одним лишним событием. Пропуск первого грузовика и позднее повторное обнаружение другого грузовика компенсировались в сумме. Это подтверждает необходимость проверки отдельных событий.')
    doc.add_paragraph('Модификация отслеживания оценивается на том же разработочном примере, поэтому ее результат не является независимой тестовой оценкой. Сравнение полного детектора с исходным и доработанным отслеживанием использует одинаковое видео, линию, порог и веса. Значения берутся из сохраненных таблиц событий. Визуальный ориентир подготовлен ассистентом и требует подтверждения человеком.')
    if (ROOT/'reports/counting-full-baseline.json').exists() and (ROOT/'reports/counting-full-continuity.json').exists():
        baseline = json.loads((ROOT/'reports/counting-full-baseline.json').read_text())
        continuity = json.loads((ROOT/'reports/counting-full-continuity.json').read_text())
        doc.add_paragraph(f"Стандартный вариант дал {baseline['temporal_event_check']['matched_events']} совпадений, экспериментальный — {continuity['temporal_event_check']['matched_events']}. Дополнительные правила не обеспечили улучшения на этом примере. В пользовательском интерфейсе и CLI стандартное отслеживание выбрано по умолчанию; модификация оставлена отдельным исследовательским режимом. Вывод ограничен предварительной разметкой разработочного ролика.")
    for path in sorted((ROOT/'outputs').glob('demo-full*/summary.json')):
        r = json.loads(path.read_text())
        doc.add_paragraph(f"Запуск {path.parent.name}: {r['crossings']} пересечений, направление к нижнему краю {r['by_direction'].get('negative_to_positive',0)}, к верхнему краю {r['by_direction'].get('positive_to_negative',0)}. Скорость текущего запуска {r['processing_fps']:.2f} кадра/с; это измерение полного конвейера с записью видео.")
    doc.add_heading('5.3 Дополнительный видеопример и ограничения',level=2)
    second = ROOT/'outputs/demo-full-second/summary.json'
    if second.exists():
        r = json.loads(second.read_text())
        doc.add_paragraph(f"Дополнительно обработан второй пример Roboflow Supervision vehicles-2.mp4, ранее не использовавшийся для доработки правил. Его длительность {r['duration_seconds']:.2f} секунды, число кадров {r['frames']}, разрешение 1920 на 1080. Получено {r['crossings']} событий. Этот запуск проверяет выполнение конвейера на другой записи; без независимой разметки число событий не является оценкой точности.")
        baseline_path = ROOT/'outputs/demo-full-second-baseline/summary.json'
        if baseline_path.exists():
            baseline = json.loads(baseline_path.read_text())
            doc.add_paragraph(f"Экспериментальный режим второго примера создал {r['tracked_ids']} ID и {r['crossings']} событий; стандартный — {baseline['tracked_ids']} ID и {baseline['crossings']} событий. Эти величины нельзя отождествлять с числом физических автомобилей. Без разметки сравнение сумм не определяет лучший режим. Реальный временной масштаб исходной съемки, включая возможное ускорение или монтаж, не подтвержден. Пересчет по длительности файла не является подтвержденной интенсивностью реального дорожного потока.")
    doc.add_paragraph('Нельзя делать вывод о надежности в реальном городе по одной сцене и адаптированному VisDrone. Выборки не дают независимого контроля погодных условий и камер, а точная дедупликация не удаляет все похожие сцены. Разметка подсчета пока предварительная. Физическая скорость и дорожная плотность не измерены. Программная работоспособность и статистическая обоснованность точности имеют разные границы.')


def main():
    runs = [json.loads(p.read_text()) for p in sorted((ROOT/'reports').glob('vehicle-*.json'))]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width,sec.page_height = Inches(8.5),Inches(11)
    sec.left_margin,sec.right_margin = Inches(1),Inches(.8)
    sec.top_margin,sec.bottom_margin = Inches(.8),Inches(.7)
    sec.different_first_page_header_footer = True
    normal = doc.styles['Normal']
    normal.font.name = 'Times New Roman'
    normal.font.size = Pt(12)
    normal.font.color.rgb = RGBColor(0,0,0)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True
    for name,size in [('Title',20),('Subtitle',14),('Heading 1',15),('Heading 2',13)]:
        s = doc.styles[name]
        s.font.name = 'Times New Roman'
        s.font.size = Pt(size)
        s.font.color.rgb = RGBColor(0,0,0)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.space_before = Pt(14)
        s.paragraph_format.space_after = Pt(8)
        s.font.underline = False
    # Remove inherited template rules and theme font overrides.
    for element in doc.styles.element.iter():
        if element.tag == qn('w:pBdr'):
            element.getparent().remove(element)
        if element.tag == qn('w:rFonts'):
            for attribute in list(element.attrib):
                if 'Theme' in attribute or 'theme' in attribute:
                    del element.attrib[attribute]
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'),'PAGE')
    footer._p.append(field)
    p = doc.add_paragraph('Дипломная работа','Subtitle')
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('Разработка программного средства анализа движения транспорта по видеозаписям','Title')
    doc.add_paragraph('Сверточная нейронная сеть и анализ транспортного потока','Subtitle')
    p = doc.add_paragraph('Тема задания')
    p.paragraph_format.space_before = Pt(18)
    p = doc.add_paragraph('CNN- Տեսաշարերի միջոցով տրանսպորտային միջոցների շարժման և երթևկության հոսքի վերլուծության ծրագրային միջոցի մշակում')
    for r in p.runs:
        r.font.name = 'Arial'
        r.font.size = Pt(12)
    doc.add_paragraph('Реализация на Python')
    doc.add_paragraph('Автор ____________________________________')
    doc.add_paragraph('Руководитель ______________________________')
    doc.add_paragraph('Учебное заведение _________________________')
    doc.add_paragraph('2026')
    doc.add_page_break()
    doc.add_heading('Содержание',level=1)
    for text in ['Аннотация','Введение','1 Анализ задачи и методов','2 Подготовка корпуса','3 Проектирование и реализация','4 Протокол экспериментальной проверки','5 Экспериментальные результаты','6 Руководство пользователя','Заключение','Список использованных источников','Приложение А Состав экспортируемых данных','Приложение Б Воспроизведение экспериментов']:
        doc.add_paragraph(text)
    doc.add_page_break()
    text = (ROOT/'thesis/CHAPTERS.md').read_text()
    for block in text.split('\n\n'):
        block = block.strip()
        if not block or block.startswith('# '):
            continue
        if block.startswith('## 6 '):
            experiment_section(doc,runs)
        if block.startswith('### '):
            doc.add_heading(block[4:],level=2)
            if block.startswith('### 2.4 '):
                figure(doc,'reports/class-distribution-full.png','Рисунок 1 Распределение рамок по классам полного train')
        elif block.startswith('## '):
            doc.add_heading(block[3:],level=1)
            if block == '## Заключение':
                full = next((r for r in runs if r['name'] == 'vehicle-finetune-full'),None)
                if full:
                    doc.add_paragraph(f"Основной опыт завершен на полном train из 6469 изображений. Тестовые mAP50 и mAP50–95 составили {full['test']['metrics/mAP50(B)']:.4f} и {full['test']['metrics/mAP50-95(B)']:.4f}. Результат измерен после десяти эпох дообучения; он не устанавливает предельное качество модели или надежность на другой камере.")
        else:
            doc.add_paragraph(re.sub(r'\s*\n\s*',' ',block))
    doc.add_heading('Приложение А Состав экспортируемых данных',level=1)
    table(doc,['Файл','Назначение'],[
        ['annotated.mp4','Видео с рамками, траекториями и счетом'],
        ['crossings.csv','Кадр, время, ID, класс и направление события'],
        ['tracks.csv','Покадровые координаты, уверенность и два ID'],
        ['tracks_summary.csv','Длительность, путь и смещение в пикселях'],
        ['frame_stats.csv','Число видимых объектов и накопленный счет'],
        ['summary.json','Параметры запуска и агрегированная статистика'],
        ['tracker.yaml','Параметры межкадрового сопоставления'],
        ['progress.json','Последний доступный прогресс обработки']],[1.8,4.0])
    doc.add_heading('Приложение Б Воспроизведение экспериментов',level=1)
    doc.add_paragraph('Команды ниже выполняются из корня проекта в установленном виртуальном окружении. При повторном запуске требуется новое имя эксперимента и новый каталог вывода. Для компьютера без MPS выбирается CPU; время и воспроизводимость могут отличаться.')
    commands = [
        'python scripts/download_data.py',
        'python scripts/prepare_visdrone.py --pilot-size 1024',
        'python scripts/run_experiment.py --name vehicle-scratch-repeat --scratch --epochs 15 --imgsz 416 --batch 8 --device mps',
        'python scripts/run_experiment.py --name vehicle-finetune-repeat --epochs 15 --imgsz 416 --batch 8 --device mps',
        'python scripts/run_experiment.py --name vehicle-full-repeat --data configs/visdrone-vehicles.yaml --epochs 10 --imgsz 640 --batch 8 --device mps',
        'python -m unittest discover -s tests -v',
        'python scripts/make_report.py',
        'python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501']
    for command in commands:
        p = doc.add_paragraph(command)
        p.paragraph_format.line_spacing = 1.1
        p.paragraph_format.space_after = Pt(9)
        for run in p.runs:
            run.font.name = 'Courier New'
            run.font.size = Pt(10)
    doc.core_properties.title = 'Анализ движения транспорта по видеозаписям с использованием CNN'
    doc.core_properties.subject = 'Дипломная работа и экспериментальные результаты'
    path = ROOT/'thesis/DIPLOMA.docx'
    doc.save(path)
    print(path)


if __name__ == '__main__':
    main()
