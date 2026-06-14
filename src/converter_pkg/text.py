from docx.enum.text import WD_ALIGN_PARAGRAPH
from pylatex import NoEscape

from .utils import (
    get_effective_paragraph_format_value,
    get_effective_run_property,
    get_list_kind,
    get_list_line_alignment_info,
    get_paragraph_alignment,
    get_run_text_with_page_break_markers,
    get_style_paragraph_format_value,
    latex_special_chars,
    paragraph_has_manual_page_break,
    paragraph_has_rendered_page_break,
)


PARAGRAPH_FORMAT_FIELDS = {
    'left_indent': 'Отступ слева',
    'right_indent': 'Отступ справа',
    'first_line_indent': 'Отступ первой строки',
    'space_before': 'Интервал перед',
    'space_after': 'Интервал после',
    'line_spacing': 'Межстрочный интервал',
    'line_spacing_rule': 'Правило межстрочного интервала',
    'keep_together': 'Не разрывать абзац',
    'keep_with_next': 'Не отрывать от следующего',
    'widow_control': 'Запрет висячих строк',
}


def are_runs_similar(run1, run2, paragraph=None):
    for field_name in ('bold', 'italic', 'underline', 'name', 'size'):
        value1 = get_effective_run_property(run1, paragraph, field_name)
        value2 = get_effective_run_property(run2, paragraph, field_name)
        if value1 != value2:
            return False

    return True


def merge_similar_runs(paragraph):
    if len(paragraph.runs) <= 1:
        return paragraph

    merged_text = []
    current_run = None

    for run in paragraph.runs:
        run_text = get_run_text_with_page_break_markers(run)
        if current_run is None:
            current_run = run
            merged_text.append(run_text)
        elif are_runs_similar(current_run, run, paragraph):
            merged_text[-1] += run_text
        else:
            current_run = run
            merged_text.append(run_text)

    return merged_text


def format_runs_in_paragraph(paragraph, escape_func):
    text = ''

    merged_runs = []
    current_text = ''
    current_run = None

    for run in paragraph.runs:
        run_text = get_run_text_with_page_break_markers(run)
        if current_run is None:
            current_run = run
            current_text = run_text
        elif are_runs_similar(current_run, run, paragraph):
            current_text += run_text
        else:
            merged_runs.append((current_text, current_run))
            current_run = run
            current_text = run_text

    if current_run is not None:
        merged_runs.append((current_text, current_run))

    for run_text, run in merged_runs:
        bold = get_effective_run_property(run, paragraph, 'bold')
        italic = get_effective_run_property(run, paragraph, 'italic')
        underline = get_effective_run_property(run, paragraph, 'underline')

        if not run_text.strip():
            run_text = escape_func(run_text)
        else:
            run_text = escape_func(run_text)
            if bold and italic:
                run_text = f'\\textbf{{\\textit{{{run_text}}}}}'
            elif bold:
                run_text = f'\\textbf{{{run_text}}}'
            elif italic:
                run_text = f'\\textit{{{run_text}}}'
            elif underline:
                run_text = f'\\underline{{{run_text}}}'

        font_name, font_name_source = get_effective_run_property(run, paragraph, 'name', include_source=True)
        font_size, font_size_source = get_effective_run_property(run, paragraph, 'size', include_source=True)
        bold_source = get_effective_run_property(run, paragraph, 'bold', include_source=True)[1]
        italic_source = get_effective_run_property(run, paragraph, 'italic', include_source=True)[1]
        underline_source = get_effective_run_property(run, paragraph, 'underline', include_source=True)[1]

        if font_size is not None and hasattr(font_size, 'pt'):
            font_size = font_size.pt

        line_spacing, line_spacing_source = get_effective_paragraph_format_value(
            paragraph, 'line_spacing', include_source=True
        )
        line_spacing_rule, line_spacing_rule_source = get_effective_paragraph_format_value(
            paragraph, 'line_spacing_rule', include_source=True
        )
        line_spacing_pt = format_line_spacing(line_spacing, line_spacing_rule)

        run_text += (
            f'% Шрифт-{font_name} Источник шрифта-{font_name_source} '
            f'Размер шрифта-{font_size} Источник размера шрифта-{font_size_source} '
            f'Жирный-{bold} Источник жирного-{bold_source} '
            f'Курсив-{italic} Источник курсива-{italic_source} '
            f'Подчеркнутый-{underline} Источник подчеркивания-{underline_source} '
            f'Межстрочный интервал-{line_spacing_pt} Источник межстрочного интервала-{line_spacing_source} '
            f'Правило-{line_spacing_rule} Источник правила-{line_spacing_rule_source} %\n'
        )

        text += run_text

    return text


