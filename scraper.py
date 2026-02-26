import pandas as pd
from jobspy import scrape_jobs
import logging
import re
from config import SEARCH_TITLES, RESUME_KEYWORDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_match_score(description, title):
    if not description or pd.isna(description):
        return 0
    
    score = 0
    text = f"{title} {description}".lower()
    
    for word in RESUME_KEYWORDS:
        if re.search(rf"\b{re.escape(word.lower())}\b", text):
            score += 1
            
    return score

def search_ziprecruiter_jobs(location="USA", results_wanted=20, hours_old=24):
    """
    Scrapes jobs from ZipRecruiter using python-jobspy for all SEARCH_TITLES.
    """
    all_jobs = []
    
    for title in SEARCH_TITLES:
        logging.info(f"Searching for '{title}' in '{location}' (last {hours_old}h)...")
        try:
            jobs = scrape_jobs(
                site_name=["zip_recruiter"],
                search_term=title,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                job_type="fulltime"
            )
            if not jobs.empty:
                jobs['search_title'] = title
                all_jobs.append(jobs)
                logging.info(f"Found {len(jobs)} jobs for '{title}'")
            else:
                logging.info(f"No jobs found for '{title}'")
        except Exception as e:
            logging.error(f"Error scraping '{title}': {e}")
            
    if not all_jobs:
        return pd.DataFrame()
        
    combined_df = pd.concat(all_jobs, ignore_index=True)
    combined_df.drop_duplicates(subset=['job_url'], inplace=True)
    
    # Apply scoring
    logging.info("Calculating match scores...")
    combined_df['match_score'] = combined_df.apply(
        lambda x: calculate_match_score(x.get('description', ''), x.get('title', '')), axis=1
    )
    
    # Sort by score
    combined_df = combined_df.sort_values(by='match_score', ascending=False)
    
    return combined_df

def save_to_csv(df, filename="ziprecruiter_jobs.csv"):
    """
    Saves the job results DataFrame to a CSV file.
    """
    if df.empty:
        logging.warning("No jobs to save.")
        return
        
    try:
        df.to_csv(filename, index=False)
        logging.info(f"Successfully saved {len(df)} jobs to {filename}")
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")

if __name__ == "__main__":
    # Test run
    results = search_ziprecruiter_jobs(results_wanted=5)
    save_to_csv(results)
