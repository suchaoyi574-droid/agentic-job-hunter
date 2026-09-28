import json
from pathlib import Path


JOBS_PATH = Path("jobs.json")
MATCHES_PATH = Path("data/matches.json")
OUTPUT_PATH = Path("data/top_jobs.json")


# =====================================================
# 最低推荐分数
# =====================================================

MIN_RECOMMENDED_SCORE = 50
TOP_N = 3


def normalize(text: str) -> str:
    return text.strip().lower()


def main():

    if not JOBS_PATH.exists():

        raise FileNotFoundError(
            "找不到 jobs.json"
        )


    if not MATCHES_PATH.exists():

        raise FileNotFoundError(
            "找不到 data/matches.json"
        )


    jobs_data = json.loads(
        JOBS_PATH.read_text(
            encoding="utf-8"
        )
    )


    matches_data = json.loads(
        MATCHES_PATH.read_text(
            encoding="utf-8"
        )
    )


    jobs = jobs_data.get(
        "jobs",
        [],
    )


    matches = matches_data.get(
        "matches",
        [],
    )


    # =================================================
    # 建立 Match Lookup
    # =================================================

    match_lookup = {}


    for match in matches:

        key = (
            normalize(
                match["title"]
            ),
            normalize(
                match["company"]
            ),
        )

        match_lookup[key] = match


    # =================================================
    # Job + Match 合并
    # =================================================

    combined = []


    for job in jobs:

        key = (
            normalize(
                job["title"]
            ),
            normalize(
                job["company"]
            ),
        )


        match = match_lookup.get(
            key
        )


        if not match:
            continue


        combined.append(
            {
                "title":
                    job["title"],

                "company":
                    job["company"],

                "location":
                    job["location"],

                "url":
                    job["url"],

                "source_role":
                    job.get(
                        "source_role",
                        "Unknown",
                    ),

                "match_score":
                    match[
                        "match_score"
                    ],

                "matched_skills":
                    match[
                        "matched_skills"
                    ],

                "missing_skills":
                    match[
                        "missing_skills"
                    ],

                "transferable_strengths":
                    match[
                        "transferable_strengths"
                    ],

                "recommendation":
                    match[
                        "recommendation"
                    ],
            }
        )


    # =================================================
    # 排序
    # =================================================

    combined.sort(
        key=lambda item:
        item["match_score"],
        reverse=True,
    )


    # =================================================
    # 只保留达到推荐阈值的岗位
    # =================================================

    recommended = [
        job
        for job in combined
        if job["match_score"]
        >= MIN_RECOMMENDED_SCORE
    ]


    top_jobs = recommended[
        :TOP_N
    ]


    # =================================================
    # 保存结果
    # =================================================

    result = {

        "minimum_recommended_score":
            MIN_RECOMMENDED_SCORE,

        "candidate_jobs_evaluated":
            len(combined),

        "recommended_jobs_found":
            len(recommended),

        "top_jobs":
            top_jobs,
    }


    # 如果没有达到阈值的岗位，
    # 保存几个最高分岗位用于调试，
    # 但明确标记它们不是推荐结果。
    if not top_jobs:

        result[
            "message"
        ] = (
            "No suitable jobs reached "
            "the recommendation threshold."
        )

        result[
            "best_available_not_recommended"
        ] = combined[:3]


    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    # =================================================
    # 没有合格岗位
    # =================================================

    if not top_jobs:

        print(
            "\n================================"
        )

        print(
            "NO SUITABLE JOBS FOUND"
        )

        print(
            "================================"
        )


        print(
            f"\n没有岗位达到最低推荐分数："
            f"{MIN_RECOMMENDED_SCORE}/100"
        )


        if combined:

            print(
                "\n本轮最高分岗位仅供诊断："
            )


            for index, job in enumerate(
                combined[:3],
                start=1,
            ):

                print(
                    f"\n#{index} "
                    f"{job['title']} "
                    f"@ {job['company']}"
                )

                print(
                    f"Score: "
                    f"{job['match_score']}/100"
                )


        print(
            "\n这些岗位不会被标记为推荐岗位。"
        )


        print(
            "\n结果保存到："
            "data/top_jobs.json"
        )

        return


    # =================================================
    # 有合格岗位
    # =================================================

    print(
        "\n================================"
    )

    print(
        "TOP RECOMMENDED JOBS"
    )

    print(
        "================================"
    )


    for rank, job in enumerate(
        top_jobs,
        start=1,
    ):

        print(
            f"\n#{rank}"
        )

        print(
            f"{job['title']} "
            f"@ {job['company']}"
        )

        print(
            f"Match Score: "
            f"{job['match_score']}/100"
        )

        print(
            f"Source Role: "
            f"{job['source_role']}"
        )

        print(
            f"Location: "
            f"{job['location']}"
        )


        print(
            "\nMatched Skills:"
        )


        if job["matched_skills"]:

            for skill in (
                job["matched_skills"]
            ):

                print(
                    f"  + {skill}"
                )

        else:

            print(
                "  None"
            )


        print(
            "\nMissing Skills:"
        )


        if job["missing_skills"]:

            for skill in (
                job["missing_skills"]
            ):

                print(
                    f"  - {skill}"
                )

        else:

            print(
                "  None"
            )


        print(
            "\nRecommendation:"
        )

        print(
            job["recommendation"]
        )


        print(
            f"\nURL: "
            f"{job['url']}"
        )


        print(
            "\n--------------------------------"
        )


    print(
        "\n结果保存到："
        "data/top_jobs.json"
    )


if __name__ == "__main__":
    main()