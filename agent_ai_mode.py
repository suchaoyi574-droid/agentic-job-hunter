import asyncio
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from database import get_connection, init_database, save_job
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


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


async def main():

    # =================================================
    # 3. 创建 DeepSeek
    # =================================================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )


    # =================================================
    # 4. Job Search Agent 任务
    # =================================================

    task = """
    You are a specialized AI job research agent.

    Find exactly 3 CURRENT job openings related to:

    - AI Agent Engineer
    - LLM Engineer
    - Applied AI Engineer
    - Agentic AI Engineer

    IMPORTANT:

    The 3 jobs MUST come from 3 DIFFERENT companies.

    Do not return multiple jobs from the same company.

    Prefer direct sources:
    - Official company career pages
    - Ashby
    - Greenhouse
    - Lever

    Avoid job aggregators when a direct job page is available.

    For EACH job:

    1. Open the actual job posting.
    2. Read the job description.
    3. Extract:

       - job title
       - company
       - location
       - short description
       - important technical skills
       - experience requirement
       - direct job URL

    Skills must be supported by the job description.

    Do not invent experience requirements.

    If experience is not specified, return:
    "Not specified"

    The description should be a concise 2-4 sentence summary.

    Do NOT apply for jobs.
    Do NOT submit forms.
    Do NOT create accounts.

    Stop searching once 3 valid jobs from
    3 different companies have been collected.
    """


    # =================================================
    # 5. 创建 Agent
    # =================================================

    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=JobSearchResult,
    )


    # =================================================
    # 6. 运行 Agent
    # =================================================

    history = await agent.run(
        max_steps=20
    )

    result = history.final_result()

    if not result:
        print("没有获取到结果")
        return


    # =================================================
    # 7. 解析 Structured Output
    # =================================================

    parsed = JobSearchResult.model_validate_json(
        result
    )


    # =================================================
    # 8. 检查是否来自不同公司
    # =================================================

    companies = [
        job.company.strip().lower()
        for job in parsed.jobs
    ]

    if len(set(companies)) != len(companies):
        print(
            "WARNING: Agent 返回了重复公司。"
        )
        print(
            "本次结果不写入数据库。"
        )
        return


    # =================================================
    # 9. 自动保存到 SQLite
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
                f"Saved to database: "
                f"{job.title} @ {job.company} "
                f"(ID: {job_id})"
            )

        conn.commit()

    finally:
        conn.close()


    # =================================================
    # 10. 同时保存 jobs.json
    # =================================================

    output_path = Path("jobs.json")

    output_path.write_text(
        parsed.model_dump_json(indent=2),
        encoding="utf-8",
    )


    # =================================================
    # 11. 打印结果
    # =================================================

    print("\n================================")
    print("JOB SEARCH RESULTS")
    print("================================")


    for index, job in enumerate(
        parsed.jobs,
        start=1,
    ):

        print(f"\nJob {index}")
        print("--------------------------------")

        print(f"Title:      {job.title}")
        print(f"Company:    {job.company}")
        print(f"Location:   {job.location}")
        print(f"Experience: {job.experience}")

        print("\nSkills:")

        for skill in job.skills:
            print(f"  - {skill}")

        print("\nDescription:")
        print(job.description)

        print(f"\nURL: {job.url}")


    print("\n================================")
    print("职位已经保存到：")
    print("1. jobs.json")
    print("2. SQLite database")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())