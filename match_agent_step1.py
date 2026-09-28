import asyncio
import json
import os
from pathlib import Path

from browser_use import ChatDeepSeek
from browser_use.llm.messages import SystemMessage, UserMessage
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


RESUME_PATH = Path("data/resume.json")
JOBS_PATH = Path("jobs.json")
OUTPUT_PATH = Path("data/matches.json")


# =====================================================
# 1. 定义单个职位的匹配结果
# =====================================================

class JobMatch(BaseModel):
    title: str
    company: str

    match_score: int = Field(
        ge=0,
        le=100
    )

    matched_skills: list[str]
    missing_skills: list[str]

    transferable_strengths: list[str]

    reasons: list[str]

    recommendation: str


# =====================================================
# 2. 所有职位匹配结果
# =====================================================

class MatchResults(BaseModel):
    matches: list[JobMatch]


async def main():

    # =================================================
    # 3. 检查文件
    # =================================================

    if not RESUME_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/resume.json"
        )

    if not JOBS_PATH.exists():
        raise FileNotFoundError(
            "找不到 jobs.json"
        )


    # =================================================
    # 4. 读取数据
    # =================================================

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


    # =================================================
    # 5. DeepSeek
    # =================================================

    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(
            "没有找到 DEEPSEEK_API_KEY"
        )


    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        temperature=0.0,
    )


    # =================================================
    # 6. Matching Prompt
    # =================================================

    messages = [

        SystemMessage(
            content="""
You are an AI job matching system.

Your task is to compare a candidate resume
against job descriptions.

You must be strict and evidence-based.

Do NOT invent skills or experience.

Scoring guideline:

90-100:
Candidate satisfies almost all important requirements.

75-89:
Strong match with some missing requirements.

60-74:
Moderate match with several relevant skills.

40-59:
Weak match but some transferable experience exists.

0-39:
Major skill and experience gaps.

Important rules:

1. Only count a skill as matched if the resume
   explicitly supports it.

2. Do NOT treat unrelated experience as direct
   technical experience.

3. Transferable skills may be mentioned separately,
   but they should not artificially inflate the score.

4. If the candidate comes from another industry,
   identify transferable strengths honestly.

5. missing_skills should contain important skills
   required by the job but unsupported by the resume.

6. recommendation should briefly explain what the
   candidate should improve before applying.

Return one match result for every supplied job.
"""
        ),

        UserMessage(
            content=f"""
Compare this candidate resume:

================ RESUME ================

{json.dumps(resume, ensure_ascii=False, indent=2)}

========================================


Against these job openings:

================ JOBS ==================

{json.dumps(jobs, ensure_ascii=False, indent=2)}

========================================

Evaluate each job independently.
"""
        ),
    ]


    print("正在分析简历和职位匹配度...")


    # =================================================
    # 7. 调用 DeepSeek
    # =================================================

    response = await llm.ainvoke(
        messages,
        output_format=MatchResults,
    )

    result = response.completion


    # =================================================
    # 8. 保存 matches.json
    # =================================================

    OUTPUT_PATH.write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )


    # =================================================
    # 9. 打印结果
    # =================================================

    print("\n================================")
    print("JOB MATCH RESULTS")
    print("================================")


    for match in result.matches:

        print(
            f"\n{match.title} @ "
            f"{match.company}"
        )

        print(
            f"Match Score: "
            f"{match.match_score}/100"
        )


        print("\nMatched Skills:")

        if match.matched_skills:
            for skill in match.matched_skills:
                print(f"  + {skill}")
        else:
            print("  None")


        print("\nMissing Skills:")

        for skill in match.missing_skills:
            print(f"  - {skill}")


        print("\nTransferable Strengths:")

        for strength in match.transferable_strengths:
            print(f"  + {strength}")


        print("\nRecommendation:")
        print(match.recommendation)

        print(
            "\n--------------------------------"
        )


    print(
        "\n完整结果已经保存到 "
        "data/matches.json"
    )


if __name__ == "__main__":
    asyncio.run(main())