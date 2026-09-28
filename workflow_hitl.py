import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from database import get_connection, init_database
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from workflow import (
    TOP_JOBS_PATH,
    after_job_search,
    after_matching,
    after_role_discovery,
    clean_old_outputs,
    job_search_node,
    load_json,
    matching_node,
    ranking_node,
    role_discovery_node,
)


PROJECT_ROOT = Path(__file__).parent.resolve()

CHECKPOINT_DB = (
    PROJECT_ROOT
    / "data"
    / "workflow_checkpoints.db"
)


# =====================================================
# Workflow State
# =====================================================

class HITLState(TypedDict):
    role_discovery_ok: bool
    search_ok: bool
    match_ok: bool
    rank_ok: bool

    jobs_found: int
    jobs_matched: int
    recommended_jobs: int

    top_jobs: list[dict]

    review_decisions: dict[str, str]

    error: str


# =====================================================
# Ranking Wrapper
# 把 top_jobs.json 读回 LangGraph State
# =====================================================

async def ranking_with_jobs_node(
    state: HITLState,
):

    result = await ranking_node(state)

    if not result.get("rank_ok"):
        return result

    data = load_json(
        TOP_JOBS_PATH
    )

    top_jobs = data.get(
        "top_jobs",
        [],
    )

    return {
        **result,
        "top_jobs": top_jobs,
        "recommended_jobs": len(top_jobs),
    }


# =====================================================
# Ranking 后决定是否需要人工审核
# =====================================================

def after_ranking(
    state: HITLState,
):

    if not state["rank_ok"]:
        return "end"

    if state["recommended_jobs"] == 0:
        return "end"

    return "review"


# =====================================================
# Human Review Node
#
# 注意：
# interrupt 前不要执行数据库写入等副作用。
# 因为恢复时这个 node 会重新执行。
# =====================================================

def human_review_node(
    state: HITLState,
):

    top_jobs = state["top_jobs"]

    review_payload = {
        "type": "job_review",
        "message": (
            "Review recommended jobs before "
            "any further action."
        ),
        "jobs": [
            {
                "rank": index,
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "match_score": job["match_score"],
                "url": job["url"],
            }
            for index, job in enumerate(
                top_jobs,
                start=1,
            )
        ],
    }

    # ===============================
    # LangGraph 在这里暂停
    # ===============================

    decisions = interrupt(
        review_payload
    )

    # 恢复后 decisions 会从这里返回
    return {
        "review_decisions": decisions
    }


# =====================================================
# 给现有数据库增加人工审核字段
# =====================================================

def ensure_review_columns(
    conn,
):

    rows = conn.execute(
        "PRAGMA table_info(jobs)"
    ).fetchall()

    columns = {
        row["name"]
        for row in rows
    }

    if "user_decision" not in columns:

        conn.execute(
            """
            ALTER TABLE jobs
            ADD COLUMN user_decision
            TEXT NOT NULL
            DEFAULT 'pending'
            """
        )

    if "reviewed_at" not in columns:

        conn.execute(
            """
            ALTER TABLE jobs
            ADD COLUMN reviewed_at TEXT
            """
        )

    conn.commit()


# =====================================================
# 把人工决定保存进 SQLite
# =====================================================

def save_review_node(
    state: HITLState,
):

    init_database()

    conn = get_connection()

    ensure_review_columns(
        conn
    )

    decisions = state.get(
        "review_decisions",
        {},
    )

    top_jobs = state.get(
        "top_jobs",
        [],
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()


    print(
        "\n================================"
    )

    print(
        "SAVING HUMAN REVIEW"
    )

    print(
        "================================"
    )


    try:

        for job in top_jobs:

            url = job["url"]

            decision = decisions.get(
                url,
                "skip",
            )


            row = conn.execute(
                """
                SELECT
                    id,
                    title,
                    company,
                    status
                FROM jobs
                WHERE url = ?
                """,
                (url,),
            ).fetchone()


            if not row:

                print(
                    f"WARNING: "
                    f"数据库找不到职位："
                    f"{job['title']}"
                )

                continue


            current_status = (
                row["status"]
            )

            new_status = (
                current_status
            )


            # ===========================
            # approve 不等于 apply
            #
            # approve 只代表：
            # “我人工审核过，愿意继续”
            # ===========================

            if (
                decision == "approve"
                and current_status
                == "matched"
            ):
                new_status = "reviewed"


            conn.execute(
                """
                UPDATE jobs

                SET
                    user_decision = ?,
                    reviewed_at = ?,
                    status = ?,
                    updated_at = ?

                WHERE id = ?
                """,
                (
                    decision,
                    timestamp,
                    new_status,
                    timestamp,
                    row["id"],
                ),
            )


            print(
                f"\n{job['title']} "
                f"@ {job['company']}"
            )

            print(
                f"Decision: {decision}"
            )

            print(
                f"Status: "
                f"{current_status}"
                f" -> "
                f"{new_status}"
            )


        conn.commit()

    finally:

        conn.close()


    return {}


# =====================================================
# Build HITL Graph
# =====================================================

def build_hitl_workflow(
    checkpointer,
):

    builder = StateGraph(
        HITLState
    )


    # ===============================
    # Nodes
    # ===============================

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
        ranking_with_jobs_node,
    )

    builder.add_node(
        "human_review",
        human_review_node,
    )

    builder.add_node(
        "save_review",
        save_review_node,
    )


    # ===============================
    # Edges
    # ===============================

    builder.add_edge(
        START,
        "role_discovery",
    )


    builder.add_conditional_edges(
        "role_discovery",
        after_role_discovery,
        {
            "search": "job_search",
            "end": END,
        },
    )


    builder.add_conditional_edges(
        "job_search",
        after_job_search,
        {
            "match": "matching",
            "end": END,
        },
    )


    builder.add_conditional_edges(
        "matching",
        after_matching,
        {
            "rank": "ranking",
            "end": END,
        },
    )


    builder.add_conditional_edges(
        "ranking",
        after_ranking,
        {
            "review": "human_review",
            "end": END,
        },
    )


    builder.add_edge(
        "human_review",
        "save_review",
    )


    builder.add_edge(
        "save_review",
        END,
    )


    return builder.compile(
        checkpointer=checkpointer
    )


