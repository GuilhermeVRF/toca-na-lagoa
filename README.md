# 🏠 Toca na Lagoa

Monitor pessoal de apartamentos para alugar na região da **Pampulha, em Belo Horizonte**.

Criei este projeto para uso próprio, para encontrar meu apartamento em BH: em vez de abrir
QuintoAndar, ZAP, VivaReal e Netimóveis várias vezes por dia, o app faz isso por mim, junta tudo
num painel só e me avisa no Telegram quando aparece algo novo ou quando um favorito muda.

> Projeto pessoal e sem fins comerciais. Ele consulta poucas vezes por dia as mesmas buscas
> públicas que eu faria no navegador, com pausa entre as requisições.

## O que ele faz

- **Busca em 4 portais** — QuintoAndar, ZAP Imóveis, VivaReal e Netimóveis — filtrando por
  bairros, número de quartos, área máxima e **faixa de preço** (valor total = aluguel +
  condomínio + IPTU).
- **Junta anúncios repetidos**: o mesmo apartamento anunciado em mais de um site vira um card só,
  com links para as outras cópias (no máximo uma cópia por site).
- **Histórico de preço** de cada anúncio.
- **Alertas no Telegram**:
  - apartamentos **novos** que batem com a busca;
  - **favoritos**: avisa quando um favorito **sai do ar** (provavelmente alugado), **volta** a ser
    anunciado ou **muda de preço** — mesmo que saia da faixa de preço.
- **Painel reativo**: filtros, favoritos e configurações atualizam sem recarregar a página, e a
  lista se atualiza sozinha quando uma verificação agendada termina.
- **Tela de login** com senha única; a sessão fica salva no navegador por 30 dias.
- **Verificações agendadas** todos os dias nos horários escolhidos (padrão 08:00, 14:00 e 20:00),
  além do botão "Verificar agora".

## Stack

| Parte | Tecnologia |
|---|---|
| API e agendador | Python 3.12, FastAPI, SQLModel (SQLite), APScheduler, httpx |
| Front-end | Vue 3 (SFC + `<script setup>`), Vite, Tailwind CSS |
| Testes | pytest + respx (backend), Vitest (front-end) |
| Deploy | Docker multi-stage, Railway |

### Organização

```
app/                    API FastAPI
├── api.py              rotas JSON (finas: só orquestram)
├── auth.py             login por senha e cookie de sessão assinado
├── schemas.py          entrada/saída e validação (mensagens em português)
├── monitor.py          rotina de verificação: busca, guarda, agrupa e alerta
├── sources/            um coletor por portal
├── dedup.py            agrupamento do mesmo apartamento entre portais
├── views.py            montagem dos cards da listagem
└── scheduler.py        agendamento das verificações
frontend/src/           app Vue, em camadas (SOLID)
├── core/               cliente HTTP, chaves de injeção, formatação
├── services/           um serviço por recurso da API (recebe o cliente HTTP por injeção)
├── stores/             estado compartilhado: toasts, roteador, status do monitor
├── config/             filtros e ícones declarativos (novo filtro = nova entrada)
└── components/         componentes pequenos, cada um com uma responsabilidade
```

Só o `frontend/src/main.js` cria dependências; os componentes recebem o que precisam via
`provide`/`inject`, o que permite testar os serviços com um cliente HTTP falso.

## Rodando localmente

Pré-requisitos: Python 3.12+ e Node 22+.

```bash
# backend
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# front-end
cd frontend && npm ci && npm run build && cd ..

# app em http://localhost:47835
.venv/bin/uvicorn app.main:app --port 47835
```

Para mexer no front-end com recarga automática, deixe o backend rodando na porta 47835 e rode
`npm run dev` em `frontend/` (o Vite repassa `/api` para o backend).

### Testes

```bash
.venv/bin/pytest          # backend
cd frontend && npm test   # front-end
```

## Docker

O `Dockerfile` compila o front-end num estágio Node e copia só o resultado para a imagem Python.

```bash
docker compose up -d --build   # ou: podman compose up -d --build
```

O app fica em `http://127.0.0.1:47835` e os dados num volume (`/app/data`).

## Deploy no Railway

O serviço roda continuamente: o painel web e o agendador das verificações ficam no mesmo
processo, e o banco SQLite fica num volume.

1. Crie um projeto a partir deste repositório (o `railway.json` usa o `Dockerfile` e o
   healthcheck em `/healthz`).
2. Adicione um **volume** montado em `/app/data`.
3. Configure as variáveis:
   - `APP_PASSWORD` — **obrigatória numa URL pública**; é a senha da tela de login (trocá-la
     encerra todas as sessões abertas);
   - `RAILWAY_RUN_UID=0` — permite gravar no volume, que o Railway monta como root;
   - `TZ=America/Sao_Paulo` — já vem no `Dockerfile`.
4. Gere um domínio, abra o painel e configure bairros, faixa de preço, horários e o Telegram em
   **Configurações**.

## Configuração do Telegram

Na tela de Configurações há um passo a passo: crie um bot com o
[@BotFather](https://t.me/BotFather), cole o token, envie `/start` para o bot, clique em
**Detectar chat** e depois em **Enviar teste**. O token fica só no banco e nunca é devolvido pela
API.

## Variáveis de ambiente

| Variável | Padrão | Uso |
|---|---|---|
| `APP_PASSWORD` | vazio (sem login) | Senha da tela de login |
| `DATA_DIR` | `./data` | Pasta do banco SQLite |
| `FRONTEND_DIST` | `./frontend/dist` | Pasta do front-end compilado |
| `TZ` | `America/Sao_Paulo` | Fuso dos horários de verificação |
| `PORT` | `8080` (no container) | Porta HTTP, definida pelo Railway |
