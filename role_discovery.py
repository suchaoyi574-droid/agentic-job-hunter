import asyncio
import json
import os
from pathlib import Path

from browser_use import ChatDeepSeek
from browser_use.llm.messages import SystemMessage, UserMessage
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


# =====================================================
# 文件路径
# =====================================================

RESUME_PATH = Path("data/resume.json")
OUTPUT_PATH = Path("data/target_roles.json")


# =====================================================
# 1. 单个推荐岗位
# =====================================================

class RoleSuggestion(BaseModel):
    title: str

    # 为什么这个岗位适合候选人
    reason: str

    # 简历中支持这个判断的证据
    resume_evidence: list[str]

    # 后面 Browser Agent 可以直接使用的搜索词
    search_queries: list[str]


# =====================================================
# 2. Role Discovery 最终输出
# =====================================================

class RoleDiscoveryResult(BaseModel):

    profile_summary: str

    recommended_roles: list[RoleSuggestion] = Field(
        min_length=3,
        max_length=5,
    )

    recommended_industries: list[str]


async def main():

    # =================================================
    # 3. 检查简历
    # =================================================

    if not RESUME_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/resume.json\n"
            "请先运行 resume_structurer.py"
        )


    # =================================================
    # 4. 读取结构化简历
    # =================================================

    resume = json.loads(
        RESUME_PATH.read_text(
            encoding="utf-8"
        )
    )


    # =================================================
    # 5. DeepSeek API Key
    # =================================================

    api_key = os.getenv(
        "DEEPSEEK_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "没有找到 DEEPSEEK_API_KEY，"
            "请检查 .env 文件"
        )


    # =================================================
    # 6. 创建 DeepSeek
    # =================================================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        temperature=0.0,
    )


    # =================================================
    # 7. Role Discovery Prompt
    # =================================================

    messages = [

        SystemMessage(
            content="""
You are a career role discovery system.

Your job is to analyze a candidate's resume and
identify job roles that realistically match their
CURRENT demonstrated skills, education, projects,
and experience.

IMPORTANT RULES:

1. Only use evidence that appears in the resume.

2. Do NOT invent skills or experience.

3. Prioritize roles the candidate could realistically
   apply for with their current profile.

4. Do not optimize for prestige or salary.

5. Do not assume the candidate has software,
   programming, AI, or engineering skills unless
   explicitly supported by the resume.

6. Recommend between 3 and 5 job roles.

7. Job titles should be realistic titles commonly used
   by employers.

8. For every role, provide resume evidence explaining
   why the role is relevant.

9. For every role, generate 2 to 4 concise English
   search queries that could be used directly on job
   boards or search engines.

10. Search queries should include useful keywords such
    as role name, field, or industry.

Example query style:

"analytical chemistry research associate"
"pharmaceutical QC analyst"
"drug discovery research assistant"

11. recommended_industries should contain industries
    that are reasonably supported by the resume.

The goal is NOT to tell the candidate what career they
must choose.

The goal is to generate realistic job-search directions
based on evidence in the resume.
"""
        ),

        UserMessage(
            content=f"""
Analyze the following candidate resume and identify
realistic job roles and search queries.

================ RESUME ================

{json.dumps(
    resume,
    ensure_ascii=False,
    indent=2
)}

========================================
"""
        ),
    ]


    print(
        "正在根据简历发现适合的岗位方向..."
    )


    # =================================================
    # 8. 调用 DeepSeek
    # =================================================

    response = await llm.ainvoke(
        messages,
        output_format=RoleDiscoveryResult,
    )

    result = response.completion


    # =================================================
    # 9. 保存 target_roles.json
    # =================================================

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    # =================================================
    # 10. 打印结果
    # =================================================

    print(
        "\n================================"
    )

    print(
        "ROLE DISCOVERY RESULTS"
    )

    print(
        "================================"
    )


    print(
        "\nCandidate Profile:"
    )

    print(
        result.profile_summary
    )


    print(
        "\nRecommended Industries:"
    )

    for industry in (
        result.recommended_industries
    ):

        print(
            f"  - {industry}"
        )


    print(
        "\nRecommended Roles:"
    )


    for index, role in enumerate(
        result.recommended_roles,
        start=1,
    ):

        print(
            f"\n{index}. {role.title}"
        )

        print(
            f"Reason: {role.reason}"
        )

        print(
            "\nResume Evidence:"
        )

        for evidence in (
            role.resume_evidence
        ):

            print(
                f"  + {evidence}"
            )

        print(
            "\nSearch Queries:"
        )

        for query in (
            role.search_queries
        ):

            print(
                f"  > {query}"
            )


    print(
        "\n================================"
    )

    print(
        "结果已保存到："
    )

    print(
        "data/target_roles.json"
    )

    print(
        "================================"
    )


if __name__ == "__main__":
    asyncio.run(main())