# =====================================================
# 人工输入
# =====================================================

def collect_human_decisions(
    jobs: list[dict],
) -> dict[str, str]:

    decisions = {}


    print(
        "\n================================"
    )

    print(
        "HUMAN REVIEW REQUIRED"
    )

    print(
        "================================"
    )

    print(
        "\nA = Approve"
    )

    print(
        "S = Skip"
    )

    print(
        "R = Reject"
    )

    print(
        "\nApprove 只表示："
        "允许进入后续流程，"
        "不会自动投递。"
    )


    for job in jobs:

        print(
            "\n--------------------------------"
        )

        print(
            f"#{job['rank']} "
            f"{job['title']} "
            f"@ {job['company']}"
        )

        print(
            f"Match Score: "
            f"{job['match_score']}/100"
        )

        print(
            f"Location: "
            f"{job['location']}"
        )

        print(
            f"URL: "
            f"{job['url']}"
        )


        while True:

            answer = input(
                "\n[A]pprove / "
                "[S]kip / "
                "[R]eject: "
            )

            answer = (
                answer
                .strip()
                .lower()
            )


            if answer in {
                "a",
                "approve",
            }:

                decision = "approve"

                break


            if answer in {
                "s",
                "skip",
            }:

                decision = "skip"

                break


            if answer in {
                "r",
                "reject",
            }:

                decision = "reject"

                break


            print(
                "请输入 A、S 或 R。"
            )


        decisions[
            job["url"]
        ] = decision


    return decisions


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
        "HUMAN-IN-THE-LOOP WORKFLOW"
    )

    print(
        "================================"
    )


    # 每次开启一轮新的 Job Hunt
    thread_id = (
        "job-hunt-"
        + str(uuid.uuid4())
    )


    print(
        f"\nThread ID:"
        f"\n{thread_id}"
    )


    # 清理上一轮普通输出
    clean_old_outputs()


    CHECKPOINT_DB.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    async with (
        AsyncSqliteSaver
        .from_conn_string(
            str(CHECKPOINT_DB)
        )
    ) as checkpointer:


        graph = build_hitl_workflow(
            checkpointer
        )


        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }


        initial_state: HITLState = {

            "role_discovery_ok": False,
            "search_ok": False,
            "match_ok": False,
            "rank_ok": False,

            "jobs_found": 0,
            "jobs_matched": 0,
            "recommended_jobs": 0,

            "top_jobs": [],

            "review_decisions": {},

            "error": "",
        }


        # ===========================
        # 第一次运行
        #
        # 会一直执行到 interrupt()
        # ===========================

        result = await graph.ainvoke(
            initial_state,
            config=config,
        )


        # ===========================
        # 是否暂停等待人工输入
        # ===========================

        interrupts = result.get(
            "__interrupt__",
            (),
        )


        if interrupts:

            interrupt_value = (
                interrupts[0].value
            )

            jobs = interrupt_value.get(
                "jobs",
                [],
            )


            decisions = (
                collect_human_decisions(
                    jobs
                )
            )


            # =======================
            # 恢复 LangGraph
            # =======================

            result = (
                await graph.ainvoke(
                    Command(
                        resume=decisions
                    ),
                    config=config,
                )
            )


        # ===========================
        # Final
        # ===========================

        print(
            "\n================================"
        )

        print(
            "HITL WORKFLOW COMPLETE"
        )

        print(
            "================================"
        )


        print(
            f"Role Discovery: "
            f"{result['role_discovery_ok']}"
        )

        print(
            f"Job Search:     "
            f"{result['search_ok']}"
        )

        print(
            f"Matching:       "
            f"{result['match_ok']}"
        )

        print(
            f"Ranking:        "
            f"{result['rank_ok']}"
        )


        print(
            f"\nJobs Found:     "
            f"{result['jobs_found']}"
        )

        print(
            f"Jobs Matched:   "
            f"{result['jobs_matched']}"
        )

        print(
            f"Recommended:    "
            f"{result['recommended_jobs']}"
        )


        print(
            "\nHuman review 已保存到 SQLite。"
        )


        print(
            "\nCheckpoint:"
        )

        print(
            CHECKPOINT_DB
        )


if __name__ == "__main__":
    asyncio.run(main())