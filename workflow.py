import asyncio
import json
import os
import sys
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# =====================================================
# 项目路径
# =====================================================

PROJECT_ROOT = Path(__file__).parent.resolve()

TARGET_ROLES_PATH = PROJECT_ROOT / "data" / "target_roles.json"
JOBS_PATH = PROJECT_ROOT / "jobs.json"
MATCHES_PATH = PROJECT_ROOT / "data" / "matches.json"
TOP_JOBS_PATH = PROJECT_ROOT / "data" / "top_jobs.json"


# =====================================================
# Workflow State
# =====================================================

class WorkflowState(TypedDict):
    role_discovery_ok: bool
    search_ok: bool
    match_ok: bool
    rank_ok: bool

    jobs_found: int
    jobs_matched: int
    recommended_jobs: int

    error: str


# =====================================================
# 删除旧的中间结果
# =====================================================

def clean_old_outputs():
    files = [
        TARGET_ROLES_PATH,
        JOBS_PATH,
        MATCHES_PATH,
        TOP_JOBS_PATH,
    ]

    print("\n================================")
    print("CLEANING OLD WORKFLOW OUTPUTS")
    print("================================")

    for path in files:
        if path.exists():
            path.unlink()

            print(
                f"Deleted old file: "
                f"{path.relative_to(PROJECT_ROOT)}"
            )


# =====================================================
# 通用：运行 Python Script
# =====================================================

