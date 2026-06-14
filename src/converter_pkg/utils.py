from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


_ALIGNMENT_XML_MAP = {
    'start': WD_ALIGN_PARAGRAPH.LEFT,
    'end': WD_ALIGN_PARAGRAPH.RIGHT,
    'left': WD_ALIGN_PARAGRAPH.LEFT,
    'center': WD_ALIGN_PARAGRAPH.CENTER,
    'right': WD_ALIGN_PARAGRAPH.RIGHT,
    'both': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'distribute': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'mediumKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'highKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'lowKashida': WD_ALIGN_PARAGRAPH.JUSTIFY,
    'thaiDistribute': WD_ALIGN_PARAGRAPH.JUSTIFY,
}


_SOURCE_LOCAL = 'локально'


def latex_special_chars(text):
    if text is None:
        return ""

    replace_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '>': r'$>$',
        '<': r'$<$'
    }

    for char, new_char in replace_chars.items():
        text = text.replace(char, new_char)

    return text


def _safe_getattr(obj, attr_name):
    if obj is None:
        return None

    try:
        return getattr(obj, attr_name, None)
    except (AttributeError, ValueError):
        return None


def _style_source(style):
    style_name = getattr(style, 'name', None)
    if style_name:
        return f'стиль:{style_name}'
    return 'стиль'


def iter_style_chain(style):
    seen = set()
    while style is not None:
        style_key = id(style)
        if style_key in seen:
            break
        seen.add(style_key)
        yield style
        style = _safe_getattr(style, 'base_style')


def _w_val(element):
    if element is None:
        return None
    return element.get(qn('w:val'))


def _w_int_attr(element, attr_name):
    if element is None:
        return None

    raw_value = element.get(qn(f'w:{attr_name}'))
    if raw_value is None:
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _first_child(element, child_name):
    if element is None:
        return None
    return element.find(qn(f'w:{child_name}'))


def _paragraph_ppr(paragraph):
    paragraph_element = _safe_getattr(paragraph, '_p')
    return _safe_getattr(paragraph_element, 'pPr')


def _style_ppr(style):
    style_element = _safe_getattr(style, 'element')
    return _safe_getattr(style_element, 'pPr')


def _alignment_from_ppr(p_pr):
    jc = _safe_getattr(p_pr, 'jc')
    if jc is None:
        jc = _first_child(p_pr, 'jc')
    if jc is None:
        return None

    return _ALIGNMENT_XML_MAP.get(_w_val(jc))


def get_style_paragraph_format_value(paragraph, field_name):
    for style in iter_style_chain(_safe_getattr(paragraph, 'style')):
        paragraph_format = _safe_getattr(style, 'paragraph_format')
        value = _safe_getattr(paragraph_format, field_name)
        if value is not None:
            return value, _style_source(style)

    return None, None


def get_effective_paragraph_format_value(paragraph, field_name, include_source=False):
    if field_name == 'alignment':
        return get_paragraph_alignment(paragraph, include_source=include_source)

    value = _safe_getattr(_safe_getattr(paragraph, 'paragraph_format'), field_name)
    if value is not None:
        result = (value, _SOURCE_LOCAL)
        return result if include_source else value

    value, source = get_style_paragraph_format_value(paragraph, field_name)
    result = (value, source)
    return result if include_source else value


def get_paragraph_alignment(paragraph, include_source=False):
    paragraph_format = _safe_getattr(paragraph, 'paragraph_format')
    try:
        alignment = paragraph_format.alignment
    except (ValueError, AttributeError):
        alignment = None

    if alignment is None:
        alignment = _alignment_from_ppr(_paragraph_ppr(paragraph))

    if alignment is not None:
        result = (alignment, _SOURCE_LOCAL)
        return result if include_source else alignment

    for style in iter_style_chain(_safe_getattr(paragraph, 'style')):
        paragraph_format = _safe_getattr(style, 'paragraph_format')
        try:
            alignment = paragraph_format.alignment
        except (ValueError, AttributeError):
            alignment = None

        if alignment is None:
            alignment = _alignment_from_ppr(_style_ppr(style))

        if alignment is not None:
            result = (alignment, _style_source(style))
            return result if include_source else alignment

    result = (None, None)
    return result if include_source else None


