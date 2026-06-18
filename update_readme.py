#!/usr/bin/env python3
"""
GitHub README Generator - Aggiorna il README con dati dinamici da GitHub API (GraphQL v4)
Migliorato: supporta GH_PAT come fallback, logging dei response per debug e timeout.
"""

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

import requests

# Preferisci un Personal Access Token (GH_PAT) se disponibile, altrimenti usa GITHUB_TOKEN
GITHUB_TOKEN = os.getenv("GH_PAT") or os.getenv("GITHUB_TOKEN")
USERNAME = "FilippoooZ"
BASE_URL = "https://api.github.com"


def fetch_graphql_data(username: str, token: str) -> Dict[str, Any]:
    """Recupera tutti i dati necessari con una singola chiamata GraphQL v4.

    Aggiunge logging in caso di errori HTTP o di risposta GraphQL per facilitare il debug
    quando il workflow non restituisce dati (es. token senza permessi o profilo privato).
    """
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
        resp = requests.post(url, json={"query": query, "variables": {"login": username}}, headers=headers, timeout=15)
    except Exception as e:
        print(f"Errore nella chiamata HTTP a GraphQL: {e}")
        raise

    # Log di base per debug
    if resp.status_code != 200:
        print(f"GraphQL HTTP status: {resp.status_code}")
        try:
            print("Response body:", resp.text)
        except Exception:
            print("Impossibile leggere response body")

    try:
        res = resp.json()
    except Exception as e:
        print("Impossibile decodificare JSON dalla response:", e)
        print("Raw response:", getattr(resp, "text", "<no text>"))
        raise

    if "errors" in res:
        print("GraphQL errors:", res.get("errors"))
        # Non fallare subito, ritorniamo comunque i dati se presenti per evitare partial updates

    data = res.get("data", {}).get("user")
    if not data:
        # Stampa diagnostica per capire perché non ci sono dati
        print("Nessun campo 'user' nella risposta GraphQL. Response completa:")
        print(res)
        raise Exception("Nessun dato utente trovato nella risposta di GitHub GraphQL API. Verifica che il token abbia i permessi corretti o che il profilo renda pubbliche le attività.")

    return data


def extract_working_on(data: Dict) -> List[Dict[str, str]]:
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
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        return content
    return content[:start_idx] + f"{start_marker}\n{replacement}\n{end_marker}" + content[end_idx + len(end_marker):]


def update_readme():
    if not GITHUB_TOKEN:
        raise Exception("Errore: nessun token disponibile. Aggiungi GH_PAT come secret (consigliato) o assicurati che GITHUB_TOKEN sia presente.")

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
    try:
        update_readme()
    except Exception as e:
        print("Errore durante l'aggiornamento del README:", e)
        sys.exit(1)
