"""Run against the development server: .venv/bin/python tests/browser_smoke.py."""
from io import BytesIO
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
output = root / '.runtime'
output.mkdir(exist_ok=True)
buffer = BytesIO()
Image.new('RGB', (600, 300), '#517966').save(buffer, 'PNG')
upload = {'name': 'test-image.png', 'mimeType': 'image/png', 'buffer': buffer.getvalue()}
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1, locale='pt-BR')
    exceptions = []
    page.on('pageerror', lambda error: exceptions.append(str(error)))
    page.goto('http://127.0.0.1:5000')
    page.screenshot(path=str(output / 'desktop.png'), full_page=True)
    page.locator('#location_p1').fill('Rua 2, Jardim Goiás, Goiânia')
    page.locator('#photo_p1').set_input_files(upload)
    if page.locator('#logo').count():
        page.locator('#logo').set_input_files(upload)
    page.locator('#clients').fill('150')
    page.get_by_role('button', name='+ Adicionar mais um ponto').click()
    page.get_by_role('button', name='Gerar ofício').click()
    page.locator('#feedback').filter(has_text='Ponto 2: anexe a foto da evidência.').wait_for()
    assert page.locator('#location_p1').input_value() == 'Rua 2, Jardim Goiás, Goiânia'
    assert page.locator('#photo_p1').evaluate('(el) => el.files.length') == 1
    if page.locator('#logo').count():
        assert page.locator('#logo').evaluate('(el) => el.files.length') == 1
    page.locator('#location_p2').fill('Avenida T-9, Goiânia')
    page.locator('#photo_p2').set_input_files(upload)
    page.locator('#format').select_option('zip')
    with page.expect_download() as download:
        page.get_by_role('button', name='Gerar ofício').click()
    file = download.value
    assert file.suggested_filename == 'oficio-amma.zip'
    file.save_as(str(output / file.suggested_filename))
    page.get_by_role('button', name='Remover ponto 2', exact=True).click()
    assert page.locator('.point').count() == 1
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(output / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert not exceptions, exceptions
    browser.close()
print('Browser passed: validation, data/file preservation, add/remove, ZIP download, mobile overflow, no JS errors.')
