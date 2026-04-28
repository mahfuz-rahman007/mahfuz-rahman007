#!/usr/bin/env python3
import json
import os
import urllib.request
from pathlib import Path

USERNAME = "mahfuz-rahman007"
README_PATH = Path(__file__).resolve().parents[1] / "README.md"
START_MARKER = "<!-- metrics:auto:start -->"
END_MARKER = "<!-- metrics:auto:end -->"


def github_request(url: str, payload: dict | None = None) -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required")

    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-metrics-updater",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def graphql(query: str) -> dict:
    response = github_request("https://api.github.com/graphql", {"query": query})
    if "errors" in response:
        raise RuntimeError(f"GraphQL errors: {response['errors']}")
    return response["data"]


def build_metrics_block() -> str:
    data = graphql(
        f'''
        query {{
          user(login: "{USERNAME}") {{
            pullRequests {{ totalCount }}
            issues {{ totalCount }}
            contributionsCollection {{
              totalPullRequestContributions
              totalIssueContributions
              totalPullRequestReviewContributions
              contributionCalendar {{
                totalContributions
              }}
            }}
            mergedPullRequests: pullRequests(first: 100, states: MERGED, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
              nodes {{
                repository {{
                  nameWithOwner
                }}
              }}
            }}
          }}
        }}
        '''
    )

    user = data["user"]
    contributions = user["contributionsCollection"]
    merged_nodes = user["mergedPullRequests"]["nodes"]
    xcloud_merged = sum(1 for pr in merged_nodes if pr["repository"]["nameWithOwner"] == "xCloudDev/xCloud")
    laravel_merged = sum(1 for pr in merged_nodes if pr["repository"]["nameWithOwner"].startswith("laravel/"))

    lines = [
        START_MARKER,
        f"- **{user['pullRequests']['totalCount']} pull requests opened**",
        f"- **{user['issues']['totalCount']} issues opened**",
        f"- **{contributions['totalPullRequestContributions']} pull request contributions**",
        f"- **{contributions['totalPullRequestReviewContributions']} pull request reviews**",
        f"- **{contributions['contributionCalendar']['totalContributions']} total contributions in the current contribution calendar**",
        f"- **{xcloud_merged} merged PRs in xCloud**",
        f"- **{laravel_merged} merged PRs in Laravel open source**",
        END_MARKER,
    ]
    return "\n".join(lines)


def update_readme() -> bool:
    content = README_PATH.read_text()
    if START_MARKER not in content or END_MARKER not in content:
        raise RuntimeError("README markers not found")

    start = content.index(START_MARKER)
    end = content.index(END_MARKER) + len(END_MARKER)
    new_block = build_metrics_block()
    updated = content[:start] + new_block + content[end:]

    if updated == content:
        return False

    README_PATH.write_text(updated)
    return True


def main() -> int:
    changed = update_readme()
    print("README updated" if changed else "README already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
