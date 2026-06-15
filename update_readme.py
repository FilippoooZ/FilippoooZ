#!/usr/bin/env python3
"""
GitHub README Generator - Aggiorna il README con dati dinamici da GitHub API
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = "FilippoooZ"

# Headers per le richieste API
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

BASE_URL = "https://api.github.com"


def fetch_user_repos(limit: int = 10) -> List[Dict[str, Any]]:
    """Recupera i repository recenti dell'utente."""
    url = f"{BASE_URL}/users/{USERNAME}/repos"
    params = {
        "sort": "updated",
        "direction": "desc",
        "per_page": limit,
        "type": "all",
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Errore nel fetching repos: {e}")
        return []


def fetch_user_events(limit: int = 30) -> List[Dict[str, Any]]:
    """Recupera gli eventi recenti dell'utente (push, PR, etc)."""
    url = f"{BASE_URL}/users/{USERNAME}/events"
    params = {"per_page": limit}
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Errore nel fetching events: {e}")
        return []


def fetch_starred_repos(limit: int = 5) -> List[Dict[str, Any]]:
    """Recupera i repository stellati più recenti."""
    url = f"{BASE_URL}/users/{USERNAME}/starred"
    params = {
        "sort": "stars",
        "direction": "desc",
        "per_page": limit,
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Errore nel fetching starred repos: {e}")
        return []


def get_repo_full_name(repo_url: str) -> str:
    """Estrae owner/repo da una URL."""
    return repo_url.split("github.com/")[1].rstrip("/")


def fetch_repo_details(repo_full_name: str) -> Dict[str, Any]:
    """Recupera i dettagli di un repository."""
    url = f"{BASE_URL}/repos/{repo_full_name}"
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Errore nel fetching repo details per {repo_full_name}: {e}")
        return {}


def extract_working_on(events: List[Dict]) -> List[Dict[str, str]]:
    """
    Estrae i progetti su cui sta lavorando dalla lista di eventi.
    Mostra i repository con push/PR recenti.
    """
    repos_with_activity = {}
    cutoff = 7  # ultimi 7 giorni

    for event in events[:30]:
        if event.get("type") not in ["PushEvent", "PullRequestEvent"]:
            continue

        repo_name = event.get("repo", {}).get("name", "")
        if not repo_name:
            continue

        if repo_name not in repos_with_activity:
            created_at = event.get("created_at", "")
            repos_with_activity[repo_name] = created_at

    result = []
    for repo_name, created_at in list(repos_with_activity.items())[:5]:
        repo_full_name = repo_name
        details = fetch_repo_details(repo_full_name)
        result.append(
            {
                "name": details.get("name", repo_name),
                "url": details.get("html_url", f"https://github.com/{repo_name}"),
                "description": details.get("description", ""),
            }
        )

    return result


def extract_latest_projects(repos: List[Dict]) -> List[Dict[str, str]]:
    """Estrae i 5 progetti più recenti."""
    result = []
    for repo in repos[:5]:
        result.append(
            {
                "name": repo.get("name", ""),
                "url": repo.get("html_url", ""),
                "description": repo.get("description", ""),
            }
        )
    return result


def extract_recent_prs(events: List[Dict]) -> List[Dict[str, str]]:
    """Estrae i 5 pull request più recenti."""
    prs = []
    for event in events:
        if event.get("type") != "PullRequestEvent":
            continue
        action = event.get("payload", {}).get("action")
        if action != "opened":
            continue

        pr_data = event.get("payload", {}).get("pull_request", {})
        repo_name = event.get("repo", {}).get("name", "")

        prs.append(
            {
                "title": pr_data.get("title", ""),
                "url": pr_data.get("html_url", ""),
                "repo_name": repo_name,
                "repo_url": f"https://github.com/{repo_name}",
            }
        )

        if len(prs) >= 5:
            break

    return prs


def extract_recent_stars(starred: List[Dict]) -> List[Dict[str, str]]:
    """Estrae i 5 repository stellati più recenti."""
    result = []
    for repo in starred[:5]:
        result.append(
            {
                "name": repo.get("full_name", ""),
                "url": repo.get("html_url", ""),
                "description": repo.get("description", ""),
            }
        )
    return result


def format_markdown_list(items: List[Dict[str, str]], item_format: str) -> str:
    """Formatta una lista di items in markdown."""
    lines = []
    for item in items:
        if "{description}" in item_format:
            desc = item.get("description", "No description")
            desc = desc.strip() if desc else "No description"
            line = item_format.format(
                name=item.get("name", ""),
                url=item.get("url", ""),
                description=desc,
                title=item.get("title", ""),
                repo_name=item.get("repo_name", ""),
                repo_url=item.get("repo_url", ""),
            )
        else:
            line = item_format.format(**item)
        lines.append(line)
    return "\n".join(lines)


def update_readme():
    """Aggiorna il README con i dati dinamici."""
    # Recupera i dati
    repos = fetch_user_repos(10)
    events = fetch_user_events(30)
    starred = fetch_starred_repos(5)

    # Estrae le sezioni
    working_on = extract_working_on(events)
    latest_projects = extract_latest_projects(repos)
    recent_prs = extract_recent_prs(events)
    recent_stars = extract_recent_stars(starred)

    # Leggi il README template
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    # Formatta le sezioni
    working_on_md = format_markdown_list(
        working_on,
        "- [{name}]({url}) - {description}",
    )
    latest_projects_md = format_markdown_list(
        latest_projects,
        "- [{name}]({url}) - {description}",
    )
    recent_prs_md = format_markdown_list(
        recent_prs,
        "- [{title}]({url}) on [{repo_name}]({repo_url})",
    )
    recent_stars_md = format_markdown_list(
        recent_stars,
        "- [{name}]({url}) - {description}",
    )

    # Sostituisci i placeholder
    content = content.replace(
        "<!-- WORKING_ON_START -->\n<!-- WORKING_ON_END -->",
        f"<!-- WORKING_ON_START -->\n{working_on_md}\n<!-- WORKING_ON_END -->",
    )
    content = content.replace(
        "<!-- LATEST_PROJECTS_START -->\n<!-- LATEST_PROJECTS_END -->",
        f"<!-- LATEST_PROJECTS_START -->\n{latest_projects_md}\n<!-- LATEST_PROJECTS_END -->",
    )
    content = content.replace(
        "<!-- RECENT_PRS_START -->\n<!-- RECENT_PRS_END -->",
        f"<!-- RECENT_PRS_START -->\n{recent_prs_md}\n<!-- RECENT_PRS_END -->",
    )
    content = content.replace(
        "<!-- RECENT_STARS_START -->\n<!-- RECENT_STARS_END -->",
        f"<!-- RECENT_STARS_START -->\n{recent_stars_md}\n<!-- RECENT_STARS_END -->",
    )

    # Scrivi il README aggiornato
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ README.md aggiornato con successo!")
    print(f"⏰ Ultimo aggiornamento: {datetime.now().isoformat()}")


if __name__ == "__main__":
    update_readme()