def get_effective_run_property(run, paragraph, field_name, include_source=False):
    value = _safe_getattr(_safe_getattr(run, 'font'), field_name)
    if value is not None:
        result = (value, _SOURCE_LOCAL)
        return result if include_source else value

    for style in iter_style_chain(_safe_getattr(run, 'style')):
        value = _safe_getattr(_safe_getattr(style, 'font'), field_name)
        if value is not None:
            result = (value, _style_source(style))
            return result if include_source else value

    for style in iter_style_chain(_safe_getattr(paragraph, 'style')):
        value = _safe_getattr(_safe_getattr(style, 'font'), field_name)
        if value is not None:
            result = (value, _style_source(style))
            return result if include_source else value

    result = (None, None)
    return result if include_source else None


def get_run_text_with_page_break_markers(run):
    text_parts = []
    run_element = _safe_getattr(run, '_r')
    if run_element is None:
        return ''

    for child in run_element:
        if child.tag == qn('w:t'):
            text_parts.append(child.text or '')
        elif child.tag == qn('w:tab'):
            text_parts.append('\t')
        elif child.tag == qn('w:br'):
            break_type = child.get(qn('w:type'))
            if break_type == 'page':
                text_parts.append('\n[Разрыв страницы]\n')
            elif break_type == 'column':
                text_parts.append('\n[Разрыв колонки]\n')
            else:
                text_parts.append('\n')
        elif child.tag == qn('w:cr'):
            text_parts.append('\n')
        elif child.tag == qn('w:lastRenderedPageBreak'):
            text_parts.append('\n[Разрыв страницы Word]\n')

    return ''.join(text_parts)


def paragraph_has_manual_page_break(paragraph):
    paragraph_element = _safe_getattr(paragraph, '_element')
    if paragraph_element is None:
        return False

    return bool(paragraph_element.xpath('.//w:br[@w:type="page"]'))


def paragraph_has_rendered_page_break(paragraph):
    paragraph_element = _safe_getattr(paragraph, '_element')
    if paragraph_element is None:
        return False

    return bool(paragraph_element.xpath('.//w:lastRenderedPageBreak'))


def _get_num_pr_info_from_ppr(p_pr):
    num_pr = _safe_getattr(p_pr, 'numPr')
    if num_pr is None:
        num_pr = _first_child(p_pr, 'numPr')
    if num_pr is None:
        return None

    num_id_element = _first_child(num_pr, 'numId')
    if num_id_element is None:
        num_id_element = _safe_getattr(num_pr, 'numId')
    num_id = _w_val(num_id_element)

    level_element = _first_child(num_pr, 'ilvl')
    if level_element is None:
        level_element = _safe_getattr(num_pr, 'ilvl')
    level = _w_val(level_element) or '0'

    if num_id is None:
        return None

    return {
        'num_id': num_id,
        'level': level,
    }


def get_effective_numbering_info(paragraph):
    local_info = _get_num_pr_info_from_ppr(_paragraph_ppr(paragraph))
    if local_info is not None:
        local_info['source'] = _SOURCE_LOCAL
        return _extend_numbering_info(paragraph, local_info)

    for style in iter_style_chain(_safe_getattr(paragraph, 'style')):
        style_info = _get_num_pr_info_from_ppr(_style_ppr(style))
        if style_info is not None:
            style_info['source'] = _style_source(style)
            return _extend_numbering_info(paragraph, style_info)

    return None


def _extend_numbering_info(paragraph, numbering_info):
    level_element = _find_numbering_level(
        paragraph,
        numbering_info.get('num_id'),
        numbering_info.get('level') or '0',
    )
    if level_element is None:
        return numbering_info

    numbering_info['level_format'] = _w_val(_first_child(level_element, 'numFmt'))
    numbering_info['level_text'] = _w_val(_first_child(level_element, 'lvlText'))
    numbering_info['level_alignment'] = _w_val(_first_child(level_element, 'lvlJc'))

    p_pr = _first_child(level_element, 'pPr')
    ind = _first_child(p_pr, 'ind')
    left_twips = _w_int_attr(ind, 'left')
    first_line_twips = _w_int_attr(ind, 'firstLine')
    hanging_twips = _w_int_attr(ind, 'hanging')

    if left_twips is not None:
        numbering_info['subsequent_line_twips'] = left_twips
        if first_line_twips is not None:
            numbering_info['first_line_twips'] = left_twips + first_line_twips
        elif hanging_twips is not None:
            numbering_info['first_line_twips'] = left_twips - hanging_twips
        else:
            numbering_info['first_line_twips'] = left_twips

    return numbering_info


