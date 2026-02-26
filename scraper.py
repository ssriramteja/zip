import pandas as pd
from jobspy import scrape_jobs
import logging
import re
from config import SEARCH_TITLES, RESUME_KEYWORDS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SITES = ["indeed", "linkedin", "zip_recruiter"]

def calculate_match_score(description, title):
    if not description or pd.isna(description):
        return 0
    
    score = 0
    text = f"{title} {description}".lower()
    
    for word in RESUME_KEYWORDS:
        if re.search(rf"\b{re.escape(word.lower())}\b", text):
            score += 1
            
    return score

def search_jobs(location="USA", results_wanted=20, hours_old=24):
    """
    Scrapes jobs from Indeed, LinkedIn, and ZipRecruiter for all SEARCH_TITLES.
    """
    all_jobs = []
    
    for title in SEARCH_TITLES:
        logging.info(f"Searching for '{title}' in '{location}' (last {hours_old}h)...")
        try:
            jobs = scrape_jobs(
                site_name=SITES,
                search_term=title,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                job_type="fulltime",
                country_indeed="USA"
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
        logging.warning("No jobs found across all titles.")
        return pd.DataFrame()
        
    combined_df = pd.concat(all_jobs, ignore_index=True)
    combined_df.drop_duplicates(subset=['job_url'], inplace=True)
    
    logging.info("Calculating match scores...")
    combined_df['match_score'] = combined_df.apply(
        lambda x: calculate_match_score(x.get('description', ''), x.get('title', '')), axis=1
    )
    
    combined_df = combined_df.sort_values(by='match_score', ascending=False)
    logging.info(f"Total unique jobs after dedup: {len(combined_df)}")
    
    return combined_df

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
            f.write("# Job Listings - Scrape Results\n")
            f.write(f"# Sources: Indeed, LinkedIn, ZipRecruiter\n")
            f.write(f"# Last Run: {pd.Timestamp.now()}\n")
            
            if df is None or df.empty:
                f.write("# Total Jobs: 0\n")
                f.write("# No jobs found matching criteria.\n")
            else:
                f.write(f"# Total Jobs: {len(df)}\n")
                f.write("=" * 50 + "\n\n")
                
                for i, (_, row) in enumerate(df.iterrows(), 1):
                    f.write(f"--- Job #{i} ---\n")
                    f.write(f"  Title:       {row.get('title', 'N/A')}\n")
                    f.write(f"  Company:     {row.get('company', 'N/A')}\n")
                    f.write(f"  Location:    {row.get('location', 'N/A')}\n")
                    f.write(f"  Source:      {row.get('site', 'N/A')}\n")
                    f.write(f"  Match Score: {row.get('match_score', 0)}\n")
                    f.write(f"  URL:         {row.get('job_url', 'N/A')}\n")
                    f.write(f"  Posted:      {row.get('date_posted', 'N/A')}\n\n")
        logging.info(f"Saved notes to {filename}")
    except Exception as e:
        logging.error(f"Error saving notes: {e}")

if __name__ == "__main__":
    results = search_jobs(results_wanted=5)
    save_to_csv(results)
    save_to_notes(results)
