# Django + PostgreSQL + Traefik + Coolify

Projeto base em Python com Django, PostgreSQL, Traefik e um script Python para publicar a stack via API do Coolify.

## Requisitos

- Python 3.12+
- Docker e Docker Compose

## Uso local

1. Copie `.env.example` para `.env`.
2. Ajuste as variaveis conforme o ambiente.
3. Crie um ambiente virtual e instale as dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

4. Suba os containers:

```bash
docker compose up --build
```

5. A aplicacao fica disponivel em `http://localhost`.

## Deploy com Coolify

O deploy remoto usa a API do Coolify para criar ou atualizar uma aplicacao apontando para um repositorio Git. O Dockerfile do projeto continua sendo usado, mas a imagem e construida pelo proprio Coolify a partir do repositorio.

1. Gere um token em `Keys & Tokens` na sua instancia do Coolify.
2. Preencha no `.env`:
   - `COOLIFY_BASE_URL` com a URL da instancia. O default do projeto e `https://coolify.drg.ink`.
   - `DOMAIN` com o dominio publico da aplicacao no Traefik e no Coolify.
   - `TRAEFIK_DASHBOARD_HOST` com o dominio do dashboard do Traefik, se for expor.
   - `COOLIFY_GIT_REPOSITORY` com o repositorio no formato `owner/repo` para GitHub.
   - `COOLIFY_GIT_BRANCH` com a branch de deploy.
   - `COOLIFY_PROJECT_UUID`
   - `COOLIFY_ENVIRONMENT_UUID`
   - `COOLIFY_DESTINATION_UUID`
3. Rode:

```bash
python scripts/deploy_coolify.py
```

### Dry run

```bash
python scripts/deploy_coolify.py --dry-run
```

O script cria ou atualiza a aplicacao Git no Coolify, sincroniza as variaveis de ambiente e pode opcionalmente criar um PostgreSQL pelo proprio Coolify.

## Referencias

- Coolify API Reference: https://coolify.io/docs/api-reference/api/
- Django PostgreSQL: https://docs.djangoproject.com/en/stable/ref/databases/#postgresql-notes
- Django Deployment Checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- Traefik Docker Provider: https://doc.traefik.io/traefik/providers/docker/