def _find_numbering_level(paragraph, num_id, level):
    if num_id is None:
        return None

    try:
        numbering = paragraph.part.numbering_part.element
    except (AttributeError, KeyError):
        return None

    num_element = None
    for candidate in numbering.findall(qn('w:num')):
        if candidate.get(qn('w:numId')) == str(num_id):
            num_element = candidate
            break
    if num_element is None:
        return None

    for override in num_element.findall(qn('w:lvlOverride')):
        if override.get(qn('w:ilvl')) == str(level):
            override_level = _first_child(override, 'lvl')
            if override_level is not None:
                return override_level

    abstract_num_id = _w_val(_first_child(num_element, 'abstractNumId'))
    if abstract_num_id is None:
        return None

    for abstract in numbering.findall(qn('w:abstractNum')):
        if abstract.get(qn('w:abstractNumId')) != str(abstract_num_id):
            continue
        for level_element in abstract.findall(qn('w:lvl')):
            if level_element.get(qn('w:ilvl')) == str(level):
                return level_element

    return None


def twips_to_cm(value):
    if value is None:
        return None
    return round(value / 1440 * 2.54, 2)


def get_list_line_alignment_info(paragraph):
    numbering_info = get_effective_numbering_info(paragraph)
    if numbering_info is not None:
        first_line = twips_to_cm(numbering_info.get('first_line_twips'))
        subsequent_line = twips_to_cm(numbering_info.get('subsequent_line_twips'))
        if first_line is not None or subsequent_line is not None:
            return {
                'first_line': first_line,
                'subsequent_line': subsequent_line,
                'marker_alignment': numbering_info.get('level_alignment'),
                'source': numbering_info.get('source'),
                'format': numbering_info.get('level_format'),
                'text': numbering_info.get('level_text'),
            }

    left_indent = get_effective_paragraph_format_value(paragraph, 'left_indent')
    first_line_indent = get_effective_paragraph_format_value(paragraph, 'first_line_indent')
    if left_indent is None and first_line_indent is None:
        return None

    left_cm = left_indent.cm if hasattr(left_indent, 'cm') else None
    first_indent_cm = first_line_indent.cm if hasattr(first_line_indent, 'cm') else 0
    first_line = round((left_cm or 0) + first_indent_cm, 2)

    return {
        'first_line': first_line,
        'subsequent_line': round(left_cm, 2) if left_cm is not None else None,
        'marker_alignment': None,
        'source': 'абзац',
        'format': None,
        'text': None,
    }


def is_list_paragraph(paragraph):
    style_name = getattr(getattr(paragraph, 'style', None), 'name', '')
    if style_name in ['List Paragraph', 'List Number', 'List Bullet']:
        return True

    return get_effective_numbering_info(paragraph) is not None


def get_list_kind(paragraph):
    numbering_info = get_effective_numbering_info(paragraph)
    if numbering_info is not None:
        if numbering_info.get('level_format') == 'bullet':
            return 'bullet'
        return 'number'

    style_name = getattr(getattr(paragraph, 'style', None), 'name', '')
    if style_name == 'List Bullet':
        return 'bullet'
    if style_name in ['List Number', 'List Paragraph']:
        return 'number'

    return None


def get_column_alignment(table, col_index):
    for row in table.rows:
        if col_index >= len(row.cells):
            continue
        cell = row.cells[col_index]
        if cell.paragraphs:
            para = cell.paragraphs[0]
            alignment = get_paragraph_alignment(para)
            if alignment is not None:
                if alignment == WD_ALIGN_PARAGRAPH.CENTER:
                    return 'c'
                elif alignment == WD_ALIGN_PARAGRAPH.RIGHT:
                    return 'r'
                else:
                    return 'l'
    return 'l'
