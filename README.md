# Bug Bounty Writeups Aggregator

Agregador pessoal de write-ups de bug bounty com atualização diária e alertas no Telegram/Discord.

## Stack

- Backend: Python + FastAPI
- Scraper: Python script (GitHub Actions diário)
- Banco: Supabase Postgres
- Frontend: React + Vite + Mantine + TanStack Query + TypeScript

## Fontes coletadas

- https://portswigger.net/research
- https://medium.com/tag/bug-bounty (RSS)
- https://api.hackerone.com/v1/hackers/hacktivity (com credenciais de API)

## Estrutura

- `backend/` API e scraper
- `frontend/` leitor web responsivo
- `infra/supabase/schema.sql` schema/index/RLS/retenção
- `.github/workflows/scrape-daily.yml` job diário
- `package.json` scripts unificados do monorepo

## Monorepo (raiz)

Use comandos na raiz:

```bash
npm install
npm run dev
npm run lint
npm run build
npm run backend:test
```

## 1) Criar projeto Supabase

1. Crie um projeto no Supabase Free.
2. Rode o SQL de `infra/supabase/schema.sql` no SQL Editor.
3. Guarde:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## 2) Configurar GitHub Actions

Em `Settings > Secrets and variables > Actions`, criar:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TELEGRAM_BOT_TOKEN` (opcional)
- `TELEGRAM_CHAT_ID` (opcional)
- `DISCORD_WEBHOOK_URL` (opcional)
- `HACKERONE_USERNAME` (opcional, habilita coleta HackerOne via API)
- `HACKERONE_API_TOKEN` (opcional, habilita coleta HackerOne via API)

O workflow diário está em UTC (`08:15`).

## 3) Rodar backend local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 4) Rodar frontend local

```bash
cd frontend
npm install
npm run dev
```

Configure `VITE_API_BASE_URL` apontando para o backend.

## Filtros

- Fonte
- Ano
- Mês
- Ordenação por data (mais recente primeiro)

## Política de dados

- Ingestão apenas de `2025-01-01` em diante.
- Função `cleanup_old_writeups(months_to_keep, preserve_favorites)` para retenção automática.

## Deploy grátis sugerido

- Frontend: Vercel Free ou Cloudflare Pages
- Backend API: Render Free Web Service
- Banco: Supabase Free
- Agendamento: GitHub Actions (diário)

Observação: planos free podem ter sleep/cold start.
