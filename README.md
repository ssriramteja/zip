# ZipRecruiter Scraper

A lightweight Python tool to scrape job listings from ZipRecruiter using `python-jobspy` or direct cookie-based requests.

## Setup

1.  **Clone/Download** this repository.
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### 1. Recommended Way: JobSpy (No cookies needed)

Run the main script to search for jobs.

```bash
python main.py --search "Data Engineer" --location "Raleigh, NC" --limit 50
```

**Arguments:**
-   `--search`: Job title (default: "Data Engineer")
-   `--location`: City/State (default: "Raleigh, NC")
-   `--limit`: Maximum number of results (default: 50)
-   `--hours`: Max age of postings in hours (default: 72)
-   `--output`: Output filename (default: `ziprecruiter_jobs.csv`)

### 2. Manual Way: Cookie-Based

If you need full control or encounter bot detection, use `cookie_scraper.py`. You will need to extract cookies manually from your browser:
1.  Log into ZipRecruiter in Chrome.
2.  Open DevTools -> Application -> Cookies.
3.  Copy `_zip_auth_token` and `_session_id`.
4.  Update the template in `cookie_scraper.py` or import it into your script.

## Output

The scraper generates a CSV file with the following fields:
-   `title`
-   `company`
-   `location`
-   `salary` (if available)
-   `description`
-   `job_url`
-   `date_posted`
