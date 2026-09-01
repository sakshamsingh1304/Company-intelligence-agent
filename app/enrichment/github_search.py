"""
GitHub enrichment — plain HTTP call to the free GitHub Search API.
Pulls open-source presence, top repos, stars, and primary languages.
No API key required (60 req/hr unauthenticated — sufficient for our use).
"""
import logging
import httpx

logger = logging.getLogger(__name__)

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def enrich(company_name: str) -> dict:
    """
    Search GitHub for repositories related to the company.
    Returns structured signal data about open-source presence.
    """
    try:
        params = {
            "q": f"{company_name}",
            "sort": "stars",
            "order": "desc",
            "per_page": 5,
        }
        headers = {"Accept": "application/vnd.github.v3+json"}
        resp = httpx.get(GITHUB_SEARCH_URL, params=params,
                         headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            total_count = data.get("total_count", 0)
            items = data.get("items", [])

            top_repos = []
            total_stars = 0
            languages = set()

            for repo in items:
                stars = repo.get("stargazers_count", 0)
                total_stars += stars
                lang = repo.get("language")
                if lang:
                    languages.add(lang)
                top_repos.append({
                    "name": repo.get("full_name", ""),
                    "description": (repo.get("description") or "")[:200],
                    "stars": stars,
                    "language": lang or "Unknown",
                    "url": repo.get("html_url", ""),
                })

            return {
                "source": "github",
                "method": "http_api",
                "found": total_count > 0,
                "total_repos_found": total_count,
                "top_repos": top_repos,
                "total_stars_top5": total_stars,
                "languages": list(languages),
                "open_source_presence": (
                    "strong" if total_count > 50
                    else "moderate" if total_count > 10
                    else "weak" if total_count > 0
                    else "none"
                ),
            }

        elif resp.status_code == 403:
            logger.warning("GitHub API rate limit reached")
            return {
                "source": "github",
                "method": "http_api",
                "found": False,
                "error": "Rate limit reached — try again later",
            }
        else:
            return {
                "source": "github",
                "method": "http_api",
                "found": False,
                "error": f"HTTP {resp.status_code}",
            }

    except Exception as e:
        logger.error(f"GitHub enrichment failed for {company_name}: {e}")
        return {
            "source": "github",
            "method": "http_api",
            "found": False,
            "error": str(e),
        }
