# Manutenção RD - GYN

Criador: **Leonardo de Souza Neres**.

Sistema web com o módulo **Gerador de Ofício AMMA**. Gera PDF, Word (.docx) ou um ZIP com ambos, usando o mesmo modelo de conteúdo. Interface em português, responsiva, com localização e foto por ponto, assinatura editável e clientes beneficiados opcionais.

## Executar

Requer Python 3.12 (versão usada na validação).

```bash
cd /workspace/Sistema-MAN-RD
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python app.py
```

O servidor de desenvolvimento escuta na porta 5000. `GET /health` informa a disponibilidade. Não precisa de banco de dados, credenciais ou serviços externos. Fotos e documentos são processados em memória e não são persistidos no servidor. O formulário preserva os campos e arquivos após erros de validação, enquanto a página permanecer aberta.

## Identidade visual do documento

- **Logo oficial:** adicione `assets/logo.png` ou anexe-o no formulário. O repositório inicial não continha esse arquivo. O sistema exige um logo para gerar o documento, remove bordas transparentes e o repete em todas as páginas. Não inclui um logo fictício.
- **Times New Roman:** o DOCX define Times New Roman, tamanho 11, espaçamento 1,5 e corpo justificado. Para incorporá-la também ao PDF, disponibilize arquivos licenciados `assets/fonts/times.ttf` e `assets/fonts/timesbd.ttf` e reinicie o servidor. Sem esses arquivos, o PDF incorpora Liberation Serif (licença SIL OFL, incluída), com métricas compatíveis com Times New Roman. Essa substituição é uma limitação conhecida frente ao requisito da fonte exata.
- Cabeçalho e rodapé são repetidos; fotografias mantêm suas proporções. Um ofício curto com um ponto cabe em uma página. Conteúdo longo ocupa mais páginas. A paginação do Word pode variar conforme a fonte instalada e o aplicativo utilizado para abrir o arquivo.

## Validações

Localização e foto são obrigatórias em cada ponto. Até 20 pontos, imagens PNG/JPG/WebP e requisição total de até 45 MB. Cidade, data, signatário e cargo são obrigatórios. Quantidade de clientes aceita inteiro positivo de até nove dígitos e é omitida do documento quando vazia. Número do ofício é opcional.

```bash
.venv/bin/python -m pytest -q
# Com o servidor iniciado e Chromium disponível em /usr/bin/chromium:
.venv/bin/python tests/browser_smoke.py
```

Os testes cobrem conteúdo dos dois formatos, negrito da quantidade, paginação PDF, cabeçalho/rodapé, recorte transparente, entradas inválidas e ZIP. O teste de navegador cobre inclusão/remoção, erros sem perda de dados e arquivos, download e ausência de overflow em celular. Os anexos sintéticos são usados somente pelos testes; seus resultados ficam em `.runtime/`, ignorada pelo Git. A paginação visual do DOCX não foi validada em Microsoft Word ou LibreOffice nesta máquina.

## Estrutura

- `app.py`: servidor, validação e tratamento das imagens.
- `documents.py`: conteúdo compartilhado e renderização PDF/DOCX.
- `templates/index.html`, `static/`: interface.
- `requirements.lock`: versões completas usadas na validação, incluindo ferramentas de teste.

O comando acima inicia um servidor de desenvolvimento. A publicação de um serviço de produção requer um servidor WSGI e a configuração de hospedagem correspondente.

## Usar no GitHub Codespaces

No repositório GitHub, abra **Code → Codespaces → Create codespace on main**. A configuração `.devcontainer/devcontainer.json` instala as dependências e inicia a aplicação automaticamente. Após o preparo, abra a aba **Ports** e use **Open in Browser** na porta **5000**. Mantenha a visibilidade da porta privada para uso pessoal.

Para reiniciar manualmente: `bash .devcontainer/start.sh`. Os logs ficam em `.runtime/server.log`. Um Codespace é um ambiente de desenvolvimento e está sujeito à cota e cobrança da conta GitHub; não equivale a hospedagem permanente.
