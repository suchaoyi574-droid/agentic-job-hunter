import json
from pathlib import Path


JOBS_PATH = Path("jobs.json")
MATCHES_PATH = Path("data/matches.json")
TOP_PATH = Path("data/top_jobs.json")


def load_json(path):

    if not path.exists():
        return {}

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def main():

    jobs_data = load_json(
        JOBS_PATH
    )

    matches_data = load_json(
        MATCHES_PATH
    )

    top_data = load_json(
        TOP_PATH
    )


    jobs = jobs_data.get(
        "jobs",
        []
    )

    matches = matches_data.get(
        "matches",
        []
    )

    top_jobs = top_data.get(
        "top_jobs",
        []
    )


    print("\n================================")
    print("AGENT EVALUATION REPORT")
    print("================================")


    # ------------------------------
    # Job Search Metrics
    # ------------------------------

    print("\n[Job Search]")

    print(
        f"Jobs collected: {len(jobs)}"
    )


    urls = [
        job.get("url")
        for job in jobs
    ]


    duplicate_count = (
        len(urls)
        -
        len(set(urls))
    )


    duplicate_rate = 0

    if urls:

        duplicate_rate = (
            duplicate_count
            /
            len(urls)
            *
            100
        )


    print(
        f"Duplicate rate: "
        f"{duplicate_rate:.2f}%"
    )


    # ------------------------------
    # Matching Metrics
    # ------------------------------

    print("\n[Matching]")


    print(
        f"Jobs evaluated: "
        f"{len(matches)}"
    )


    scores = [
        match.get(
            "match_score",
            0
        )
        for match in matches
    ]


    if scores:

        average = (
            sum(scores)
            /
            len(scores)
        )

        print(
            f"Average match score: "
            f"{average:.2f}"
        )

        print(
            f"Highest score: "
            f"{max(scores)}"
        )

        print(
            f"Lowest score: "
            f"{min(scores)}"
        )


    # ------------------------------
    # Ranking Metrics
    # ------------------------------

    print("\n[Ranking]")


    print(
        f"Recommended jobs: "
        f"{len(top_jobs)}"
    )


    if top_jobs:

        print(
            "\nTop Recommendations:"
        )


        for index, job in enumerate(
            top_jobs,
            start=1,
        ):

            print(
                f"{index}. "
                f"{job['title']} "
                f"@ "
                f"{job['company']} "
                f"- "
                f"{job['match_score']}/100"
            )


    # ------------------------------
    # Final
    # ------------------------------

    print(
        "\n================================"
    )

    print(
        "Evaluation Complete"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    main()