import asyncio
import json
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from database import get_connection, init_database, save_job
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


# =====================================================
# 文件路径
# =====================================================

TARGET_ROLES_PATH = Path("data/target_roles.json")
OUTPUT_PATH = Path("jobs.json")


# =====================================================
# 1. 职位数据结构
# =====================================================

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
        min_length=3,
        max_length=3,
    )


# =====================================================
# 2. DeepSeek API Key
# =====================================================

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件"
    )


# =====================================================
# 3. 读取 Role Discovery 结果
# =====================================================

def load_target_roles() -> dict:

    if not TARGET_ROLES_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/target_roles.json\n"
            "请先运行：uv run role_discovery.py"
        )

    return json.loads(
        TARGET_ROLES_PATH.read_text(
            encoding="utf-8"
        )
    )


# =====================================================
# 4. 把 Role Discovery 结果转成搜索计划
# =====================================================

def build_search_plan(role_data: dict) -> str:

    roles = role_data.get(
        "recommended_roles",
        [],
    )

    if not roles:
        raise ValueError(
            "target_roles.json 中没有 recommended_roles"
        )

    parts = []

    for index, role in enumerate(
        roles,
        start=1,
    ):

        title = role.get(
            "title",
            "Unknown Role",
        )

        queries = role.get(
            "search_queries",
            [],
        )

        parts.append(
            f"\nRole {index}: {title}"
        )

        for query in queries:
            parts.append(
                f"- Search query: {query}"
            )

    return "\n".join(parts)


async def main():

    # =================================================
    # 5. 读取推荐岗位
    # =================================================

    role_data = load_target_roles()

    search_plan = build_search_plan(
        role_data
    )


    print(
        "\n================================"
    )

    print(
        "RESUME-AWARE JOB SEARCH"
    )

    print(
        "================================"
    )

    print(
        "\nRole Discovery 提供的搜索方向："
    )

    print(
        search_plan
    )


    # =================================================
    # 6. 创建 DeepSeek
    # =================================================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )


    # =================================================
    # 7. 动态生成搜索任务
    # =================================================

    task = f"""
You are a resume-aware job search agent.

A previous Role Discovery Agent analyzed the
candidate's resume and generated the following
realistic target roles and search queries:

================ TARGET ROLES ================

{search_plan}

================================================


Your task is to find exactly 3 CURRENT job openings
that are realistically related to these recommended
roles.

IMPORTANT:

The search targets above were generated from the
candidate's actual resume.

Do NOT ignore them and switch to unrelated job fields.

For example:

- Do NOT search AI Engineer jobs unless AI roles
  appear in TARGET ROLES.
- Do NOT search senior software jobs for a candidate
  whose profile only supports junior or internship work.


SEARCH STRATEGY:

1. Use the provided search queries as starting points.

2. You may reformulate queries when necessary.

3. Prefer roles appropriate for:
   - interns
   - fresh graduates
   - junior candidates
   - assistants
   - entry-level candidates

   when those levels are consistent with the supplied
   target roles.

4. The 3 jobs MUST come from 3 DIFFERENT companies.

5. Prefer current and active listings.

6. Prefer direct sources such as:
   - official company careers pages
   - Greenhouse
   - Lever
   - Ashby
   - company recruitment pages

7. If an official page cannot be found, a reputable
   job listing page may be used.

8. Avoid obviously expired listings.

9. Do not return multiple jobs from the same company.


FOR EACH JOB:

Open the actual job listing and extract:

- job title
- company
- location
- short description
- important skills
- experience requirement
- direct job URL


DATA QUALITY RULES:

- Skills must be supported by the job description.

- Do NOT invent requirements.

- If years of experience are not specified, return:

  "Not specified"

- Description should be a concise 2-4 sentence
  summary.

- Do not copy the entire job description.


SAFETY:

Do NOT apply for jobs.

Do NOT submit application forms.

Do NOT create accounts.

Do NOT upload candidate information.


Stop searching once 3 valid jobs from
3 different companies have been collected.
"""


    # =================================================
    # 8. 创建 Browser Agent
    # =================================================

    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=JobSearchResult,
    )


    # =================================================
    # 9. 运行搜索
    # =================================================

    history = await agent.run(
        max_steps=25
    )

    result = history.final_result()

    if not result:

        print(
            "没有获取到职位结果"
        )

        return


    # =================================================
    # 10. Structured Output
    # =================================================

    parsed = (
        JobSearchResult
        .model_validate_json(
            result
        )
    )


    # =================================================
    # 11. 检查公司是否重复
    # =================================================

    companies = [
        job.company.strip().lower()
        for job in parsed.jobs
    ]

    if len(set(companies)) != len(companies):

        print(
            "\nWARNING:"
        )

        print(
            "Agent 返回了重复公司。"
        )

        print(
            "本次结果不保存。"
        )

        return


    # =================================================
    # 12. 保存 SQLite
    # =================================================

    init_database()

    conn = get_connection()

    try:

        for job in parsed.jobs:

            job_id = save_job(
                conn,
                job.model_dump(),
            )

            print(
                f"\nSaved to database: "
                f"{job.title} "
                f"@ {job.company} "
                f"(ID: {job_id})"
            )

        conn.commit()

    finally:

        conn.close()


    # =================================================
    # 13. 保存 jobs.json
    # =================================================

    OUTPUT_PATH.write_text(
        json.dumps(
            parsed.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    # =================================================
    # 14. 打印搜索结果
    # =================================================

    print(
        "\n================================"
    )

    print(
        "RESUME-AWARE JOB RESULTS"
    )

    print(
        "================================"
    )


    for index, job in enumerate(
        parsed.jobs,
        start=1,
    ):

        print(
            f"\nJob {index}"
        )

        print(
            "--------------------------------"
        )

        print(
            f"Title:      {job.title}"
        )

        print(
            f"Company:    {job.company}"
        )

        print(
            f"Location:   {job.location}"
        )

        print(
            f"Experience: {job.experience}"
        )


        print(
            "\nSkills:"
        )

        if job.skills:

            for skill in job.skills:

                print(
                    f"  - {skill}"
                )

        else:

            print(
                "  Not specified"
            )


        print(
            "\nDescription:"
        )

        print(
            job.description
        )


        print(
            f"\nURL: {job.url}"
        )


    # =================================================
    # 15. 完成
    # =================================================

    print(
        "\n================================"
    )

    print(
        "JOB SEARCH COMPLETE"
    )

    print(
        "================================"
    )

    print(
        "\n搜索依据："
    )

    print(
        "data/target_roles.json"
    )

    print(
        "\n职位已保存到："
    )

    print(
        "1. jobs.json"
    )

    print(
        "2. SQLite database"
    )


if __name__ == "__main__":
    asyncio.run(main())