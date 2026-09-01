"""
Browser-based enrichment — real Selenium automation (Task §2 requirement).
Scrapes DuckDuckGo HTML search results for company intelligence.
This is NOT a plain HTTP call — it drives a real headless Chrome browser.
"""
import logging
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

_GLOBAL_DRIVER = None

def init_driver():
    """Initialize the global WebDriver instance."""
    global _GLOBAL_DRIVER
    if not _GLOBAL_DRIVER:
        _GLOBAL_DRIVER = _get_driver()

def quit_driver():
    """Quit the global WebDriver instance."""
    global _GLOBAL_DRIVER
    if _GLOBAL_DRIVER:
        try:
            _GLOBAL_DRIVER.quit()
        except Exception:
            pass
        _GLOBAL_DRIVER = None

def _get_driver() -> webdriver.Chrome:
    """Configure and return a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # In Docker / Render, Chrome + chromedriver are installed at known paths
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
    else:
        # Local dev: use webdriver-manager to auto-download
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=options)


def enrich(company_name: str) -> dict:
    """
    Use a real browser to search DuckDuckGo and scrape results.
    Extracts top search snippets, URLs, and inferred metadata.
    """
    global _GLOBAL_DRIVER
    if not _GLOBAL_DRIVER:
        init_driver()

    try:
        query = f"{company_name} company overview"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"

        logger.info(f"Browser automation: navigating to DuckDuckGo for '{company_name}'")
        _GLOBAL_DRIVER.get(url)

        # Wait for search results to load
        WebDriverWait(_GLOBAL_DRIVER, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".result"))
        )

        results = []
        elements = _GLOBAL_DRIVER.find_elements(By.CSS_SELECTOR, ".result")[:5]

        for el in elements:
            try:
                title_el = el.find_element(By.CSS_SELECTOR, ".result__a")
                title = title_el.text.strip()
                link = title_el.get_attribute("href") or ""

                try:
                    snippet_el = el.find_element(By.CSS_SELECTOR, ".result__snippet")
                    snippet = snippet_el.text.strip()
                except Exception:
                    snippet = ""

                if title:
                    results.append({
                        "title": title,
                        "snippet": snippet[:300],
                        "link": link,
                    })
            except Exception:
                continue

        # Try to extract page title
        page_title = _GLOBAL_DRIVER.title

        return {
            "source": "duckduckgo_browser",
            "method": "selenium_browser_automation",
            "found": len(results) > 0,
            "query": query,
            "page_title": page_title,
            "results_count": len(results),
            "top_results": results,
        }

    except Exception as e:
        logger.error(f"Browser enrichment failed for {company_name}: {e}")
        return {
            "source": "duckduckgo_browser",
            "method": "selenium_browser_automation",
            "found": False,
            "error": str(e),
        }
