import asyncio

from mcp import Client
from mcp_server import mcp


async def main():
    async with Client(mcp) as client:

        result = await client.call_tool(
            "get_recommended_jobs",
            {}
        )

        print("调用是否失败：", result.is_error)

        print("\n返回内容：")

        for item in result.content:
            print(item)


if __name__ == "__main__":
    asyncio.run(main())