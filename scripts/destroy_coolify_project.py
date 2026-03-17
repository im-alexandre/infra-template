from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variavel obrigatoria ausente: {name}")
    return value


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

    def get_project(self, project_uuid: str) -> dict[str, Any]:
        response = self.session.get(self._url(f"/projects/{project_uuid}"), timeout=30)
        response.raise_for_status()
        return response.json()

    def list_applications(self) -> list[dict[str, Any]]:
        response = self.session.get(self._url("/applications"), timeout=30)
        response.raise_for_status()
        return response.json()

    def list_databases(self) -> list[dict[str, Any]]:
        response = self.session.get(self._url("/databases"), timeout=30)
        response.raise_for_status()
        return response.json()

    def delete_application(self, application_uuid: str) -> dict[str, Any] | None:
        response = self.session.delete(self._url(f"/applications/{application_uuid}"), timeout=60)
        response.raise_for_status()
        if not response.text.strip():
            return None
        return response.json()

    def delete_database(self, database_uuid: str) -> dict[str, Any] | None:
        response = self.session.delete(self._url(f"/databases/{database_uuid}"), timeout=60)
        response.raise_for_status()
        if not response.text.strip():
            return None
        return response.json()

    def delete_project(self, project_uuid: str) -> dict[str, Any] | None:
        response = self.session.delete(self._url(f"/projects/{project_uuid}"), timeout=60)
        response.raise_for_status()
        if not response.text.strip():
            return None
        return response.json()


RESOURCE_SPECS = [
    {
        "label": "Aplicacoes",
        "singular": "Aplicacao",
        "list_method": "list_applications",
        "delete_method": "delete_application",
    },
    {
        "label": "Bancos",
        "singular": "Banco",
        "list_method": "list_databases",
        "delete_method": "delete_database",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Destroi um projeto do Coolify e tudo que estiver dentro dele.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o projeto alvo sem deletar.")
    parser.add_argument("--yes", action="store_true", help="Confirma a exclusao real.")
    return parser.parse_args()


def discover_project_resources(
    client: CoolifyClient, environments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    environment_ids = {item.get("id") for item in environments}
    resources: list[dict[str, Any]] = []

    for spec in RESOURCE_SPECS:
        list_method = getattr(client, spec["list_method"])
        items = [
            item
            for item in list_method()
            if item.get("environment_id") in environment_ids
        ]
        resources.append({**spec, "items": items})

    return resources


def print_resource_plan(resources: list[dict[str, Any]]) -> None:
    for resource in resources:
        items = resource["items"]
        if not items:
            continue
        print(f"{resource['label']} que serao removidos:")
        for item in items:
            print(f"- {item.get('name')} ({item.get('uuid')})")


def delete_project_resources(client: CoolifyClient, resources: list[dict[str, Any]]) -> None:
    for resource in resources:
        delete_method = getattr(client, resource["delete_method"])
        for item in resource["items"]:
            result = delete_method(item["uuid"])
            if result and "message" in result:
                print(result["message"])
            else:
                print(f"{resource['singular']} removido: {item['name']} ({item['uuid']})")


def main() -> int:
    args = parse_args()

    try:
        project_uuid = required_env("COOLIFY_PROJECT_UUID")
        client = CoolifyClient(
            base_url=os.getenv("COOLIFY_BASE_URL", "https://coolify.drg.ink"),
            token=required_env("COOLIFY_API_TOKEN"),
        )
        project = client.get_project(project_uuid)
        environments = project.get("environments", [])
        resources = discover_project_resources(client, environments)
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        print(f"Erro HTTP ao consultar o Coolify: {exc}\n{body}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Projeto alvo: {project.get('name')} ({project_uuid})")
    if environments:
        environment_names = ", ".join(item.get("name", "<sem nome>") for item in environments)
        print(f"Ambientes encontrados: {environment_names}")
    print_resource_plan(resources)

    if args.dry_run:
        print("Dry-run concluido. Nenhuma exclusao foi executada.")
        return 0

    if not args.yes:
        print("Nada foi apagado. Rode com --yes para confirmar a exclusao do projeto.", file=sys.stderr)
        return 1

    try:
        delete_project_resources(client, resources)
        result = client.delete_project(project_uuid)
        if result and "message" in result:
            print(result["message"])
        else:
            print("Projeto removido no Coolify.")
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        print(f"Erro HTTP ao deletar o projeto no Coolify: {exc}\n{body}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
