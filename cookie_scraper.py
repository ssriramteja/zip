import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import logging
from config import SEARCH_TITLES, RESUME_KEYWORDS
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Provided cookies from user
COOKIES = {
    "last_click_event_ids": "019c9b1a-d5f8-7456-8b62-8837475435cc:...",
    "ziprecruiter_session": "df031e0ea4a14b4f2cf64f3f76a9d6ac",
    "ziprecruiter_browser": "005d251a-93f2-4f57-ad66-3a5119b6c4f0",
    "__cf_bm": "kSSfC7Si_NxsaMgLn3lqIF8rLPQvECb_BnzROu3n.Yw-1772127451-1.0.1.1-k4sK6YUbSX4RuEL14HD8Uv99ZsLjJjcja_l0LPmWWPHPzW296RAG0a2.2apE76j5XD07wCR7tXMdokqYt0wh9L_wBBcbYuhX9HiaNqAzHdtilGJOm2Nka2y4l6qHu_MR",
    "zglobalid": "3fc23d96-ebda-4859-9075-bed11d889b36.8ac3f2b33942.69a084ed",
    "zva": "123468826%3Bvid%3AaaCE2-WS9O-e1Ajd"
}

def calculate_match_score(text):
    if not text: return 0
    score = 0
    text = text.lower()
    for word in RESUME_KEYWORDS:
        if re.search(rf"\b{re.escape(word.lower())}\b", text):
            score += 1
    return score

def scrape_with_cookies(search="Data Engineer", location="Raleigh, NC", radius="25"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.ziprecruiter.com/"
    }

    base_url = "https://www.ziprecruiter.com/jobs-search"
    params = {
        "search": search,
        "location": location,
        "radius": radius,
        "days": 1 # ZipRecruiter parameter for fresh jobs
    }

    session = requests.Session()
    session.cookies.update(COOKIES)
    session.headers.update(headers)

    try:
        logging.info(f"Manual scrape for '{search}'...")
        response = session.get(base_url, params=params)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("article", class_="job_result")
        
        results = []
        for job in job_cards:
            try:
                title_elem = job.find("h2", class_="heading_6_5") or job.find("span", class_="job_title")
                company_elem = job.find("a", class_="company_name") or job.find("span", class_="company_name")
                location_elem = job.find("span", class_="location")
                link_elem = job.find("a", class_="job_link")
                
                if title_elem and company_elem:
                    title = title_elem.text.strip()
                    results.append({
                        "title": title,
                        "company": company_elem.text.strip(),
                        "location": location_elem.text.strip() if location_elem else "N/A",
                        "url": link_elem["href"] if link_elem else "N/A",
                        "match_score": calculate_match_score(title) # Limited scoring without description
                    })
            except Exception as e:
                logging.debug(f"Parsing error: {e}")
                
        return results
    except Exception as e:
        logging.error(f"Manual scrape failed: {e}")
        return []

if __name__ == "__main__":
    all_results = []
    for title in SEARCH_TITLES:
        jobs = scrape_with_cookies(search=title)
        all_results.extend(jobs)
        time.sleep(2)
    
    df = pd.DataFrame(all_results)
    if not df.empty:
        df.sort_values(by="match_score", ascending=False).to_csv("zip_manual_scrape.csv", index=False)
        print("Manual scrape complete. Saved to zip_manual_scrape.csv")
