import asyncio
import json
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from database import get_connection, init_database, save_job
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


TARGET_ROLES_PATH = Path("data/target_roles.json")
OUTPUT_PATH = Path("jobs.json")


class Job(BaseModel):
    title: str
    company: str
    location: str
    description: str
    skills: list[str]
    experience: str
    url: str


class JobSearchResult(BaseModel):
    jobs: list[Job] = Field(
        min_length=10,
        max_length=10,
    )


api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件"
    )


def load_target_roles() -> dict:

    if not TARGET_ROLES_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/target_roles.json\n"
            "请先运行 role_discovery.py"
        )

    return json.loads(
        TARGET_ROLES_PATH.read_text(
            encoding="utf-8"
        )
    )


def build_search_plan(role_data: dict) -> str:

    roles = role_data.get(
        "recommended_roles",
        [],
    )

    if not roles:
        raise ValueError(
            "target_roles.json 中没有 recommended_roles"
        )

    lines = []

    for index, role in enumerate(
        roles,
        start=1,
    ):

        lines.append(
            f"\nRole {index}: {role['title']}"
        )

        for query in role.get(
            "search_queries",
            [],
        ):
            lines.append(
                f"- {query}"
            )

    return "\n".join(lines)


async def main():

    role_data = load_target_roles()

    search_plan = build_search_plan(
        role_data
    )


    print(
        "\n================================"
    )
    print(
        "RESUME-AWARE CANDIDATE SEARCH"
    )
    print(
        "================================"
    )

    print(search_plan)


    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )


    task = f"""
You are a resume-aware job discovery agent.

A Role Discovery Agent analyzed the candidate's
resume and produced these realistic job directions:

================ TARGET ROLES ================

{search_plan}

================================================


Find exactly 10 CURRENT job openings.

GOAL:

Build a diverse candidate-job pool which will later
be scored by a separate Matching Agent.

RULES:

1. Jobs must be related to the TARGET ROLES.

2. Prefer roles appropriate for:
   - interns
   - fresh graduates
   - entry-level candidates
   - junior candidates
   - research assistants
   - laboratory assistants

3. Avoid senior positions unless the target-role
   information clearly supports them.

4. The 10 jobs should preferably come from
   10 DIFFERENT companies.

5. Never return duplicate job URLs.

6. Try to cover multiple recommended role categories
   instead of searching only one role.

7. Prefer current active listings.

8. Prefer:
   - official career pages
   - company recruitment pages
   - Greenhouse
   - Lever
   - Ashby

9. Reputable job boards may be used when an official
   listing cannot be found.

10. Do not invent job information.


FOR EACH JOB:

Open the listing when possible and collect:

- title
- company
- location
- short job description
- important skills
- experience requirement
- direct URL


If experience is not specified:

"Not specified"


The description must be concise.

Do NOT apply for jobs.

Do NOT submit forms.

Do NOT create accounts.

Do NOT upload candidate data.

Stop after 10 valid candidate jobs have been collected.
"""


    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=JobSearchResult,
    )


    history = await agent.run(
        max_steps=60
    )

    result = history.final_result()

    if not result:
        print(
            "没有获取到职位"
        )
        return


    parsed = (
        JobSearchResult
        .model_validate_json(
            result
        )
    )


    # 检查重复 URL
    urls = [
        job.url.strip().lower()
        for job in parsed.jobs
    ]

    if len(set(urls)) != len(urls):

        print(
            "WARNING: 出现重复职位 URL。"
        )

        print(
            "本次结果不保存。"
        )

        return


    # ===============================
    # SQLite
    # ===============================

    init_database()

    conn = get_connection()

    try:

        for job in parsed.jobs:

            job_id = save_job(
                conn,
                job.model_dump(),
            )

            print(
                f"Saved: "
                f"{job.title} @ "
                f"{job.company} "
                f"(ID {job_id})"
            )

        conn.commit()

    finally:

        conn.close()


    # ===============================
    # jobs.json
    # ===============================

    OUTPUT_PATH.write_text(
        json.dumps(
            parsed.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print(
        "\n================================"
    )
    print(
        "10 CANDIDATE JOBS FOUND"
    )
    print(
        "================================"
    )

    for index, job in enumerate(
        parsed.jobs,
        start=1,
    ):

        print(
            f"\n{index}. "
            f"{job.title} @ "
            f"{job.company}"
        )

        print(
            f"Location: {job.location}"
        )

        print(
            f"URL: {job.url}"
        )


    print(
        "\n10 个候选职位已保存到 jobs.json"
    )


if __name__ == "__main__":
    asyncio.run(main())