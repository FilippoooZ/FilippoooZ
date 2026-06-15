#!/usr/bin/env python3
"""
GitHub README Generator - Aggiorna il README con dati dinamici da GitHub API (GraphQL v4)
"""

import os
from datetime import datetime
from typing import List, Dict, Any

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = "FilippoooZ"
BASE_URL = "https://api.github.com"


def fetch_graphql_data(username: str, token: str) -> Dict[str, Any]:
    """Recupera tutti i dati necessari con una singola chiamata GraphQL v4."""
    url = f"{BASE_URL}/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    query = """
    query($login: String!) {
      user(login: $login) {
        workingOn: repositories(first: 10, ownerAffiliations: OWNER, orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes {
            name
            url
            description
          }
        }
        latestProjects: repositories(first: 10, ownerAffiliations: OWNER, orderBy: {field: CREATED_AT, direction: DESC}) {
          nodes {
            name
            url
            description
          }
        }
        pullRequests(first: 10) {
          nodes {
            title
            url
            repository {
              nameWithOwner
              url
            }
          }
        }
        starredRepositories(first: 10) {
          edges {
            node {
              nameWithOwner
              url
              description
            }
          }
        }
      }
    }
    """
    
    try:
        resp = requests.post(url, json={"query": query, "variables": {"login": username}}, headers=headers)
        resp.raise_for_status()
        res = resp.json()
    except Exception as e:
        raise Exception(f"Errore nella richiesta HTTP a GraphQL: {e}")
        
    if "errors" in res:
        raise Exception(f"GitHub GraphQL API ha restituito errori: {res['errors']}")
        
    data = res.get("data", {}).get("user")
    if not data:
        raise Exception("Nessun dato utente trovato nella risposta di GitHub GraphQL API")
        
    return data


def extract_working_on(data: Dict) -> List[Dict[str, str]]:
    """Estrae i repository su cui si è lavorato di recente."""
    nodes = data.get("workingOn", {}).get("nodes", [])
    result = []
    for node in nodes:
        result.append({
            "name": node.get("name", ""),
            "url": node.get("url", ""),
            "description": node.get("description", "")
        })
    return result[:5]


def extract_latest_projects(data: Dict) -> List[Dict[str, str]]:
    """Estrae i progetti creati più di recente."""
    nodes = data.get("latestProjects", {}).get("nodes", [])
    result = []
    for node in nodes:
        result.append({
            "name": node.get("name", ""),
            "url": node.get("url", ""),
            "description": node.get("description", "")
        })
    return result[:5]


def extract_recent_prs(data: Dict) -> List[Dict[str, str]]:
    """Estrae le pull request create di recente."""
    nodes = data.get("pullRequests", {}).get("nodes", [])
    result = []
    for node in nodes:
        repo = node.get("repository", {})
        result.append({
            "title": node.get("title", ""),
            "url": node.get("url", ""),
            "repo_name": repo.get("nameWithOwner", ""),
            "repo_url": repo.get("url", "")
        })
    return result[:5]


def extract_recent_stars(data: Dict) -> List[Dict[str, str]]:
    """Estrae i repository stellati di recente."""
    edges = data.get("starredRepositories", {}).get("edges", [])
    result = []
    for edge in edges:
        node = edge.get("node", {})
        result.append({
            "name": node.get("nameWithOwner", ""),
            "url": node.get("url", ""),
            "description": node.get("description", "")
        })
    return result[:5]


def format_markdown_list(items: List[Dict[str, str]], item_format: str) -> str:
    """Formatta una lista di items in markdown, omettendo la descrizione se vuota o 'No description'."""
    lines = []
    for item in items:
        if "{description}" in item_format:
            desc = item.get("description")
            if not desc or desc.strip().lower() in ["", "no description"]:
                base_format = item_format.split(" - {description}")[0]
                line = base_format.format(
                    name=item.get("name", ""),
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    repo_name=item.get("repo_name", ""),
                    repo_url=item.get("repo_url", ""),
                )
            else:
                line = item_format.format(
                    name=item.get("name", ""),
                    url=item.get("url", ""),
                    description=desc.strip(),
                    title=item.get("title", ""),
                    repo_name=item.get("repo_name", ""),
                    repo_url=item.get("repo_url", ""),
                )
        else:
            line = item_format.format(**item)
        lines.append(line)
    return "\n".join(lines)


def replace_chunk(content: str, start_marker: str, end_marker: str, replacement: str) -> str:
    """Sostituisce il contenuto tra due marker (inclusi i marker stessi)."""
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        return content
    return content[:start_idx] + f"{start_marker}\n{replacement}\n{end_marker}" + content[end_idx + len(end_marker):]


def update_readme():
    """Aggiorna il README con i dati dinamici."""
    if not GITHUB_TOKEN:
        raise Exception("Errore: la variabile d'ambiente GITHUB_TOKEN non è impostata.")

    # Recupera i dati via GraphQL
    data = fetch_graphql_data(USERNAME, GITHUB_TOKEN)

    # Estrae le sezioni
    working_on = extract_working_on(data)
    latest_projects = extract_latest_projects(data)
    recent_prs = extract_recent_prs(data)
    recent_stars = extract_recent_stars(data)

    # Leggi il README
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

    # Sostituisci i placeholder nel README
    content = replace_chunk(content, "<!-- WORKING_ON_START -->", "<!-- WORKING_ON_END -->", working_on_md)
    content = replace_chunk(content, "<!-- LATEST_PROJECTS_START -->", "<!-- LATEST_PROJECTS_END -->", latest_projects_md)
    content = replace_chunk(content, "<!-- RECENT_PRS_START -->", "<!-- RECENT_PRS_END -->", recent_prs_md)
    content = replace_chunk(content, "<!-- RECENT_STARS_START -->", "<!-- RECENT_STARS_END -->", recent_stars_md)

    # Scrivi il README aggiornato
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ README.md aggiornato con successo via GraphQL API!")
    print(f"⏰ Ultimo aggiornamento: {datetime.now().isoformat()}")


if __name__ == "__main__":
    update_readme()
