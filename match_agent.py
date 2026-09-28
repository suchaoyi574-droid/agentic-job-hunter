import asyncio
import json
import os
from pathlib import Path

from browser_use import ChatDeepSeek
from browser_use.llm.messages import SystemMessage, UserMessage
from database import get_connection, init_database, save_match
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


RESUME_PATH = Path("data/resume.json")
JOBS_PATH = Path("jobs.json")
OUTPUT_PATH = Path("data/matches.json")


class JobMatch(BaseModel):

    title: str
    company: str

    match_score: int = Field(
        ge=0,
        le=100,
    )

    matched_skills: list[str]
    missing_skills: list[str]
    transferable_strengths: list[str]
    reasons: list[str]
    recommendation: str


class MatchResults(BaseModel):
    matches: list[JobMatch]


async def main():

    if not RESUME_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/resume.json"
        )

    if not JOBS_PATH.exists():
        raise FileNotFoundError(
            "找不到 jobs.json"
        )


    resume = json.loads(
        RESUME_PATH.read_text(
            encoding="utf-8"
        )
    )

    jobs = json.loads(
        JOBS_PATH.read_text(
            encoding="utf-8"
        )
    )


    job_list = jobs.get(
        "jobs",
        [],
    )

    if not job_list:
        raise ValueError(
            "jobs.json 中没有职位"
        )


    api_key = os.getenv(
        "DEEPSEEK_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "没有找到 DEEPSEEK_API_KEY"
        )


    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        temperature=0.0,
    )


    messages = [

        SystemMessage(
            content="""
You are a strict resume-to-job matching system.

Compare every supplied job against the candidate's
actual resume.

Never invent skills or experience.


SCORING:

90-100:
Exceptional direct match.

75-89:
Strong match.

60-74:
Reasonable match.

40-59:
Weak but meaningful match.

20-39:
Large skill or experience gaps.

0-19:
Very little relevant overlap.


RULES:

1. matched_skills must be explicitly supported
   by the resume.

2. missing_skills should contain important
   requirements unsupported by the resume.

3. Transferable abilities belong in
   transferable_strengths, not matched_skills.

4. Do not inflate the score because the candidate
   is academically strong.

5. Consider seniority carefully.

An internship or entry-level position should not be
evaluated like a senior role.

6. Consider education requirements.

7. Consider domain knowledge.

8. recommendation must be practical and concise.

9. Return exactly one result for EVERY supplied job.

10. Preserve job title and company exactly.
"""
        ),

        UserMessage(
            content=f"""
Evaluate this candidate:

================ RESUME ================

{json.dumps(
    resume,
    ensure_ascii=False,
    indent=2
)}

========================================


Against ALL of these jobs:

================ JOBS ==================

{json.dumps(
    jobs,
    ensure_ascii=False,
    indent=2
)}

========================================


There are {len(job_list)} jobs.

Return exactly {len(job_list)} match results.
"""
        ),
    ]


    print(
        f"正在匹配 {len(job_list)} 个职位..."
    )


    response = await llm.ainvoke(
        messages,
        output_format=MatchResults,
    )

    result = response.completion


    if len(result.matches) != len(job_list):

        raise ValueError(
            f"应该返回 {len(job_list)} 个匹配结果，"
            f"实际返回 {len(result.matches)} 个"
        )


    # ===============================
    # 保存 JSON
    # ===============================

    OUTPUT_PATH.write_text(
        json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    # ===============================
    # 保存 SQLite
    # ===============================

    init_database()

    conn = get_connection()

    try:

        for match in result.matches:

            save_match(
                conn,
                match.model_dump(),
            )

            print(
                f"{match.match_score:3}/100  "
                f"{match.title} "
                f"@ {match.company}"
            )

        conn.commit()

    finally:

        conn.close()


    print(
        "\n匹配结果已保存："
        "data/matches.json"
    )


if __name__ == "__main__":
    asyncio.run(main())