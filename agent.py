import asyncio
import json
import math
import os
from pathlib import Path

from browser_use import Agent, ChatDeepSeek
from database import get_connection, init_database, save_job
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


TARGET_ROLES_PATH = Path("data/target_roles.json")
OUTPUT_PATH = Path("jobs.json")

TARGET_JOB_COUNT = 10


# =====================================================
# 数据结构
# =====================================================

class Job(BaseModel):
    title: str
    company: str
    location: str
    description: str
    skills: list[str]
    experience: str
    url: str

    # 这个职位是根据哪个推荐岗位搜出来的
    source_role: str


class RoleJobSearchResult(BaseModel):
    jobs: list[Job]


# =====================================================
# API KEY
# =====================================================

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env"
    )


# =====================================================
# 读取 Role Discovery
# =====================================================

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


# =====================================================
# 针对一个岗位方向进行搜索
# =====================================================

async def search_one_role(
    llm,
    role: dict,
    jobs_needed: int,
) -> list[Job]:

    role_title = role["title"]

    queries = role.get(
        "search_queries",
        [],
    )

    evidence = role.get(
        "resume_evidence",
        [],
    )

    query_text = "\n".join(
        f"- {query}"
        for query in queries
    )

    evidence_text = "\n".join(
        f"- {item}"
        for item in evidence
    )


    print("\n================================")
    print("SEARCHING TARGET ROLE")
    print("================================")

    print(f"\n{role_title}")

    print("\nSearch queries:")
    print(query_text)


    task = f"""
You are a specialized job-search agent.

You are currently searching for ONE specific
candidate job category.

TARGET ROLE:

{role_title}


SEARCH QUERIES PROVIDED BY THE ROLE DISCOVERY AGENT:

{query_text}


WHY THIS ROLE MATCHES THE CANDIDATE:

{evidence_text}


Find approximately {jobs_needed} CURRENT job openings
that are genuinely related to THIS target role.


CRITICAL RULE:

You MUST stay within this career field.

Do NOT switch to unrelated careers.

For example:

If TARGET ROLE is pharmaceutical QC analyst,
do NOT search for:

- AI Engineer
- Software Engineer
- LLM Engineer
- Agent Engineer

If TARGET ROLE is chemistry teacher,
do NOT search pharmaceutical engineering jobs unless
the listing itself is clearly a chemistry teaching role.


SEARCH RULES:

1. Start with the supplied search queries.

2. You may slightly reformulate a query, but it must
   preserve the SAME profession and career field.

3. Prefer jobs appropriate for the candidate's
   demonstrated seniority.

4. Prefer:
   - internship
   - entry-level
   - junior
   - assistant
   - fresh graduate

5. Avoid senior roles unless absolutely appropriate.

6. Prefer currently active listings.

7. Prefer direct company career pages when available.

8. Reputable job boards are allowed when necessary.

9. Do not invent job information.

10. Do not apply for anything.


FOR EACH JOB:

Open or inspect the job listing and extract:

- title
- company
- location
- concise description
- important skills
- experience requirement
- URL

Set source_role EXACTLY to:

{role_title}


If experience is not specified, use:

"Not specified"


Return only jobs clearly related to:

{role_title}
"""


    agent = Agent(
        task=task,
        llm=llm,
        output_model_schema=RoleJobSearchResult,
    )


    history = await agent.run(
        max_steps=25
    )

    result = history.final_result()

    if not result:

        print(
            f"没有找到 {role_title} 的职位"
        )

        return []


    parsed = (
        RoleJobSearchResult
        .model_validate_json(
            result
        )
    )


    valid_jobs = []


    for job in parsed.jobs:

        # 不信任模型自己返回的 source_role，
        # 强制设置成当前真正的搜索方向
        job.source_role = role_title

        valid_jobs.append(job)


    return valid_jobs


# =====================================================
# 主程序
# =====================================================

async def main():

    role_data = load_target_roles()

    roles = role_data.get(
        "recommended_roles",
        [],
    )

    if not roles:
        raise ValueError(
            "target_roles.json 没有推荐岗位"
        )


    print("\n================================")
    print("STRICT RESUME-AWARE JOB SEARCH")
    print("================================")

    print(
        f"\nRole Discovery 提供了 "
        f"{len(roles)} 个岗位方向。"
    )


    # 根据岗位数量计算每个方向大概搜多少
    jobs_per_role = math.ceil(
        TARGET_JOB_COUNT
        / len(roles)
    )


    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )


    all_jobs = []

    seen_urls = set()


    # =================================================
    # 每个 Role 单独搜索
    # =================================================

    for role in roles:

        if len(all_jobs) >= TARGET_JOB_COUNT:
            break


        jobs = await search_one_role(
            llm,
            role,
            jobs_per_role,
        )


        for job in jobs:

            url_key = (
                job.url
                .strip()
                .lower()
            )


            if url_key in seen_urls:
                continue


            seen_urls.add(
                url_key
            )

            all_jobs.append(
                job
            )


            if (
                len(all_jobs)
                >= TARGET_JOB_COUNT
            ):
                break


    # =================================================
    # 检查数量
    # =================================================

    if not all_jobs:

        raise RuntimeError(
            "没有找到任何有效职位"
        )


    print(
        f"\n共找到 "
        f"{len(all_jobs)} 个候选职位。"
    )


    if len(all_jobs) < TARGET_JOB_COUNT:

        print(
            f"WARNING: 目标是 "
            f"{TARGET_JOB_COUNT} 个，"
            f"本次只找到 {len(all_jobs)} 个。"
        )


    # =================================================
    # 保存 SQLite
    # =================================================

    init_database()

    conn = get_connection()

    try:

        for job in all_jobs:

            job_id = save_job(
                conn,
                job.model_dump(),
            )

            print(
                f"Saved: "
                f"{job.title} "
                f"@ {job.company} "
                f"(ID {job_id})"
            )

        conn.commit()

    finally:

        conn.close()


    # =================================================
    # 保存 jobs.json
    # =================================================

    output = {
        "jobs": [
            job.model_dump()
            for job in all_jobs
        ]
    }


    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    # =================================================
    # 输出
    # =================================================

    print("\n================================")
    print("CANDIDATE JOB POOL")
    print("================================")


    for index, job in enumerate(
        all_jobs,
        start=1,
    ):

        print(
            f"\n#{index}"
        )

        print(
            f"{job.title} "
            f"@ {job.company}"
        )

        print(
            f"Source Role: "
            f"{job.source_role}"
        )

        print(
            f"Location: "
            f"{job.location}"
        )

        print(
            f"URL: "
            f"{job.url}"
        )


    print("\n================================")

    print(
        "候选职位已保存到 jobs.json"
    )

    print(
        "下一步运行 match_agent.py"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    asyncio.run(main())