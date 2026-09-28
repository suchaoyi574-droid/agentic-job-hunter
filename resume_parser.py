from pathlib import Path

from pypdf import PdfReader


RESUME_PATH = Path("data/resume.pdf")
OUTPUT_PATH = Path("data/resume.txt")


def extract_resume_text(pdf_path: Path) -> str:
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"找不到简历文件: {pdf_path}\n"
            "请把你的 PDF 简历放到 data/resume.pdf"
        )

    reader = PdfReader(pdf_path)

    pages_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()

        if text:
            pages_text.append(
                f"\n===== PAGE {page_number} =====\n{text}"
            )

    return "\n".join(pages_text)


def main():
    print("正在读取简历...")

    resume_text = extract_resume_text(RESUME_PATH)

    if not resume_text.strip():
        print("没有提取到文字。")
        print("你的 PDF 可能是扫描图片版。")
        return

    OUTPUT_PATH.write_text(
        resume_text,
        encoding="utf-8",
    )

    print("\n==============================")
    print("RESUME PARSER SUCCESS")
    print("==============================")

    print(f"\n字符数: {len(resume_text)}")
    print(f"输出文件: {OUTPUT_PATH}")

    print("\n前 1000 个字符：")
    print("------------------------------")
    print(resume_text[:1000])


if __name__ == "__main__":
    main()