def format_length_cm(value):
    if value is None:
        return None

    if hasattr(value, 'cm'):
        return round(value.cm, 2)

    return value


def format_length_pt(value):
    if value is None:
        return None

    if hasattr(value, 'pt'):
        return round(value.pt, 2)

    return value


def format_line_spacing(value, line_spacing_rule=None):
    if value is None:
        return None

    if hasattr(value, 'pt'):
        return round(value.pt, 2)

    if isinstance(value, (int, float)):
        rule_value = getattr(line_spacing_rule, 'value', line_spacing_rule)
        if rule_value in [3, 4]:
            return round(value / 12700, 2)
        return value

    return str(value)


def format_value_for_metadata(field_name, value):
    if field_name in {'space_before', 'space_after'}:
        formatted_value = format_length_pt(value)
        unit = 'пт' if formatted_value is not None else ''
    elif field_name in {'left_indent', 'right_indent', 'first_line_indent'}:
        formatted_value = format_length_cm(value)
        unit = 'см' if formatted_value is not None else ''
    elif field_name == 'line_spacing':
        formatted_value = format_line_spacing(value)
        unit = ''
    else:
        formatted_value = value
        unit = ''

    return f'{formatted_value}{unit}'


def format_paragraph_metadata_comment(paragraph, paragraph_type='Абзац', level=None):
    style_name = getattr(getattr(paragraph, 'style', None), 'name', None)
    alignment, alignment_source = get_paragraph_alignment(paragraph, include_source=True)

    metadata = [
        f'Тип-{paragraph_type}',
        f'Стиль-{style_name}',
    ]
    if level is not None:
        metadata.append(f'Уровень-{level}')

    metadata.append(f'Выравнивание-{alignment}')
    metadata.append(f'Источник выравнивания-{alignment_source}')

    for field_name, label in PARAGRAPH_FORMAT_FIELDS.items():
        value, source = get_effective_paragraph_format_value(paragraph, field_name, include_source=True)
        metadata.append(f'{label}-{format_value_for_metadata(field_name, value)}')
        metadata.append(f'Источник {label}-{source}')

    local_page_break = getattr(paragraph.paragraph_format, 'page_break_before', None)
    style_page_break, style_page_break_source = get_style_paragraph_format_value(
        paragraph, 'page_break_before'
    )
    effective_page_break, effective_page_break_source = get_effective_paragraph_format_value(
        paragraph, 'page_break_before', include_source=True
    )

    metadata.append(f'Ручной разрыв страницы-{paragraph_has_manual_page_break(paragraph)}')
    metadata.append(f'Разрыв страницы Word-{paragraph_has_rendered_page_break(paragraph)}')
    metadata.append(f'Перенос на новую страницу локально-{local_page_break}')
    metadata.append(f'Перенос на новую страницу в стиле-{style_page_break}')
    metadata.append(f'Источник переноса в стиле-{style_page_break_source}')
    metadata.append(f'Перенос на новую страницу итог-{effective_page_break}')
    metadata.append(f'Источник переноса итог-{effective_page_break_source}')

    if paragraph_type == 'Список':
        list_info = get_list_line_alignment_info(paragraph)
        if list_info is not None:
            first_line = list_info.get('first_line')
            subsequent_line = list_info.get('subsequent_line')
            first_line_value = f'{first_line}см' if first_line is not None else None
            subsequent_line_value = f'{subsequent_line}см' if subsequent_line is not None else None

            metadata.append(f'Формат списка-{list_info.get("format")}')
            metadata.append(f'Шаблон маркера списка-{list_info.get("text")}')
            metadata.append(f'Выравнивание маркера списка-{list_info.get("marker_alignment")}')
            metadata.append(f'Выравнивание первой строки списка-{first_line_value}')
            metadata.append(f'Выравнивание последующих строк списка-{subsequent_line_value}')
            metadata.append(f'Источник выравнивания списка-{list_info.get("source")}')


    return f"% Формат абзаца: {' '.join(metadata)} %\n"


