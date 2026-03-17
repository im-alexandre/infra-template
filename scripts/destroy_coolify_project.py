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

    def delete_project(self, project_uuid: str) -> dict[str, Any] | None:
        response = self.session.delete(self._url(f"/projects/{project_uuid}"), timeout=60)
        response.raise_for_status()
        if not response.text.strip():
            return None
        return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Destroi um projeto do Coolify e tudo que estiver dentro dele.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o projeto alvo sem deletar.")
    parser.add_argument("--yes", action="store_true", help="Confirma a exclusao real.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        project_uuid = required_env("COOLIFY_PROJECT_UUID")
        client = CoolifyClient(
            base_url=os.getenv("COOLIFY_BASE_URL", "https://coolify.drg.ink"),
            token=required_env("COOLIFY_API_TOKEN"),
        )
        project = client.get_project(project_uuid)
    except requests.HTTPError as exc:
        body = exc.response.text if exc.response is not None else ""
        print(f"Erro HTTP ao consultar o Coolify: {exc}\n{body}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Projeto alvo: {project.get('name')} ({project_uuid})")
    environments = project.get("environments", [])
    if environments:
        environment_names = ", ".join(item.get("name", "<sem nome>") for item in environments)
        print(f"Ambientes encontrados: {environment_names}")

    if args.dry_run:
        print("Dry-run concluido. Nenhuma exclusao foi executada.")
        return 0

    if not args.yes:
        print("Nada foi apagado. Rode com --yes para confirmar a exclusao do projeto.", file=sys.stderr)
        return 1

    try:
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
