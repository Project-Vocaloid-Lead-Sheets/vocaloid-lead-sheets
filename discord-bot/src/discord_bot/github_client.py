import aiohttp
import logging
import pathlib
import base64
import json

from typing import Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

@dataclass(frozen=False)
class GitHubWorkflow:
    run_id: int
    html_url: str
    git_sha: str
    status: str
    channel_id: str
    conclusion: str | None

    @property
    def completed(self) -> bool:
        return self.status == "completed"

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

    async def get_branch_sha(self, branch: str = "main") -> str:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/git/ref/heads/{branch}"
        async with self._session.get(url) as response:
            response.raise_for_status()
            body = await response.json()
        return body["object"]["sha"]

    async def post_workflow(
        self, workflow: str, *, ref: str = "main", inputs: dict[str, Any] | None = None
    ) -> GitHubWorkflow:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/actions/workflows/{workflow}/dispatches"
        payload = {"ref": ref, "inputs": inputs or {}, "return_run_details": True}
        sha = await self.get_branch_sha(ref)

        async with self._session.post(url, json=payload) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(f"GitHub workflow dispatch failed ({response.status}): {body}")

            try:
                data: dict[str, Any] = json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError( f"GitHub returned invalid JSON: {body!r}") from exc

        try:
            return GitHubWorkflow(
                run_id=int(data["workflow_run_id"]),
                html_url=str(data["html_url"]),
                git_sha=sha,
                status=None,
                channel_id=None,
                conclusion=None
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"GitHub returned an invalid dispatch response: {data!r}") from exc

    async def get_workflow_status(self, run_id: int):
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/actions/runs/{run_id}"
        async with self._session.get(url) as response:
            body = await response.text()
            if response.status != 200:
                raise RuntimeError(f"GitHub workflow lookup failed ({response.status}): {body}")

            try:
                data: dict[str, Any] = await response.json()
            except aiohttp.ContentTypeError as exc:
                raise RuntimeError(f"GitHub returned a non-JSON response: {body!r}") from exc

        try:
            return GitHubWorkflow(
                run_id=int(data["id"]),
                html_url=str(data["html_url"]),
                git_sha=None,
                status=str(data["status"]),
                channel_id=None,
                conclusion=str(data["conclusion"]) if data["conclusion"] is not None else None
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"GitHub returned an invalid workflow response: {data!r}") from exc

    async def get_diff_file_list(self, before_sha: str, after_sha: str) -> list[str]:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/compare/{before_sha}...{after_sha}"

        async with self._session.get(url) as response:
            response.raise_for_status()
            body = await response.json()

        return [file["filename"] for file in body["files"] if file["status"] != "removed"]

    async def download_json_at(self, path: str, ref: str = "main") -> dict:
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/contents/{path}"
        async with self._session.get(url, params={"ref": ref}) as response:
            response.raise_for_status()
            body = await response.json()
            return json.loads(base64.b64decode(body["content"]))
