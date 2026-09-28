import asyncio
import os

from browser_use import Agent, ChatDeepSeek
from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("没有找到 DEEPSEEK_API_KEY，请检查 .env 文件")


async def main():
    llm = ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=api_key,
    )

    agent = Agent(
        task="""
        Search the web for AI Agent Engineer jobs.

        Find 3 job openings and return:
        - Job title
        - Company
        - Location
        - Job URL
        """,
        llm=llm,
    )

    history = await agent.run()

    print("\n=== FINAL RESULT ===")
    print(history.final_result())


if __name__ == "__main__":
    asyncio.run(main())