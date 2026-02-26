"""
ZipRecruiter Scraper using Playwright + ThreadPoolExecutor + TF-IDF NLP matching.
"""
import time
import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from playwright.sync_api import sync_playwright

from config import SEARCH_TITLES, RESUME_KEYWORDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COOKIES = [
    {'name': 'ziprecruiter_session', 'value': 'df031e0ea4a14b4f2cf64f3f76a9d6ac', 'domain': '.ziprecruiter.com', 'path': '/'},
    {'name': 'ziprecruiter_browser', 'value': '005d251a-93f2-4f57-ad66-3a5119b6c4f0', 'domain': '.ziprecruiter.com', 'path': '/'},
    {'name': 'zglobalid', 'value': '3fc23d96-ebda-4859-9075-bed11d889b36.8ac3f2b33942.69a084ed', 'domain': '.ziprecruiter.com', 'path': '/'},
    {'name': 'zva', 'value': '123468826%3Bvid%3AaaCE2-WS9O-e1Ajd', 'domain': '.ziprecruiter.com', 'path': '/'},
]

BASE_URL = "https://www.ziprecruiter.com/jobs-search"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Build resume profile text for TF-IDF comparison
RESUME_PROFILE = " ".join(RESUME_KEYWORDS)
MAX_WORKERS = 3  # Parallel browser instances


def compute_match_pct(description):
    """Use TF-IDF cosine similarity between resume keywords and job description."""
    if not description or len(description.strip()) < 20:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([RESUME_PROFILE, description])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(score * 100, 1)
    except Exception:
        return 0.0


def extract_jobs_from_page(page):
    """Click each job card, read description from right pane, score it."""
    jobs = []

    companies = page.query_selector_all('[data-testid="job-card-company"]')
    locations = page.query_selector_all('[data-testid="job-card-location"]')
    total = len(companies)
    logging.info(f"Found {total} job cards on page")

    for i, comp_el in enumerate(companies):
        try:
            card = comp_el.evaluate_handle(
                'el => el.closest("li") || el.closest("div[role=\\"button\\"]") || el.parentElement.parentElement.parentElement.parentElement'
            )

            all_text = card.inner_text()
            lines = [l.strip() for l in all_text.split("\n") if l.strip()]

            company = comp_el.inner_text().strip()
            location = locations[i].inner_text().strip() if i < len(locations) else "N/A"

            title = "N/A"
            for line in lines:
                if line != company and line != location and len(line) > 3 and not line.startswith("$"):
                    title = line
                    break

            link = card.query_selector("a[href]")
            url = link.get_attribute("href") if link else "N/A"
            if url and not url.startswith("http"):
                url = "https://www.ziprecruiter.com" + url

            salary = "N/A"
            for line in lines:
                if "$" in line or "year" in line.lower() or "hour" in line.lower():
                    salary = line
                    break

            # Click card to load full description
            description = ""
            try:
                card.click()
                page.wait_for_timeout(1200)
                detail_pane = page.query_selector('[data-testid="job-details-scroll-container"]')
                if detail_pane:
                    description = detail_pane.inner_text()
            except Exception as e:
                logging.debug(f"Could not load description for card {i}: {e}")

            match_pct = compute_match_pct(f"{title} {description}")

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "match_pct": match_pct,
                "description": description[:500] if description else "",
                "url": url,
                "date_scraped": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            logging.info(f"  [{i+1}/{total}] {title} @ {company} — {match_pct}% match")

        except Exception as e:
            logging.debug(f"Error parsing card {i}: {e}")

    return jobs


def scrape_ziprecruiter(search_term, location="United States", days=1):
    """Scrape ZipRecruiter for a single search term using Playwright."""
    url = f"{BASE_URL}?search={search_term}&location={location}&days={days}"
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA)
        context.add_cookies(COOKIES)
        page = context.new_page()

        try:
            logging.info(f"[Thread] Searching: '{search_term}'...")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(6000)

            page_title = page.title()
            logging.info(f"[Thread] Page: {page_title}")

            jobs = extract_jobs_from_page(page)
            for j in jobs:
                j["search_title"] = search_term

            logging.info(f"[Thread] Done: {len(jobs)} jobs for '{search_term}'")

        except Exception as e:
            logging.error(f"Error scraping '{search_term}': {e}")
        finally:
            browser.close()

    return jobs


def search_all_titles(location="United States", days=1):
    """Search ZipRecruiter for all configured job titles using parallel threads."""
    all_jobs = []
    logging.info(f"Starting parallel scrape with {MAX_WORKERS} workers for {len(SEARCH_TITLES)} titles...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(scrape_ziprecruiter, title, location, days): title
            for title in SEARCH_TITLES
        }

        for future in as_completed(futures):
            title = futures[future]
            try:
                jobs = future.result()
                all_jobs.extend(jobs)
                logging.info(f"Collected {len(jobs)} from '{title}' (total so far: {len(all_jobs)})")
            except Exception as e:
                logging.error(f"Thread failed for '{title}': {e}")

    if not all_jobs:
        logging.warning("No jobs found across all search titles.")
        return pd.DataFrame()

    df = pd.DataFrame(all_jobs)
    df.drop_duplicates(subset=["title", "company"], inplace=True)
    df = df.sort_values(by="match_pct", ascending=False)

    logging.info(f"Total unique jobs: {len(df)}")
    return df


def save_to_csv(df, filename="jobs.csv"):
    try:
        if df is None:
            df = pd.DataFrame()
        df.to_csv(filename, index=False)
        logging.info(f"Saved {len(df)} jobs to {filename}")
    except Exception as e:
        logging.error(f"Error saving CSV: {e}")


def save_to_notes(df, filename="job_notes.txt"):
    try:
        with open(filename, "w") as f:
            f.write("# ZipRecruiter Job Listings\n")
            f.write(f"# Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

            if df is None or df.empty:
                f.write("# Total Jobs: 0\n")
                f.write("# No jobs found.\n")
            else:
                f.write(f"# Total Jobs: {len(df)}\n")
                f.write("=" * 50 + "\n\n")

                for i, (_, row) in enumerate(df.iterrows(), 1):
                    f.write(f"--- Job #{i} ---\n")
                    f.write(f"  Title:       {row.get('title', 'N/A')}\n")
                    f.write(f"  Company:     {row.get('company', 'N/A')}\n")
                    f.write(f"  Location:    {row.get('location', 'N/A')}\n")
                    f.write(f"  Salary:      {row.get('salary', 'N/A')}\n")
                    f.write(f"  Match:       {row.get('match_pct', 0)}%\n")
                    f.write(f"  URL:         {row.get('url', 'N/A')}\n\n")
        logging.info(f"Saved notes to {filename}")
    except Exception as e:
        logging.error(f"Error saving notes: {e}")


if __name__ == "__main__":
    results = search_all_titles(days=1)
    save_to_csv(results)
    save_to_notes(results)
