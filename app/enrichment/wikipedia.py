"""
Wikipedia enrichment — plain HTTP call to the free REST API.
Pulls company summary, description, and existence flag.
"""
import logging
import httpx

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary"


def enrich(company_name: str) -> dict:
    """
    Query Wikipedia for a company page summary.
    Returns structured signal data.
    """
    try:
        # Try exact name first, then with "company" suffix
        for query in [company_name, f"{company_name} (company)"]:
            url = f"{WIKIPEDIA_API}/{query.replace(' ', '_')}"
            resp = httpx.get(url, timeout=15, follow_redirects=True)

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "source": "wikipedia",
                    "method": "http_api",
                    "found": True,
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "extract": data.get("extract", "")[:1000],
                    "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                }

        # Not found on Wikipedia
        return {
            "source": "wikipedia",
            "method": "http_api",
            "found": False,
            "title": company_name,
            "description": "No Wikipedia page found",
            "extract": "",
            "page_url": "",
        }

    except Exception as e:
        logger.error(f"Wikipedia enrichment failed for {company_name}: {e}")
        return {
            "source": "wikipedia",
            "method": "http_api",
            "found": False,
            "error": str(e),
        }
