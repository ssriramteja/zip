import argparse
from scraper import search_jobs, save_to_csv, save_to_notes

def main():
    parser = argparse.ArgumentParser(description="Job Scraper (Indeed + LinkedIn + ZipRecruiter)")
    parser.add_argument("--location", type=str, default="USA", help="Location for the job search")
    parser.add_argument("--limit", type=int, default=15, help="Number of results per title")
    parser.add_argument("--hours", type=int, default=24, help="Only jobs posted in the last N hours")
    parser.add_argument("--output", type=str, default="jobs.csv", help="Output CSV filename")
    parser.add_argument("--notes", type=str, default="job_notes.txt", help="Output notes filename")

    args = parser.parse_args()

    print(f"--- Job Scraper ---")
    print(f"Sources: Indeed, LinkedIn, ZipRecruiter")
    print(f"Location: {args.location}")
    print(f"Limit: {args.limit} per title")
    print(f"Freshness: {args.hours} hours")
    print(f"-------------------")

    jobs_df = search_jobs(
        location=args.location,
        results_wanted=args.limit,
        hours_old=args.hours
    )

    save_to_csv(jobs_df, args.output)
    save_to_notes(jobs_df, args.notes)

    if not jobs_df.empty:
        print(f"Done! {len(jobs_df)} jobs saved to {args.output} and {args.notes}")
    else:
        print("No jobs found. Empty files created for tracking.")

if __name__ == "__main__":
    main()
