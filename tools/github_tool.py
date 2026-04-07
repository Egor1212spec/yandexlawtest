"""
tools/github_tool.py
Fetches recent commits from one or more GitHub repositories.
"""

import requests
from datetime import datetime, timedelta, timezone
from config import Config


class GitHubTool:
    BASE = "https://api.github.com"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.headers = {
            "Authorization": f"token {cfg.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }

    def get_recent_commits(self) -> str:
        """Return a Markdown-formatted string of recent commits across all repos."""
        since = (
            datetime.now(timezone.utc) - timedelta(days=self.cfg.GITHUB_DAYS_BACK)
        ).isoformat()

        lines = []
        for repo in self.cfg.GITHUB_REPOS:
            lines.append(f"\n## Repository: {repo}\n")
            try:
                url = f"{self.BASE}/repos/{repo}/commits"
                resp = requests.get(
                    url,
                    headers=self.headers,
                    params={"since": since, "per_page": 50},
                    timeout=10,
                )
                resp.raise_for_status()
                commits = resp.json()

                if not commits:
                    lines.append("_No commits in this period._\n")
                    continue

                for c in commits:
                    sha = c["sha"][:7]
                    msg = c["commit"]["message"].split("\n")[0]  # first line only
                    author = c["commit"]["author"]["name"]
                    date = c["commit"]["author"]["date"][:10]
                    lines.append(f"- `{sha}` [{date}] **{author}**: {msg}")

            except Exception as e:
                lines.append(f"_Error fetching commits: {e}_")

        return "\n".join(lines)

    def get_commit_details(self, repo: str, sha: str) -> str:
        """Fetch full diff/message for a single commit."""
        try:
            url = f"{self.BASE}/repos/{repo}/commits/{sha}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            msg = data["commit"]["message"]
            files = [f["filename"] for f in data.get("files", [])]
            return f"**{sha[:7]}**: {msg}\nFiles changed: {', '.join(files)}"
        except Exception as e:
            return f"Error: {e}"
