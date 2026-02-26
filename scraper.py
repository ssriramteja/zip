"""
ZipRecruiter Scraper using Playwright with cookies.
Bypasses Cloudflare by using a real browser with session cookies.
"""
import json
import time
import re
import pandas as pd
import logging
from datetime import datetime
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


def calculate_match_score(text):
    if not text:
        return 0
    score = 0
    text_lower = text.lower()
    for kw in RESUME_KEYWORDS:
        if re.search(rf"\b{re.escape(kw.lower())}\b", text_lower):
            score += 1
    return score


def extract_jobs_from_page(page):
    """Extract job data from a loaded ZipRecruiter search results page."""
    jobs = []

    companies = page.query_selector_all('[data-testid="job-card-company"]')
    locations = page.query_selector_all('[data-testid="job-card-location"]')

    for i, comp_el in enumerate(companies):
        try:
            # Walk up to the job card container
            card = comp_el.evaluate_handle("el => el.closest('li') || el.closest('div[role=\"button\"]') || el.parentElement.parentElement.parentElement.parentElement")

            # Get all text lines from the card to find the title (first bold text)
            all_text = card.inner_text()
            lines = [l.strip() for l in all_text.split("\n") if l.strip()]

            company = comp_el.inner_text().strip()
            location = locations[i].inner_text().strip() if i < len(locations) else "N/A"

            # Title is typically the first line that isn't the company name
            title = "N/A"
            for line in lines:
                if line != company and line != location and len(line) > 3 and not line.startswith("$"):
                    title = line
                    break

            # Try to find a URL from the card
            link = card.query_selector("a[href]")
            url = link.get_attribute("href") if link else "N/A"
            if url and not url.startswith("http"):
                url = "https://www.ziprecruiter.com" + url

            # Try to get salary info
            salary = "N/A"
            for line in lines:
                if "$" in line or "year" in line.lower() or "hour" in line.lower():
                    salary = line
                    break

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "salary": salary,
                "url": url,
                "date_scraped": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        except Exception as e:
            logging.debug(f"Error parsing card {i}: {e}")

    return jobs


def scrape_ziprecruiter(search_term, location="United States", days=1):
    """Scrape ZipRecruiter for a single search term."""
    url = f"{BASE_URL}?search={search_term}&location={location}&days={days}"
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA)
        context.add_cookies(COOKIES)
        page = context.new_page()

        try:
            logging.info(f"Loading: {search_term} in {location}...")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(6000)

            page_title = page.title()
            logging.info(f"Page: {page_title}")

            jobs = extract_jobs_from_page(page)
            logging.info(f"Extracted {len(jobs)} jobs for '{search_term}'")

        except Exception as e:
            logging.error(f"Error scraping '{search_term}': {e}")
        finally:
            browser.close()

    return jobs


def search_all_titles(location="United States", days=1):
    """Search ZipRecruiter for all configured job titles."""
    all_jobs = []

    for title in SEARCH_TITLES:
        jobs = scrape_ziprecruiter(title, location=location, days=days)
        for j in jobs:
            j["search_title"] = title
        all_jobs.extend(jobs)
        time.sleep(2)  # Rate limit

    if not all_jobs:
        logging.warning("No jobs found across all search titles.")
        return pd.DataFrame()

    df = pd.DataFrame(all_jobs)
    df.drop_duplicates(subset=["title", "company"], inplace=True)

    # Score each job
    df["match_score"] = df.apply(
        lambda x: calculate_match_score(f"{x.get('title', '')} {x.get('company', '')}"),
        axis=1
    )
    df = df.sort_values(by="match_score", ascending=False)

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
                    f.write(f"  Match Score: {row.get('match_score', 0)}\n")
                    f.write(f"  URL:         {row.get('url', 'N/A')}\n\n")
        logging.info(f"Saved notes to {filename}")
    except Exception as e:
        logging.error(f"Error saving notes: {e}")


if __name__ == "__main__":
    results = search_all_titles(days=1)
    save_to_csv(results)
    save_to_notes(results)
