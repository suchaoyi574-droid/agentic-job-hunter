import asyncio
import json
import os
from pathlib import Path

from browser_use import ChatDeepSeek
from browser_use.llm.messages import SystemMessage, UserMessage
from database import get_connection, init_database, save_match
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# =====================================================
# 1. 加载环境变量
# =====================================================

load_dotenv()


# =====================================================
# 2. 文件路径
# =====================================================

RESUME_PATH = Path("data/resume.json")
JOBS_PATH = Path("jobs.json")
OUTPUT_PATH = Path("data/matches.json")


# =====================================================
# 3. 定义单个职位匹配结果
# =====================================================

class JobMatch(BaseModel):

    title: str
    company: str

    # 0 - 100
    match_score: int = Field(
        ge=0,
        le=100,
    )

    # 简历中明确支持的技能
    matched_skills: list[str]

    # JD 要求但简历没有体现的技能
    missing_skills: list[str]

    # 跨行业也可以迁移过去的能力
    transferable_strengths: list[str]

    # 为什么给这个分数
    reasons: list[str]

    # 给求职者的改进建议
    recommendation: str


# =====================================================
# 4. 所有职位匹配结果
# =====================================================

class MatchResults(BaseModel):

    matches: list[JobMatch] = Field(
        min_length=3,
        max_length=3,
    )


async def main():

    # =================================================
    # 5. 检查数据文件是否存在
    # =================================================

    if not RESUME_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/resume.json\n"
            "请先运行 resume_structurer.py"
        )

    if not JOBS_PATH.exists():
        raise FileNotFoundError(
            "找不到 jobs.json\n"
            "请先运行 agent.py 搜索职位"
        )


    # =================================================
    # 6. 读取 resume.json
    # =================================================

    resume = json.loads(
        RESUME_PATH.read_text(
            encoding="utf-8"
        )
    )


    # =================================================
    # 7. 读取 jobs.json
    # =================================================

    jobs = json.loads(
        JOBS_PATH.read_text(
            encoding="utf-8"
        )
    )

    job_list = jobs.get("jobs", [])

    if len(job_list) != 3:
        raise ValueError(
            f"jobs.json 中应该有 3 个职位，"
            f"但现在有 {len(job_list)} 个"
        )


    # =================================================
    # 8. 获取 DeepSeek API Key
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
    # 9. 创建 DeepSeek
    # =================================================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        temperature=0.0,
    )


    # =================================================
    # 10. Matching Agent Prompt
    # =================================================

    messages = [

        SystemMessage(
            content="""
You are a strict AI job matching system.

Your task is to compare a candidate resume against
multiple AI engineering job descriptions.

You must be evidence-based.

Do NOT invent skills.
Do NOT invent experience.
Do NOT assume the candidate knows something unless
the resume explicitly supports it.


MATCH SCORE GUIDELINE

90-100:
Candidate satisfies almost all important requirements
and has directly relevant experience.

75-89:
Strong match, but some requirements are missing.

60-74:
Moderate match with several relevant technical skills.

40-59:
Weak match, but meaningful relevant or transferable
experience exists.

20-39:
Large technical gaps with limited direct relevance.

0-19:
Very little direct technical overlap.


IMPORTANT RULES

1. matched_skills:

Only include skills that are explicitly supported by
the candidate resume.

Do NOT infer programming or AI skills from unrelated
academic or laboratory experience.


2. missing_skills:

Include important technical skills required by the
job but unsupported by the resume.


3. transferable_strengths:

These are abilities that could transfer between fields,
such as:

- analytical thinking
- research
- experimental design
- communication
- documentation
- problem solving
- teaching
- project coordination

Transferable strengths should NOT artificially increase
the technical match score.


4. reasons:

Explain the most important evidence behind the score.


5. recommendation:

Give a short and practical recommendation describing
what the candidate would need to improve for this role.


6. Evaluate every supplied job independently.

Return exactly one match result for every job.
"""
        ),

        UserMessage(
            content=f"""
Compare the following candidate resume against the
following 3 job openings.


================ RESUME ================

{json.dumps(
    resume,
    ensure_ascii=False,
    indent=2
)}

========================================


================ JOBS ==================

{json.dumps(
    jobs,
    ensure_ascii=False,
    indent=2
)}

========================================


Return one evaluation for each job.

The title and company in your result must match the
corresponding job title and company exactly.
"""
        ),
    ]


    # =================================================
    # 11. 调用 DeepSeek
    # =================================================

    print(
        "正在分析简历和职位匹配度..."
    )

    response = await llm.ainvoke(
        messages,
        output_format=MatchResults,
    )

    result = response.completion


    # =================================================
    # 12. 基础结果检查
    # =================================================

    if len(result.matches) != len(job_list):

        raise ValueError(
            "Matching Agent 返回的职位数量"
            "和 jobs.json 不一致"
        )


    # =================================================
    # 13. 保存 matches.json
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
    # 14. 自动保存匹配结果到 SQLite
    # =================================================

    init_database()

    conn = get_connection()

    try:

        for match in result.matches:

            save_match(
                conn,
                match.model_dump(),
            )

            print(
                f"Saved match: "
                f"{match.title} @ "
                f"{match.company} "
                f"({match.match_score}/100)"
            )

        conn.commit()

    finally:

        conn.close()


    # =================================================
    # 15. 打印结果
    # =================================================

    print(
        "\n================================"
    )

    print(
        "JOB MATCH RESULTS"
    )

    print(
        "================================"
    )


    for match in result.matches:

        print(
            f"\n{match.title} "
            f"@ {match.company}"
        )

        print(
            f"Match Score: "
            f"{match.match_score}/100"
        )


        # ---------------------------------------------
        # Matched Skills
        # ---------------------------------------------

        print(
            "\nMatched Skills:"
        )

        if match.matched_skills:

            for skill in match.matched_skills:

                print(
                    f"  + {skill}"
                )

        else:

            print(
                "  None"
            )


        # ---------------------------------------------
        # Missing Skills
        # ---------------------------------------------

        print(
            "\nMissing Skills:"
        )

        if match.missing_skills:

            for skill in match.missing_skills:

                print(
                    f"  - {skill}"
                )

        else:

            print(
                "  None"
            )


        # ---------------------------------------------
        # Transferable Strengths
        # ---------------------------------------------

        print(
            "\nTransferable Strengths:"
        )

        if match.transferable_strengths:

            for strength in (
                match.transferable_strengths
            ):

                print(
                    f"  + {strength}"
                )

        else:

            print(
                "  None"
            )


        # ---------------------------------------------
        # Reasons
        # ---------------------------------------------

        print(
            "\nReasons:"
        )

        for reason in match.reasons:

            print(
                f"  - {reason}"
            )


        # ---------------------------------------------
        # Recommendation
        # ---------------------------------------------

        print(
            "\nRecommendation:"
        )

        print(
            match.recommendation
        )


        print(
            "\n--------------------------------"
        )


    # =================================================
    # 16. 完成
    # =================================================

    print(
        "\n================================"
    )

    print(
        "MATCHING COMPLETE"
    )

    print(
        "================================"
    )

    print(
        "\n结果已经保存到："
    )

    print(
        "1. data/matches.json"
    )

    print(
        "2. SQLite database"
    )


if __name__ == "__main__":
    asyncio.run(main())