import aiohttp
import logging
import json

from typing import Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class GitHubWorkflow:
    run_id: int
    html_url: str

class GitHubClient:
    def __init__(self, owner: str, repo: str, token: str):
        self._owner = owner
        self._repo = repo

        headers = {
            "Accept": "application/vnd.github+json",
            "authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pvls-automation/1.0",
        }

        self._session = aiohttp.ClientSession(headers=headers)

    async def close(self) -> None:
        await self._session.close()

    async def post_workflow(
        self, workflow: str, *, ref: str = "main", inputs: dict[str, Any] | None = None
    ) -> GitHubWorkflow:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/actions/workflows/{workflow}/dispatches"
        payload = {"ref": ref, "inputs": inputs or {}, "return_run_details": True}

        async with self._session.post(url, json=payload) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(f"GitHub workflow dispatch failed ({response.status}): {body}")

            try:
                data: dict[str, Any] = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError( f"GitHub returned invalid JSON: {body!r}") from exc

        try:
            return GitHubWorkflow(run_id=int(data["workflow_run_id"]), html_url=str(data["html_url"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"GitHub returned an invalid dispatch response: {data!r}") from exc
