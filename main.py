import argparse
from scraper import search_all_titles, save_to_csv, save_to_notes

def main():
    parser = argparse.ArgumentParser(description="ZipRecruiter Job Scraper")
    parser.add_argument("--location", type=str, default="United States", help="Location")
    parser.add_argument("--days", type=int, default=1, help="Jobs posted within last N days")
    parser.add_argument("--output", type=str, default="jobs.csv", help="Output CSV")
    parser.add_argument("--notes", type=str, default="job_notes.txt", help="Output notes")

    args = parser.parse_args()

    print("--- ZipRecruiter Scraper (Playwright) ---")
    print(f"Location: {args.location}")
    print(f"Freshness: {args.days} day(s)")
    print("-" * 40)

    df = search_all_titles(location=args.location, days=args.days)

    save_to_csv(df, args.output)
    save_to_notes(df, args.notes)

    if not df.empty:
        print(f"\nDone! {len(df)} jobs saved to {args.output} and {args.notes}")
    else:
        print("\nNo jobs found. Empty files created.")

if __name__ == "__main__":
    main()
