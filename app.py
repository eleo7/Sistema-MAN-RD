from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import re
import warnings
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge

from documents import generate_docx, generate_pdf, PDF_FONT

ROOT = Path(__file__).parent
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 45 * 1024 * 1024
MODELS = {
    'palmeira': 'extirpação de uma Palmeira Imperial',
    'arvore': 'Extirpação de Árvore: com risco de queda ou contato com rede elétrica de distribuição',
}
MONTHS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def clean_image(source, *, logo=False):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(source) as original:
                if original.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('use uma imagem PNG, JPG ou WebP.')
                original.load()
                im = ImageOps.exif_transpose(original).convert('RGBA')
        if logo:
            bbox = im.getchannel('A').getbbox()
            if not bbox:
                raise ValueError('a imagem está totalmente transparente.')
            im = im.crop(bbox)
        im.thumbnail((1800, 1800))
        output = BytesIO()
        im.save(output, format='PNG')
        return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('imagem inválida ou muito grande; use PNG, JPG ou WebP.') from None


def read_data():
    errors = []
    def field(name, label, default='', required=False, limit=250):
        value = request.form.get(name, default).strip()
        if required and not value:
            errors.append(f'{label}: preencha este campo.')
        if len(value) > limit:
            errors.append(f'{label}: use no máximo {limit} caracteres.')
        if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
            errors.append(f'{label}: contém caracteres inválidos.')
        return value

    data = {
        'number': field('number', 'Número do ofício', limit=80),
        'city': field('city', 'Cidade', 'Goiânia', True, 100),
        'signer': field('signer', 'Signatário', 'Cesar Augusto Guarilha', True),
        'role': field('role', 'Cargo', 'Gerente de Manutenção e Automação RD Centro', True),
        'clients': field('clients', 'Clientes beneficiados', limit=12),
        'format': field('format', 'Formato', 'pdf'),
        'model': field('model', 'Modelo', 'palmeira'),
    }
    if data['model'] not in MODELS:
        errors.append('Selecione um modelo válido.')
    if data['format'] not in {'pdf', 'docx', 'zip'}:
        errors.append('Selecione um formato válido.')
    if data['clients'] and not re.fullmatch(r'[1-9][0-9]{0,8}', data['clients']):
        errors.append('Clientes beneficiados: informe um número inteiro positivo de até 9 dígitos.')
    try:
        parsed = date.fromisoformat(request.form.get('date', ''))
        data['date_text'] = f"{data['city']}, {parsed.day:02d} de {MONTHS[parsed.month - 1]} de {parsed.year}"
    except ValueError:
        errors.append('Data: informe uma data válida.')
    ids = request.form.getlist('point_id')
    if not 1 <= len(ids) <= 20 or len(set(ids)) != len(ids):
        errors.append('Adicione entre 1 e 20 pontos de evidência, sem duplicações.')
        ids = []
    data['points'] = []
    for index, pid in enumerate(ids, 1):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,60}', pid):
            errors.append(f'Ponto {index}: identificador inválido.')
            continue
        location = field(f'location_{pid}', f'Ponto {index}: localização', required=True, limit=2000)
        upload = request.files.get(f'photo_{pid}')
        photo = None
        if not upload or not upload.filename:
            errors.append(f'Ponto {index}: anexe a foto da evidência.')
        else:
            try:
                photo = clean_image(upload.stream)
            except ValueError as exc:
                errors.append(f'Ponto {index}: {exc}')
        data['points'].append({'location': location, 'photo': photo})
    upload = request.files.get('logo')
    local_logo = ROOT / 'assets' / 'logo.png'
    data['logo'] = None
    source = upload.stream if upload and upload.filename else local_logo if local_logo.exists() else None
    if source is None:
        errors.append('Logo: anexe o logo da Equatorial Energia para compor o cabeçalho.')
    else:
        try:
            data['logo'] = clean_image(source, logo=True)
        except ValueError as exc:
            errors.append(f'Logo: {exc}')
    if errors:
        return None, errors
    data['excerpt'] = MODELS[data['model']]
    return data, []


@app.get('/')
def index():
    return render_template('index.html', today=datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat(), has_logo=(ROOT / 'assets' / 'logo.png').exists(), exact_font=PDF_FONT == 'TimesNewRoman')


@app.get('/health')
def health():
    return jsonify(status='ok')


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    return jsonify(errors=['Os anexos excedem 45 MB. Reduza o tamanho das fotos e tente novamente.']), 413


@app.post('/generate')
def generate():
    data, errors = read_data()
    if errors:
        return jsonify(errors=errors), 422
    output_format = data['format']
    if output_format == 'pdf':
        content, mime = generate_pdf(data), 'application/pdf'
    elif output_format == 'docx':
        content, mime = generate_docx(data), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('oficio-amma.pdf', generate_pdf(data))
            archive.writestr('oficio-amma.docx', generate_docx(data))
        content, mime = buffer.getvalue(), 'application/zip'
    return send_file(BytesIO(content), mimetype=mime, as_attachment=True, download_name=f'oficio-amma.{output_format}', max_age=0)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
