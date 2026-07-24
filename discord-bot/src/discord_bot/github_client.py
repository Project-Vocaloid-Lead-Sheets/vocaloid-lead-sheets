import aiohttp
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

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

    async def dispatch_workflow(self, workflow: str, *, ref: str = "main", inputs: dict[str, any] | None = None):
        url = f"https://api.github.com/repos/{self._owner}/{self._repo}/actions/workflows/{workflow}/dispatches"
        payload = {"ref": ref, "inputs": inputs or {}}

        async with self._session.post(url, json=payload) as response:
            body = await response.text()
            if response.status != 204:
                raise RuntimeError(f"GitHub workflow dispatch failed ({response.status}): {body}")
