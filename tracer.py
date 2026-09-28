import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone


TRACE_DIR = Path(
    "data/traces"
)


class AgentTracer:

    def __init__(
        self,
        workflow_name: str,
    ):

        TRACE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.trace_id = (
            str(uuid.uuid4())
        )

        self.data = {

            "trace_id":
                self.trace_id,

            "workflow":
                workflow_name,

            "started_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "nodes": []
        }


    def start_node(
        self,
        name: str,
    ):

        return {

            "name": name,

            "start":
                time.time(),

        }


    def end_node(
        self,
        node,
        status="success",
        metadata=None,
    ):

        duration = (
            time.time()
            -
            node["start"]
        )


        record = {

            "name":
                node["name"],

            "status":
                status,

            "duration_seconds":
                round(
                    duration,
                    3
                ),

        }


        if metadata:

            record.update(
                metadata
            )


        self.data[
            "nodes"
        ].append(
            record
        )


    def save(self):

        self.data[
            "finished_at"
        ] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )


        path = (
            TRACE_DIR
            /
            f"{self.trace_id}.json"
        )


        path.write_text(
            json.dumps(
                self.data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


        return path