import asyncio
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


# =====================================================
# 1. 定义一个职位的数据结构
# =====================================================

class Job(BaseModel):
    title: str
    company: str
    location: str

    # 职位内容的简要总结
    description: str

    # JD 中提取出来的技能
    skills: list[str]

    # 经验要求，例如 "3+ years"
    experience: str

    # 直接职位链接
    url: str


# =====================================================
# 2. 定义搜索结果
#    强制要求正好 3 个职位
# =====================================================

class JobSearchResult(BaseModel):
    jobs: list[Job] = Field(
        min_length=3,
        max_length=3
    )


# =====================================================
# 3. DeepSeek API Key
# =====================================================

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件"
    )


async def main():

    # =================================================
    # 4. 创建 DeepSeek
    # =================================================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )


    # =================================================
    # 5. Job Search Agent 的任务
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
       - short description of the role
       - important technical skills
       - experience requirement
       - direct job URL

    Skill examples include:

    - Python
    - LLM
    - RAG
    - LangChain
    - LangGraph
    - MCP
    - Tool Calling
    - Agents
    - FastAPI
    - Docker
    - Kubernetes
    - AWS
    - GCP
    - PyTorch

    Rules:

    - Skills must come from or be clearly supported by the job description.
    - Do not invent an experience requirement.
    - If experience is not specified, return:
      "Not specified"

    - description should be a concise 2-4 sentence summary,
      NOT the entire job posting.

    - Do NOT apply for any job.
    - Do NOT submit forms.
    - Do NOT create accounts.

    Stop searching as soon as 3 valid jobs from
    3 different companies have been collected.
    """


    # =================================================
    # 6. 创建 Agent
    # =================================================

    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=JobSearchResult,
    )


    # =================================================
    # 7. 开始搜索
    # =================================================

    history = await agent.run(
        max_steps=20
    )

    result = history.final_result()

    if not result:
        print("没有获取到结果")
        return


    # =================================================
    # 8. JSON -> Python 对象
    # =================================================

    parsed = JobSearchResult.model_validate_json(result)


    # =================================================
    # 9. 再检查一次公司有没有重复
    # =================================================

    companies = [
        job.company.strip().lower()
        for job in parsed.jobs
    ]

    if len(set(companies)) != len(companies):
        print("WARNING: Agent 返回了重复公司。")
        print("这次结果不符合要求。")
        return


    # =================================================
    # 10. 保存 jobs.json
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


    for index, job in enumerate(parsed.jobs, start=1):

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
    print("结果已经保存到 jobs.json")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())