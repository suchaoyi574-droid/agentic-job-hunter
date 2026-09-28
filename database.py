import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path("data/agentic_job_hunter.db")
JOBS_PATH = Path("jobs.json")
MATCHES_PATH = Path("data/matches.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 开启外键支持
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_database():
    conn = get_connection()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,

            description TEXT,
            experience TEXT,

            skills_json TEXT NOT NULL DEFAULT '[]',

            url TEXT NOT NULL UNIQUE,

            status TEXT NOT NULL DEFAULT 'discovered',

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            job_id INTEGER NOT NULL UNIQUE,

            match_score INTEGER NOT NULL,

            matched_skills_json TEXT NOT NULL DEFAULT '[]',
            missing_skills_json TEXT NOT NULL DEFAULT '[]',
            transferable_strengths_json TEXT NOT NULL DEFAULT '[]',
            reasons_json TEXT NOT NULL DEFAULT '[]',

            recommendation TEXT,

            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,

            FOREIGN KEY(job_id)
                REFERENCES jobs(id)
                ON DELETE CASCADE
        );
        """
    )

    conn.commit()
    conn.close()


def save_job(conn, job: dict):
    timestamp = now_iso()

    existing = conn.execute(
        """
        SELECT id
        FROM jobs
        WHERE url = ?
        """,
        (job["url"],),
    ).fetchone()

    skills_json = json.dumps(
        job.get("skills", []),
        ensure_ascii=False,
    )

    if existing:
        conn.execute(
            """
            UPDATE jobs

            SET
                title = ?,
                company = ?,
                location = ?,
                description = ?,
                experience = ?,
                skills_json = ?,
                updated_at = ?

            WHERE id = ?
            """,
            (
                job.get("title"),
                job.get("company"),
                job.get("location"),
                job.get("description"),
                job.get("experience"),
                skills_json,
                timestamp,
                existing["id"],
            ),
        )

        return existing["id"]

    cursor = conn.execute(
        """
        INSERT INTO jobs (
            title,
            company,
            location,
            description,
            experience,
            skills_json,
            url,
            status,
            created_at,
            updated_at
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            job.get("description"),
            job.get("experience"),
            skills_json,
            job["url"],
            "discovered",
            timestamp,
            timestamp,
        ),
    )

    return cursor.lastrowid


def save_match(conn, match: dict):
    # 通过 company + title 找对应职位
    job = conn.execute(
        """
        SELECT id, status
        FROM jobs

        WHERE LOWER(title) = LOWER(?)
        AND LOWER(company) = LOWER(?)
        """,
        (
            match["title"],
            match["company"],
        ),
    ).fetchone()

    if not job:
        print(
            f"WARNING: 数据库中找不到职位: "
            f"{match['title']} @ {match['company']}"
        )
        return

    timestamp = now_iso()

    existing = conn.execute(
        """
        SELECT id
        FROM matches
        WHERE job_id = ?
        """,
        (job["id"],),
    ).fetchone()

    values = (
        match["match_score"],
        json.dumps(
            match.get("matched_skills", []),
            ensure_ascii=False,
        ),
        json.dumps(
            match.get("missing_skills", []),
            ensure_ascii=False,
        ),
        json.dumps(
            match.get("transferable_strengths", []),
            ensure_ascii=False,
        ),
        json.dumps(
            match.get("reasons", []),
            ensure_ascii=False,
        ),
        match.get("recommendation"),
    )

    if existing:
        conn.execute(
            """
            UPDATE matches

            SET
                match_score = ?,
                matched_skills_json = ?,
                missing_skills_json = ?,
                transferable_strengths_json = ?,
                reasons_json = ?,
                recommendation = ?,
                updated_at = ?

            WHERE job_id = ?
            """,
            values
            + (
                timestamp,
                job["id"],
            ),
        )

    else:
        conn.execute(
            """
            INSERT INTO matches (
                job_id,
                match_score,
                matched_skills_json,
                missing_skills_json,
                transferable_strengths_json,
                reasons_json,
                recommendation,
                created_at,
                updated_at
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job["id"],
                *values,
                timestamp,
                timestamp,
            ),
        )

    # 第一次匹配完成后，把状态从 discovered -> matched
    if job["status"] == "discovered":
        conn.execute(
            """
            UPDATE jobs
            SET
                status = 'matched',
                updated_at = ?
            WHERE id = ?
            """,
            (
                timestamp,
                job["id"],
            ),
        )


def import_existing_data():
    conn = get_connection()

    # ------------------------------
    # 导入 jobs.json
    # ------------------------------

    if JOBS_PATH.exists():
        data = json.loads(
            JOBS_PATH.read_text(
                encoding="utf-8"
            )
        )

        for job in data.get("jobs", []):
            save_job(conn, job)

    else:
        print("WARNING: 找不到 jobs.json")

    # ------------------------------
    # 导入 matches.json
    # ------------------------------

    if MATCHES_PATH.exists():
        data = json.loads(
            MATCHES_PATH.read_text(
                encoding="utf-8"
            )
        )

        for match in data.get("matches", []):
            save_match(conn, match)

    else:
        print(
            "WARNING: 找不到 data/matches.json"
        )

    conn.commit()
    conn.close()


def show_database():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            jobs.id,
            jobs.title,
            jobs.company,
            jobs.status,
            matches.match_score

        FROM jobs

        LEFT JOIN matches
            ON matches.job_id = jobs.id

        ORDER BY jobs.id
        """
    ).fetchall()

    print("\n================================")
    print("DATABASE CONTENT")
    print("================================")

    for row in rows:
        score = (
            row["match_score"]
            if row["match_score"] is not None
            else "Not evaluated"
        )

        print(
            f"\nID: {row['id']}"
        )

        print(
            f"{row['title']} @ {row['company']}"
        )

        print(
            f"Status: {row['status']}"
        )

        print(
            f"Match Score: {score}"
        )

    print("\n================================")
    print(
        f"Database: {DB_PATH}"
    )

    conn.close()


def main():
    print("初始化 SQLite 数据库...")

    init_database()

    print("导入 jobs.json 和 matches.json...")

    import_existing_data()

    show_database()


if __name__ == "__main__":
    main()