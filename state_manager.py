import sys

from database import get_connection, init_database


# =====================================================
# 允许的状态变化
# =====================================================

ALLOWED_TRANSITIONS = {
    "discovered": {
        "matched",
    },

    "matched": {
        "reviewed",
    },

    "reviewed": {
        "applied",
        "rejected",
    },

    "applied": {
        "interview",
        "rejected",
    },

    "interview": {
        "offer",
        "rejected",
    },

    "offer": set(),

    "rejected": set(),
}


# =====================================================
# 查看所有职位
# =====================================================

def list_jobs():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            id,
            title,
            company,
            status
        FROM jobs
        ORDER BY id
        """
    ).fetchall()

    print("\n================================")
    print("APPLICATION STATES")
    print("================================")

    for row in rows:
        print(
            f"\nID: {row['id']}"
        )

        print(
            f"{row['title']} @ {row['company']}"
        )

        print(
            f"Status: {row['status']}"
        )

    print("\n================================")

    conn.close()


# =====================================================
# 更新职位状态
# =====================================================

def update_status(
    job_id: int,
    new_status: str,
):
    conn = get_connection()

    try:

        job = conn.execute(
            """
            SELECT
                id,
                title,
                company,
                status
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()

        if not job:
            print(
                f"找不到 Job ID {job_id}"
            )
            return


        current_status = job["status"]

        print(
            f"\n职位："
            f"{job['title']} @ {job['company']}"
        )

        print(
            f"当前状态：{current_status}"
        )

        print(
            f"目标状态：{new_status}"
        )


        # ---------------------------------------------
        # 检查目标状态是否合法
        # ---------------------------------------------

        if new_status not in ALLOWED_TRANSITIONS:

            print(
                f"\n非法状态：{new_status}"
            )

            print(
                "允许状态："
                + ", ".join(
                    ALLOWED_TRANSITIONS.keys()
                )
            )

            return


        # ---------------------------------------------
        # 检查当前状态
        # ---------------------------------------------

        if current_status not in ALLOWED_TRANSITIONS:

            print(
                f"\n数据库中存在未知状态："
                f"{current_status}"
            )

            return


        # ---------------------------------------------
        # 检查状态转换是否合法
        # ---------------------------------------------

        allowed = (
            ALLOWED_TRANSITIONS[
                current_status
            ]
        )

        if new_status not in allowed:

            print(
                "\n状态转换被拒绝。"
            )

            if allowed:

                print(
                    "当前允许转换到："
                )

                for status in allowed:
                    print(
                        f"  - {status}"
                    )

            else:

                print(
                    "当前状态已经是终止状态。"
                )

            return


        # ---------------------------------------------
        # 更新数据库
        # ---------------------------------------------

        conn.execute(
            """
            UPDATE jobs

            SET
                status = ?,
                updated_at = datetime('now')

            WHERE id = ?
            """,
            (
                new_status,
                job_id,
            ),
        )

        conn.commit()

        print(
            "\n状态更新成功："
        )

        print(
            f"{current_status}"
            f" -> "
            f"{new_status}"
        )

    finally:

        conn.close()


# =====================================================
# CLI
# =====================================================

def main():

    init_database()

    if len(sys.argv) == 1:

        list_jobs()
        return


    command = sys.argv[1]


    if command == "list":

        list_jobs()
        return


    if command == "update":

        if len(sys.argv) != 4:

            print(
                "用法："
            )

            print(
                "uv run state_manager.py "
                "update <job_id> <status>"
            )

            return


        job_id = int(
            sys.argv[2]
        )

        new_status = (
            sys.argv[3]
            .strip()
            .lower()
        )

        update_status(
            job_id,
            new_status,
        )

        return


    print(
        f"未知命令：{command}"
    )


if __name__ == "__main__":
    main()