import asyncio
import os
from pathlib import Path

from browser_use import ChatDeepSeek
from browser_use.llm.messages import SystemMessage, UserMessage
from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


RESUME_TEXT_PATH = Path("data/resume.txt")
OUTPUT_PATH = Path("data/resume.json")


# ==============================
# 定义简历的数据结构
# ==============================

class WorkExperience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    highlights: list[str]


class Project(BaseModel):
    name: str
    description: str | None = None
    technologies: list[str]
    highlights: list[str]


class Education(BaseModel):
    school: str | None = None
    degree: str | None = None
    major: str | None = None
    duration: str | None = None


class ResumeProfile(BaseModel):
    summary: str
    skills: list[str]
    work_experience: list[WorkExperience]
    projects: list[Project]
    education: list[Education]


async def main():

    # ==============================
    # 1. 检查 resume.txt
    # ==============================

    if not RESUME_TEXT_PATH.exists():
        raise FileNotFoundError(
            "找不到 data/resume.txt，请先运行 resume_parser.py"
        )

    resume_text = RESUME_TEXT_PATH.read_text(
        encoding="utf-8"
    )


    # ==============================
    # 2. 获取 DeepSeek Key
    # ==============================

    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(
            "没有找到 DEEPSEEK_API_KEY"
        )


    # ==============================
    # 3. 创建 DeepSeek
    # ==============================

    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
        temperature=0.0,
    )


    # ==============================
    # 4. 让 DeepSeek 理解简历
    # ==============================

    messages = [
        SystemMessage(
            content="""
You are a resume information extraction system.

Extract structured information from the candidate's resume.

Rules:

- Only use information explicitly supported by the resume.
- Do NOT invent skills.
- Do NOT invent work experience.
- Do NOT invent project technologies.
- If information is unavailable, use null or an empty list.
- Keep project and experience highlights concise.
- Normalize obvious technology names such as Python, Docker,
  FastAPI, LangChain, PyTorch, AWS, SQL, etc.
"""
        ),

        UserMessage(
            content=f"""
Extract the candidate profile from this resume:

---------------- RESUME ----------------

{resume_text}

--------------- END RESUME --------------
"""
        ),
    ]


    print("正在让 DeepSeek 分析简历...")


    # ==============================
    # 5. Structured Output
    # ==============================

    response = await llm.ainvoke(
        messages,
        output_format=ResumeProfile,
    )

    profile = response.completion


    # ==============================
    # 6. 保存 resume.json
    # ==============================

    OUTPUT_PATH.write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )


    print("\n==============================")
    print("RESUME STRUCTURING SUCCESS")
    print("==============================")

    print(f"\nSkills ({len(profile.skills)}):")

    for skill in profile.skills:
        print(f"  - {skill}")

    print(
        f"\nWork Experience: "
        f"{len(profile.work_experience)}"
    )

    print(
        f"Projects: "
        f"{len(profile.projects)}"
    )

    print(
        f"Education: "
        f"{len(profile.education)}"
    )

    print(
        "\n结果已经保存到 data/resume.json"
    )


if __name__ == "__main__":
    asyncio.run(main())