from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variavel obrigatoria ausente: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class CoolifyClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def get_json(self, path: str) -> Any:
        response = self.session.get(self._url(path), timeout=30)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.post(self._url(path), data=json.dumps(payload), timeout=60)
        response.raise_for_status()
        return response.json()

    def patch_json(self, path: str, payload: dict[str, Any]) -> Any:
        response = self.session.patch(self._url(path), data=json.dumps(payload), timeout=60)
        response.raise_for_status()
        return response.json()

    def list_applications(self) -> list[dict[str, Any]]:
        return self.get_json("/applications")

    def create_application(self, payload: dict[str, Any]) -> dict[str, Any]:
        git_type = payload["git_type"]
        if git_type == "public":
            return self.post_json("/applications/public", payload)
        if git_type == "private-deploy-key":
            return self.post_json("/applications/private-deploy-key", payload)
        raise RuntimeError(f"Tipo de repositiorio nao suportado: {git_type}")

    def update_application(self, application_uuid: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch_json(f"/applications/{application_uuid}", payload)

    def start_application(self, application_uuid: str) -> dict[str, Any]:
        return self.get_json(f"/applications/{application_uuid}/start")

    def list_application_envs(self, application_uuid: str) -> list[dict[str, Any]]:
        return self.get_json(f"/applications/{application_uuid}/envs")

    def create_application_env(self, application_uuid: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post_json(f"/applications/{application_uuid}/envs", payload)

    def update_application_env(self, env_uuid: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch_json(f"/envs/{env_uuid}", payload)

    def list_databases(self) -> list[dict[str, Any]]:
        return self.get_json("/databases")

    def create_postgresql_database(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post_json("/databases/postgresql", payload)

    def start_database(self, database_uuid: str) -> dict[str, Any]:
        return self.get_json(f"/databases/{database_uuid}/start")


def build_application_payload() -> dict[str, Any]:
    domain = required_env("DOMAIN")
    payload = {
        "project_uuid": required_env("COOLIFY_PROJECT_UUID"),
        "server_uuid": required_env("COOLIFY_SERVER_UUID"),
        "environment_name": required_env("COOLIFY_ENVIRONMENT_NAME"),
        "environment_uuid": required_env("COOLIFY_ENVIRONMENT_UUID"),
        "destination_uuid": required_env("COOLIFY_DESTINATION_UUID"),
        "name": os.getenv("COOLIFY_APP_NAME", "infra_template"),
        "description": os.getenv("COOLIFY_APP_DESCRIPTION", "infra_template - Django app"),
        "git_repository": required_env("COOLIFY_GIT_REPOSITORY"),
        "git_branch": os.getenv("COOLIFY_GIT_BRANCH", "main"),
        "git_type": os.getenv("COOLIFY_GIT_TYPE", "public"),
        "build_pack": os.getenv("COOLIFY_BUILD_PACK", "dockerfile"),
        "dockerfile_location": os.getenv("COOLIFY_DOCKERFILE_LOCATION", "/Dockerfile"),
        "base_directory": os.getenv("COOLIFY_BASE_DIRECTORY", "/"),
        "ports_exposes": os.getenv("COOLIFY_APP_PORT", "8000"),
        "publish_directory": os.getenv("COOLIFY_PUBLISH_DIRECTORY", ""),
        "domains": f"https://{domain}",
        "health_check_enabled": True,
        "health_check_path": "/healthz/",
        "health_check_port": os.getenv("COOLIFY_APP_PORT", "8000"),
        "health_check_host": "127.0.0.1",
        "health_check_method": "GET",
        "health_check_return_code": 200,
        "health_check_scheme": "http",
        "health_check_interval": 10,
        "health_check_timeout": 5,
        "health_check_retries": 15,
        "health_check_start_period": 30,
        "is_force_https_enabled": True,
        "redirect": "both",
        "instant_deploy": False,
    }
    private_key_uuid = os.getenv("COOLIFY_PRIVATE_KEY_UUID", "").strip()
    if payload["git_type"] == "private-deploy-key":
        if not private_key_uuid:
            raise RuntimeError("COOLIFY_PRIVATE_KEY_UUID e obrigatoria para git privado com deploy key.")
        payload["private_key_uuid"] = private_key_uuid
    return payload


def build_database_payload() -> dict[str, Any]:
    return {
        "server_uuid": required_env("COOLIFY_SERVER_UUID"),
        "project_uuid": required_env("COOLIFY_PROJECT_UUID"),
        "environment_name": required_env("COOLIFY_ENVIRONMENT_NAME"),
        "environment_uuid": required_env("COOLIFY_ENVIRONMENT_UUID"),
        "destination_uuid": required_env("COOLIFY_DESTINATION_UUID"),
        "name": os.getenv("COOLIFY_DATABASE_NAME", "infra-template-db"),
        "description": os.getenv("COOLIFY_DATABASE_DESCRIPTION", "infra_template - PostgreSQL"),
        "postgres_user": required_env("POSTGRES_USER"),
        "postgres_password": required_env("POSTGRES_PASSWORD"),
        "postgres_db": required_env("POSTGRES_DB"),
        "is_public": env_bool("COOLIFY_DATABASE_IS_PUBLIC", False),
        "public_port": int(os.getenv("COOLIFY_DATABASE_PUBLIC_PORT", "5432")),
        "instant_deploy": False,
    }


def desired_application_envs(postgres_host_override: str | None = None) -> list[dict[str, Any]]:
    public_domain = required_env("DOMAIN")
    csrf_origins = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", f"https://{public_domain}")
    allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", public_domain)
    postgres_host = postgres_host_override or os.getenv("COOLIFY_POSTGRES_HOST", "").strip() or os.getenv("POSTGRES_HOST", "").strip()

    envs = [
        {"key": "DJANGO_SECRET_KEY", "value": required_env("DJANGO_SECRET_KEY"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_DEBUG", "value": os.getenv("DJANGO_DEBUG", "False"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_ALLOWED_HOSTS", "value": allowed_hosts, "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_CSRF_TRUSTED_ORIGINS", "value": csrf_origins, "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_SUPERUSER_USERNAME", "value": required_env("DJANGO_SUPERUSER_USERNAME"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_SUPERUSER_EMAIL", "value": required_env("DJANGO_SUPERUSER_EMAIL"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "DJANGO_SUPERUSER_PASSWORD", "value": required_env("DJANGO_SUPERUSER_PASSWORD"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "POSTGRES_DB", "value": required_env("POSTGRES_DB"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "POSTGRES_USER", "value": required_env("POSTGRES_USER"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "POSTGRES_PASSWORD", "value": required_env("POSTGRES_PASSWORD"), "is_preview": False, "is_build_time": False, "is_literal": False},
        {"key": "POSTGRES_PORT", "value": os.getenv("POSTGRES_PORT", "5432"), "is_preview": False, "is_build_time": False, "is_literal": False},
    ]
    if postgres_host:
        envs.append({"key": "POSTGRES_HOST", "value": postgres_host, "is_preview": False, "is_build_time": False, "is_literal": False})
    return envs


def upsert_application(client: CoolifyClient, payload: dict[str, Any]) -> tuple[str, str]:
    application_name = payload["name"]
    applications = client.list_applications()
    existing = next((item for item in applications if item.get("name") == application_name), None)
    if existing:
        result = client.update_application(existing["uuid"], payload)
        return existing["uuid"], f"Aplicacao atualizada: {result['uuid']}"

    result = client.create_application(payload)
    return result["uuid"], f"Aplicacao criada: {result['uuid']}"


def upsert_application_envs(client: CoolifyClient, application_uuid: str, envs: list[dict[str, Any]]) -> None:
    existing_envs = client.list_application_envs(application_uuid)
    existing_by_key = {item["key"]: item for item in existing_envs}
    for env_payload in envs:
        current = existing_by_key.get(env_payload["key"])
        if current:
            client.update_application_env(current["uuid"], env_payload)
        else:
            client.create_application_env(application_uuid, env_payload)


def parse_internal_postgres_host(database: dict[str, Any]) -> str | None:
    internal_db_url = database.get("internal_db_url")
    if not internal_db_url:
        return None
    parsed = urlparse(internal_db_url)
    return parsed.hostname


def maybe_create_database(client: CoolifyClient) -> tuple[str | None, str | None, str | None]:
    if not env_bool("COOLIFY_CREATE_POSTGRES", False):
        return None, None, None

    database_name = os.getenv("COOLIFY_DATABASE_NAME", "infra-template-db")
    existing = next((item for item in client.list_databases() if item.get("name") == database_name), None)
    if existing:
        return existing["uuid"], f"Banco ja existe: {existing['uuid']}", parse_internal_postgres_host(existing)

    created = client.create_postgresql_database(build_database_payload())
    database_uuid = created["uuid"]
    refreshed = next((item for item in client.list_databases() if item.get("uuid") == database_uuid), created)
    return database_uuid, f"Banco criado: {database_uuid}", parse_internal_postgres_host(refreshed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy Django via Git na API do Coolify.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra os payloads sem chamar a API.")
    parser.add_argument("--skip-start", action="store_true", help="Nao dispara start ao final.")
    parser.add_argument("--skip-database", action="store_true", help="Nao cria nem inicia o PostgreSQL no Coolify.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    application_payload = build_application_payload()
    database_payload = build_database_payload()
    postgres_host_override = os.getenv("COOLIFY_POSTGRES_HOST", "").strip() or None
    application_envs = desired_application_envs(postgres_host_override)

    if args.dry_run:
        output = {
            "application": application_payload,
            "application_envs": application_envs,
            "database_enabled": env_bool("COOLIFY_CREATE_POSTGRES", False) and not args.skip_database,
            "database": database_payload,
        }
        print(json.dumps(output, indent=2))
        return 0

    client = CoolifyClient(
        base_url=os.getenv("COOLIFY_BASE_URL", "https://coolify.drg.ink"),
        token=required_env("COOLIFY_API_TOKEN"),
    )

    try:
        database_uuid = None
        if not args.skip_database:
            database_uuid, database_message, postgres_host = maybe_create_database(client)
            if database_message:
                print(database_message)
            if postgres_host:
                application_envs = desired_application_envs(postgres_host)
                print(f"Host interno do PostgreSQL detectado: {postgres_host}")
            if database_uuid and not args.skip_start:
                db_result = client.start_database(database_uuid)
                print(db_result.get("message", "Start do banco solicitado."))

        application_uuid, application_message = upsert_application(client, application_payload)
        print(application_message)
        upsert_application_envs(client, application_uuid, application_envs)
        print("Variaveis da aplicacao sincronizadas.")

        if not (postgres_host_override or (not args.skip_database and postgres_host)):
            print(
                "Aviso: COOLIFY_POSTGRES_HOST nao esta definido. "
                "Se o host interno do Postgres no Coolify for diferente de POSTGRES_HOST, ajuste no .env antes do start."
            )

        if not args.skip_start:
            app_result = client.start_application(application_uuid)
            print(app_result.get("message", "Start da aplicacao solicitado."))
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        print(f"Erro HTTP ao falar com o Coolify: {exc}\n{body}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
