import asyncio
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


# -------------------------
# 1. 定义一个职位的数据结构
# -------------------------
class Job(BaseModel):
    title: str
    company: str
    location: str
    url: str


# -------------------------
# 2. 定义整个搜索结果的数据结构
# -------------------------
class JobSearchResult(BaseModel):
    jobs: list[Job]


# -------------------------
# 3. 读取 DeepSeek API Key
# -------------------------
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("没有找到 DEEPSEEK_API_KEY，请检查 .env 文件")


async def main():
    # -------------------------
    # 4. 创建 DeepSeek 模型
    # -------------------------
    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )

    # -------------------------
    # 5. 给 Agent 一个更明确的任务
    # -------------------------
    task = """
    Search the web for exactly 3 current job openings related to:

    - AI Agent Engineer
    - LLM Engineer
    - Applied AI Engineer

    Requirements:
    - Find 3 different real job openings.
    - Prefer official company career pages or ATS pages
      such as Ashby, Greenhouse, or Lever.
    - Avoid job aggregators when a direct job URL is available.
    - For every job collect:
        1. job title
        2. company
        3. location
        4. direct job URL
    - Do NOT apply for any job.
    - Stop searching once 3 valid jobs have been collected.
    """

    # -------------------------
    # 6. 创建 Job Search Agent
    # -------------------------
    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=JobSearchResult,
    )

    # -------------------------
    # 7. 运行 Agent
    # -------------------------
    history = await agent.run(max_steps=15)

    result = history.final_result()

    if not result:
        print("没有获取到搜索结果")
        return

    # -------------------------
    # 8. 验证 JSON 数据
    # -------------------------
    parsed = JobSearchResult.model_validate_json(result)

    # -------------------------
    # 9. 保存到 jobs.json
    # -------------------------
    output_path = Path("jobs.json")

    output_path.write_text(
        parsed.model_dump_json(indent=2),
        encoding="utf-8",
    )

    # -------------------------
    # 10. 打印结果
    # -------------------------
    print("\n=== JOB SEARCH RESULT ===")

    for index, job in enumerate(parsed.jobs, start=1):
        print(f"\nJob {index}")
        print(f"Title:    {job.title}")
        print(f"Company:  {job.company}")
        print(f"Location: {job.location}")
        print(f"URL:      {job.url}")

    print("\n结果已经保存到 jobs.json")


if __name__ == "__main__":
    asyncio.run(main())