async def run_script(script_name: str) -> bool:

    print("\n================================")
    print(f"RUNNING: {script_name}")
    print("================================\n")

    env = os.environ.copy()

    # 避免 Windows 子进程中文乱码
    env["PYTHONIOENCODING"] = "utf-8"

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        script_name,
        cwd=str(PROJECT_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    assert process.stdout is not None

    while True:
        line = await process.stdout.readline()

        if not line:
            break

        print(
            line.decode(
                "utf-8",
                errors="replace",
            ),
            end="",
        )

    return_code = await process.wait()

    if return_code != 0:
        print(
            f"\nERROR: {script_name} "
            f"退出代码 = {return_code}"
        )

        return False

    return True


# =====================================================
# JSON Loader
# =====================================================

def load_json(path: Path):

    if not path.exists():
        raise FileNotFoundError(
            f"没有生成文件: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


# =====================================================
# Node 1
# Role Discovery
# =====================================================

async def role_discovery_node(
    state: WorkflowState,
):

    print("\n################################")
    print("NODE 1: ROLE DISCOVERY")
    print("################################")

    success = await run_script(
        "role_discovery.py"
    )

    if not success:
        return {
            "role_discovery_ok": False,
            "error": "Role Discovery failed.",
        }

    try:
        data = load_json(
            TARGET_ROLES_PATH
        )

        roles = data.get(
            "recommended_roles",
            [],
        )

        if not roles:
            raise ValueError(
                "没有生成推荐岗位"
            )

    except Exception as exc:

        return {
            "role_discovery_ok": False,
            "error": (
                f"Role Discovery output invalid: "
                f"{exc}"
            ),
        }

    print(
        f"\nRole Discovery 成功："
        f"{len(roles)} 个岗位方向"
    )

    return {
        "role_discovery_ok": True,
        "error": "",
    }


# =====================================================
# Role Discovery 路由
# =====================================================

def after_role_discovery(
    state: WorkflowState,
):

    if state["role_discovery_ok"]:
        return "search"

    return "end"


# =====================================================
# Node 2
# Job Search
# =====================================================

async def job_search_node(
    state: WorkflowState,
):

    print("\n################################")
    print("NODE 2: JOB SEARCH")
    print("################################")

    success = await run_script(
        "agent.py"
    )

    if not success:
        return {
            "search_ok": False,
            "error": "Job Search failed.",
        }

    try:

        data = load_json(
            JOBS_PATH
        )

        jobs = data.get(
            "jobs",
            [],
        )

        if not jobs:
            raise ValueError(
                "没有找到候选职位"
            )

    except Exception as exc:

        return {
            "search_ok": False,
            "error": (
                f"Job Search output invalid: "
                f"{exc}"
            ),
        }


    print(
        f"\nJob Search 成功："
        f"{len(jobs)} 个候选职位"
    )

    return {
        "search_ok": True,
        "jobs_found": len(jobs),
        "error": "",
    }


# =====================================================
# Job Search 路由
# =====================================================

def after_job_search(
    state: WorkflowState,
):

    if state["search_ok"]:
        return "match"

    return "end"


# =====================================================
# Node 3
# Matching
# =====================================================

async def matching_node(
    state: WorkflowState,
):

    print("\n################################")
    print("NODE 3: JOB MATCHING")
    print("################################")

    success = await run_script(
        "match_agent.py"
    )

    if not success:
        return {
            "match_ok": False,
            "error": "Matching Agent failed.",
        }


    try:

        jobs_data = load_json(
            JOBS_PATH
        )

        match_data = load_json(
            MATCHES_PATH
        )

        jobs = jobs_data.get(
            "jobs",
            [],
        )

        matches = match_data.get(
            "matches",
            [],
        )

        if not matches:
            raise ValueError(
                "没有生成匹配结果"
            )

        if len(matches) != len(jobs):
            raise ValueError(
                f"职位数量 {len(jobs)}，"
                f"匹配结果数量 {len(matches)}，"
                "两者不一致"
            )

    except Exception as exc:

        return {
            "match_ok": False,
            "error": (
                f"Matching output invalid: "
                f"{exc}"
            ),
        }


    print(
        f"\nMatching 成功："
        f"{len(matches)} 个职位已评分"
    )


    return {
        "match_ok": True,
        "jobs_matched": len(matches),
        "error": "",
    }


# =====================================================
# Matching 路由
# =====================================================

def after_matching(
    state: WorkflowState,
):

    if state["match_ok"]:
        return "rank"

    return "end"


# =====================================================
# Node 4
# Ranking
# =====================================================

async def ranking_node(
    state: WorkflowState,
):

    print("\n################################")
    print("NODE 4: FILTER + RANK")
    print("################################")

    success = await run_script(
        "rank_jobs.py"
    )

    if not success:
        return {
            "rank_ok": False,
            "error": "Ranking failed.",
        }


    try:

        data = load_json(
            TOP_JOBS_PATH
        )

        top_jobs = data.get(
            "top_jobs",
            [],
        )

    except Exception as exc:

        return {
            "rank_ok": False,
            "error": (
                f"Ranking output invalid: "
                f"{exc}"
            ),
        }


    print(
        f"\nRanking 完成："
        f"{len(top_jobs)} 个推荐岗位"
    )


    return {
        "rank_ok": True,
        "recommended_jobs": len(
            top_jobs
        ),
        "error": "",
    }


# =====================================================
# Build LangGraph
# =====================================================

def build_workflow():

    builder = StateGraph(
        WorkflowState
    )


    builder.add_node(
        "role_discovery",
        role_discovery_node,
    )

    builder.add_node(
        "job_search",
        job_search_node,
    )

    builder.add_node(
        "matching",
        matching_node,
    )

    builder.add_node(
        "ranking",
        ranking_node,
    )


    # START
    builder.add_edge(
        START,
        "role_discovery",
    )


    # Role Discovery
    builder.add_conditional_edges(
        "role_discovery",
        after_role_discovery,
        {
            "search": "job_search",
            "end": END,
        },
    )


    # Search
    builder.add_conditional_edges(
        "job_search",
        after_job_search,
        {
            "match": "matching",
            "end": END,
        },
    )


    # Matching
    builder.add_conditional_edges(
        "matching",
        after_matching,
        {
            "rank": "ranking",
            "end": END,
        },
    )


    # Ranking
    builder.add_edge(
        "ranking",
        END,
    )


    return builder.compile()


# =====================================================
# Main
# =====================================================

async def main():

    print(
        "\n================================"
    )

    print(
        "AGENTIC JOB HUNTER"
    )

    print(
        "FULL LANGGRAPH WORKFLOW"
    )

    print(
        "================================"
    )


    # ---------------------------------------------
    # 每次完整运行先清理旧 JSON
    # ---------------------------------------------

    clean_old_outputs()


    workflow = build_workflow()


    initial_state: WorkflowState = {

        "role_discovery_ok": False,
        "search_ok": False,
        "match_ok": False,
        "rank_ok": False,

        "jobs_found": 0,
        "jobs_matched": 0,
        "recommended_jobs": 0,

        "error": "",
    }


    final_state = await workflow.ainvoke(
        initial_state
    )


    # =================================================
    # 最终状态
    # =================================================

    print(
        "\n================================"
    )

    print(
        "WORKFLOW COMPLETE"
    )

    print(
        "================================"
    )


    print(
        f"Role Discovery: "
        f"{final_state['role_discovery_ok']}"
    )

    print(
        f"Job Search:     "
        f"{final_state['search_ok']}"
    )

    print(
        f"Matching:       "
        f"{final_state['match_ok']}"
    )

    print(
        f"Ranking:        "
        f"{final_state['rank_ok']}"
    )


    print(
        f"\nJobs Found:     "
        f"{final_state['jobs_found']}"
    )

    print(
        f"Jobs Matched:   "
        f"{final_state['jobs_matched']}"
    )

    print(
        f"Recommended:    "
        f"{final_state['recommended_jobs']}"
    )


    if final_state["error"]:

        print(
            f"\nERROR:\n"
            f"{final_state['error']}"
        )

        return


    # =================================================
    # 最终结果位置
    # =================================================

    print(
        "\n最终结果："
    )

    print(
        "data/top_jobs.json"
    )


if __name__ == "__main__":
    asyncio.run(main())