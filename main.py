import argparse
import sys
from scraper import search_ziprecruiter_jobs, save_to_csv

def main():
    parser = argparse.ArgumentParser(description="ZipRecruiter Job Scraper")
    parser.add_argument("--location", type=str, default="USA", help="Location for the job search")
    parser.add_argument("--limit", type=int, default=10, help="Number of results per title")
    parser.add_argument("--hours", type=int, default=24, help="Only jobs posted in the last N hours")
    parser.add_argument("--output", type=str, default="ziprecruiter_jobs.csv", help="Output CSV filename")

    args = parser.parse_args()

    print(f"--- ZipRecruiter Scraper ---")
    print(f"Searching for all titles in config.py")
    print(f"Location: {args.location}")
    print(f"Limit: {args.limit} per title")
    print(f"Freshness: {args.hours} hours")
    print(f"---------------------------")

    jobs_df = search_ziprecruiter_jobs(
        location=args.location,
        results_wanted=args.limit,
        hours_old=args.hours
    )

    if not jobs_df.empty:
        save_to_csv(jobs_df, args.output)
        print(f"Done! Results saved to {args.output}")
    else:
        print("No jobs found or an error occurred.")

if __name__ == "__main__":
    main()
