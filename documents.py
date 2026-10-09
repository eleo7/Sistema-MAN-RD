"""A single document content model shared by PDF and Word renderers."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as PDFImage, KeepTogether, HRFlowable

RECIPIENT = 'Exma. Sra. Dra. Zilma Percussor'
RECIPIENT_ROLE = 'Presidente da Agência Municipal do Meio Ambiente'
SALUTATION = 'Exma. Sra. Presidente,'
EVIDENCE = 'Abaixo segue as informações de localização e evidências fotográficas.'
COMPANY = 'EQUATORIAL ENERGIA GOIÁS'
ADDRESS = 'Rua 2, Quadra A-37, Nº 651. Jardim Goiás – Goiânia - GO. CEP: 74805-108 - Fone: (62) 3623-1101'
WEBSITE = 'www.equatorialenergia.com.br'
FONT_DIR = Path(__file__).parent / 'assets' / 'fonts'
PDF_FONT = 'LiberationSerif'
pdfmetrics.registerFont(TTFont(PDF_FONT, str(FONT_DIR / 'LiberationSerif-Regular.ttf')))
pdfmetrics.registerFont(TTFont(PDF_FONT + '-Bold', str(FONT_DIR / 'LiberationSerif-Bold.ttf')))
pdfmetrics.registerFontFamily(PDF_FONT, normal=PDF_FONT, bold=PDF_FONT + '-Bold')
if (FONT_DIR / 'times.ttf').exists() and (FONT_DIR / 'timesbd.ttf').exists():
    pdfmetrics.registerFont(TTFont('TimesNewRoman', str(FONT_DIR / 'times.ttf')))
    pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', str(FONT_DIR / 'timesbd.ttf')))
    pdfmetrics.registerFontFamily('TimesNewRoman', normal='TimesNewRoman', bold='TimesNewRoman-Bold')
    PDF_FONT = 'TimesNewRoman'


def content(data):
    body = ('A EQUATORIAL GOIÁS DISTRIBUIDORA DE ENERGIA S.A., ("EQUATORIAL ENERGIA") empresa prestadora de serviços de distribuição de energia elétrica, inscrita no CNPJ/MF sob o nº 01.543.032/0001-04, com sede na Rua 2, Quadra A-37, nº 505, Edifício Gileno Godói, Bairro Jardim Goiás, Município de Goiânia, Estado de Goiás, CEP 74.805-180, vem, mui respeitosamente, através deste, solicitar apoio no processo de ')
    blocks = []
    if data['number']:
        blocks.append(('left', [('Ofício nº ' + data['number'], True)]))
    blocks.extend([
        ('right', [(data['date_text'], False)]),
        ('recipient', [(RECIPIENT, True), ('\n' + RECIPIENT_ROLE, False)]),
        ('left', [(SALUTATION, False)]),
    ])
    if len(data['points']) == 1:
        blocks.append(('justify', [(body, False), (data['excerpt'], True), (' na seguinte localização: ', False), (data['points'][0]['location'], True), ('.', False)]))
    else:
        blocks.append(('justify', [(body, False), (data['excerpt'], True), (' nas localizações indicadas abaixo.', False)]))
    if data['clients']:
        blocks.append(('justify', [('Ressalta-se que a presente intervenção beneficiará diretamente uma quantidade média de ', False), (data['clients'], True), (' clientes da região, mitigando o risco iminente de descontinuidade no fornecimento de energia elétrica.', False)]))
    blocks.append(('left', [(EVIDENCE, False)]))
    return blocks


def signature_lines(data):
    return [line for line in [data['signer'], data['qualification'], data['registration'], data['role']] if line.strip()]


def labels(index, count):
    return ('Localização:', 'Evidência fotográfica') if count == 1 else (f'Ponto {index} — Localização:', f'Evidência fotográfica — Ponto {index}')


def image_size(blob, max_width, max_height):
    with Image.open(BytesIO(blob)) as im:
        w, h = im.size
    scale = min(max_width / w, max_height / h)
    return w * scale, h * scale


def generate_pdf(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=57, rightMargin=57, topMargin=76, bottomMargin=65, title='Ofício AMMA', author=data['signer'])
    base = ParagraphStyle('body', fontName=PDF_FONT, fontSize=11, leading=16.5, spaceAfter=6, splitLongWords=True)
    styles = {name: ParagraphStyle(name, parent=base, alignment=align) for name, align in [('left', 0), ('right', TA_RIGHT), ('justify', TA_JUSTIFY), ('center', TA_CENTER)]}
    styles['recipient'] = ParagraphStyle('recipient', parent=styles['left'], spaceAfter=16.5, keepWithNext=True)
    caption = ParagraphStyle('caption', parent=styles['center'], fontSize=9, leading=13.5, spaceAfter=7)
    def markup(runs):
        return ''.join(f'<b>{escape(text)}</b>' if bold else escape(text) for text, bold in runs).replace('\n', '<br/>')
    story = [Paragraph(markup(runs), styles[align]) for align, runs in content(data)]
    for i, point in enumerate(data['points'], 1):
        label, legend = labels(i, len(data['points']))
        story.append(Paragraph(markup([(label + ' ', True), (point['location'], False)]), styles['left']))
        w, h = image_size(point['photo'], 330, 135)
        photo = PDFImage(BytesIO(point['photo']), width=w, height=h)
        story.append(KeepTogether([photo, Spacer(1, 3), Paragraph(escape(legend), caption)]))
    signature_style = ParagraphStyle('signature', parent=styles['center'], fontSize=10, leading=15, spaceAfter=0)
    signature = [Paragraph('Atenciosamente,', styles['left']), Spacer(1, 20), HRFlowable(width='85%', thickness=0.6, color='#555555', spaceAfter=4)]
    signature.extend(Paragraph(markup([(line, True)]), signature_style) for line in signature_lines(data))
    story.append(KeepTogether(signature))

    def page(canvas, _doc):
        canvas.saveState()
        w, h = image_size(data['logo'], 142, 43)
        canvas.drawImage(ImageReader(BytesIO(data['logo'])), 57, A4[1] - 23 - h, width=w, height=h, mask='auto')
        canvas.setStrokeColorRGB(.77, .81, .84)
        canvas.line(57, 56, A4[0] - 57, 56)
        foot_style = ParagraphStyle('footer', fontName=PDF_FONT, fontSize=8, leading=10, alignment=TA_CENTER)
        footer = Paragraph(f'<b>{COMPANY}</b><br/>{ADDRESS}<br/><link href="http://www.equatorialenergia.com.br/">{WEBSITE}</link>', foot_style)
        _, height = footer.wrap(A4[0] - 114, 45)
        footer.drawOn(canvas, 57, 50 - height)
        canvas.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()


def generate_docx(data):
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(2.68), Cm(2.3)
    section.left_margin = section.right_margin = Cm(2.01)
    section.header_distance, section.footer_distance = Cm(.8), Cm(.6)
    normal = doc.styles['Normal']
    normal.font.name, normal.font.size = 'Times New Roman', Pt(11)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True
    normal.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
    header = section.header.paragraphs[0]
    header.paragraph_format.space_after = Pt(0)
    header.paragraph_format.line_spacing = 1
    w, h = image_size(data['logo'], 5, 1.52)
    header.add_run().add_picture(BytesIO(data['logo']), width=Cm(w), height=Cm(h))
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.line_spacing = 1
    footer.paragraph_format.space_after = Pt(0)
    for text, bold in [(COMPANY, True), ('\n' + ADDRESS, False), ('\n' + WEBSITE, False)]:
        run = footer.add_run(text)
        run.bold, run.font.size = bold, Pt(8)
    alignments = {'left': WD_ALIGN_PARAGRAPH.LEFT, 'right': WD_ALIGN_PARAGRAPH.RIGHT, 'justify': WD_ALIGN_PARAGRAPH.JUSTIFY}
    for align, runs in content(data):
        p = doc.add_paragraph()
        p.alignment = alignments.get(align, WD_ALIGN_PARAGRAPH.LEFT)
        if align == 'recipient':
            p.paragraph_format.space_after = Pt(16.5)
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
        for text, bold in runs:
            p.add_run(text).bold = bold
    for i, point in enumerate(data['points'], 1):
        label, legend = labels(i, len(data['points']))
        p = doc.add_paragraph()
        p.add_run(label + ' ').bold = True
        p.add_run(point['location'])
        p.paragraph_format.keep_with_next = True
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1
        p.paragraph_format.keep_with_next = True
        w, h = image_size(point['photo'], 11.64, 4.76)
        p.add_run().add_picture(BytesIO(point['photo']), width=Cm(w), height=Cm(h))
        p = doc.add_paragraph(legend)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.5
        p.runs[0].font.size = Pt(9)
    p = doc.add_paragraph('Atenciosamente,')
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(26)
    lines = signature_lines(data)
    for index, line in enumerate(lines):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.keep_with_next = index < len(lines) - 1
        p.paragraph_format.keep_together = True
        run = p.add_run(line)
        run.bold = True
        run.font.size = Pt(10)
        if index == 0:
            borders = OxmlElement('w:pBdr')
            top = OxmlElement('w:top')
            for key, value in [('val', 'single'), ('sz', '5'), ('space', '4'), ('color', '555555')]:
                top.set(qn('w:' + key), value)
            borders.append(top)
            p._p.get_or_add_pPr().append(borders)
            p.paragraph_format.left_indent = Cm(1.27)
            p.paragraph_format.right_indent = Cm(1.27)
    doc.core_properties.title = 'Ofício AMMA'
    doc.core_properties.author = data['signer']
    output = BytesIO()
    doc.save(output)
    return output.getvalue()
