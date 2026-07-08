"""命令行入口：python main.py --input 学生成绩.xlsx --output 二模质量分析结果.xlsx"""
from __future__ import annotations

import argparse
import sys

from .pipeline import DEFAULT_OUTPUT_NAME, FriendlyError, run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据学生成绩表格生成质量分析结果")
    parser.add_argument("-i", "--input", required=True, help="输入的学生成绩表格（文件名或完整路径）")
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_NAME,
        help=f"输出的分析结果表格（文件名或完整路径），默认「{DEFAULT_OUTPUT_NAME}」",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output_path = run(args.input, args.output)
    except FriendlyError as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 1
    print(f"已生成分析结果：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
