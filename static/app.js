const form = document.querySelector('#office-form');
const points = document.querySelector('#points');
const feedback = document.querySelector('#feedback');
const addButton = document.querySelector('#add-point');
let serial = 0;

function renumber() {
  const cards = [...points.children];
  cards.forEach((card, i) => {
    card.querySelector('.point-number').textContent = i + 1;
    const remove = card.querySelector('.remove-point');
    remove.disabled = cards.length === 1;
    remove.setAttribute('aria-label', `Remover ponto ${i + 1}`);
  });
  document.querySelector('#point-count').textContent = `${cards.length} ${cards.length === 1 ? 'ponto' : 'pontos'}`;
  addButton.disabled = cards.length >= 20;
}

function addPoint() {
  if (points.children.length >= 20) return;
  const card = document.querySelector('#point-template').content.firstElementChild.cloneNode(true);
  const id = `p${++serial}`;
  card.querySelector('[name=point_id]').value = id;
  const location = card.querySelector('textarea');
  location.name = `location_${id}`;
  location.id = location.name;
  card.querySelector('.location-label').htmlFor = location.id;
  const photo = card.querySelector('[type=file]');
  photo.name = `photo_${id}`;
  photo.id = photo.name;
  card.querySelector('.photo-label').htmlFor = photo.id;
  let previewUrl;
  photo.addEventListener('change', () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const preview = card.querySelector('img');
    preview.hidden = !photo.files.length;
    if (photo.files.length) {
      previewUrl = URL.createObjectURL(photo.files[0]);
      preview.src = previewUrl;
      preview.onerror = () => { preview.hidden = true; };
    }
  });
  card.querySelector('.remove-point').addEventListener('click', () => {
    if (points.children.length === 1) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    card.remove();
    renumber();
    addButton.focus();
  });
  points.append(card);
  renumber();
  return location;
}
addButton.addEventListener('click', () => addPoint()?.focus());
addPoint();
document.querySelector('#model').addEventListener('change', (event) => {
  document.querySelector('#model-note').textContent = event.target.value === 'palmeira'
    ? 'Solicitação de extirpação de uma Palmeira Imperial.'
    : 'Extirpação de Árvore: com risco de queda ou contato com rede elétrica de distribuição.';
});
function showFeedback(messages, success = false) {
  feedback.replaceChildren();
  feedback.classList.toggle('success', success);
  const list = document.createElement('ul');
  for (const message of messages) {
    const item = document.createElement('li');
    item.textContent = message;
    list.append(item);
  }
  feedback.append(list);
  feedback.hidden = false;
  feedback.focus();
}
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = document.querySelector('#generate');
  if (button.disabled) return;
  feedback.hidden = true;
  const payload = new FormData(form);
  button.disabled = true;
  button.querySelector('span').textContent = 'Gerando documento…';
  try {
    const response = await fetch('/generate', { method: 'POST', body: payload });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      showFeedback(body.errors || ['Não foi possível gerar o documento. Tente novamente.']);
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `oficio-amma.${payload.get('format')}`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    showFeedback(['Ofício gerado com sucesso. Confira o documento antes de enviá-lo.'], true);
  } catch {
    showFeedback(['Falha de conexão. Seus dados e anexos foram preservados; tente novamente.']);
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Gerar ofício';
  }
});