def parse_paragraphs(paragraphs, latex_doc, flag_itemize, flag_enumerate):

    if paragraphs.style.name.startswith("Heading"):
        if flag_itemize:
            latex_doc.append(NoEscape(r'\end{itemize}'))
            flag_itemize = False

        if flag_enumerate:
            latex_doc.append(NoEscape(r'\end{enumerate}'))
            flag_enumerate = False

        level = int(paragraphs.style.name.split()[1])
        if level == 1:
            latex_doc.append(NoEscape(f'\\section{{{latex_special_chars(paragraphs.text)}}}'))
        elif level == 2:
            latex_doc.append(NoEscape(f'\\subsection{{{latex_special_chars(paragraphs.text)}}}'))
        elif level == 3:
            latex_doc.append(NoEscape(f'\\subsubsection{{{latex_special_chars(paragraphs.text)}}}'))
        else:
            latex_doc.append(NoEscape(f'\\paragraph{{{latex_special_chars(paragraphs.text)}}}'))

        latex_doc.append(NoEscape(format_paragraph_metadata_comment(paragraphs, 'Заголовок', level)))

        return flag_itemize, flag_enumerate

    text = format_runs_in_paragraph(paragraphs, latex_special_chars)
    paragraph_metadata = format_paragraph_metadata_comment(paragraphs)

    alignment = get_paragraph_alignment(paragraphs)
    if alignment == WD_ALIGN_PARAGRAPH.LEFT:
        latex_alignment = "flushleft"
    elif alignment == WD_ALIGN_PARAGRAPH.CENTER:
        latex_alignment = 'center'
    elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
        latex_alignment = 'flushright'
    else:
        latex_alignment = 'flushleft'

    if text.strip():
        latex_doc.append(NoEscape(f'\\begin{{{latex_alignment}}}'))
        latex_doc.append(NoEscape(text))
        latex_doc.append(NoEscape(paragraph_metadata))
        latex_doc.append(NoEscape(f'\\end{{{latex_alignment}}}'))

    return flag_itemize, flag_enumerate


def parse_list_paragraphs(paragraphs, latex_doc, flag_itemize, flag_enumerate):
    text = format_runs_in_paragraph(paragraphs, latex_special_chars)
    paragraph_metadata = format_paragraph_metadata_comment(paragraphs, 'Список')
    list_kind = get_list_kind(paragraphs)

    if list_kind == 'bullet':
        if not flag_itemize:
            if flag_enumerate:
                latex_doc.append(NoEscape(r'\end{enumerate}'))
                flag_enumerate = False

            flag_itemize = True
            latex_doc.append(NoEscape(r'\begin{itemize}'))

        latex_doc.append(NoEscape(r'\item ' + text + paragraph_metadata))
    elif list_kind == 'number':
        if not flag_enumerate:
            if flag_itemize:
                latex_doc.append(NoEscape(r'\end{itemize}'))
                flag_itemize = False

            flag_enumerate = True
            latex_doc.append(NoEscape(r'\begin{enumerate}'))
        latex_doc.append(NoEscape(r'\item ' + text + paragraph_metadata))

    return flag_itemize, flag_enumerate
