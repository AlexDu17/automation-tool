"""串联 读取 -> 解析 -> 统计 -> 写出 的主流程，并把所有已知错误转成老师能看懂的中文提示。"""
from __future__ import annotations

import os

from .model import HeaderFormatError, parse_header, parse_students
from .reader import UnsupportedWorkbookError, load_raw_rows
from .writer import build_workbook

DEFAULT_OUTPUT_NAME = "二模质量分析结果.xlsx"


class FriendlyError(Exception):
    """可以直接展示给老师看的错误提示（不含 Python 报错细节）。"""


def resolve_path(path: str, base_dir: str) -> str:
    path = path.strip().strip('"')
    if os.path.isabs(path):
        return path
    return os.path.join(base_dir, path)


def run(input_path: str, output_path: str, base_dir: str | None = None) -> str:
    base_dir = base_dir or os.getcwd()
    input_path = resolve_path(input_path, base_dir)
    output_path = resolve_path(output_path or DEFAULT_OUTPUT_NAME, base_dir)

    if not os.path.exists(input_path):
        raise FriendlyError(f"找不到输入文件：\n{input_path}\n\n请检查文件名或路径是否正确。")

    try:
        rows = load_raw_rows(input_path)
    except UnsupportedWorkbookError:
        raise FriendlyError(
            f"无法打开这个文件，它可能不是 Excel 表格，或者已损坏：\n{input_path}"
        )
    except Exception as exc:  # noqa: BLE001
        raise FriendlyError(f"读取输入文件时出错：{exc}")

    try:
        parsed = parse_header(rows)
    except HeaderFormatError as exc:
        raise FriendlyError(f"输入表格的表头不是预期的格式：{exc}")

    students = parse_students(rows, parsed)
    if not students:
        raise FriendlyError("输入表格里没有找到任何学生数据，请检查文件内容。")

    wb = build_workbook(students, parsed)

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.isdir(output_dir):
        raise FriendlyError(f"输出文件夹不存在：\n{output_dir}")

    try:
        wb.save(output_path)
    except PermissionError:
        raise FriendlyError(
            f"无法保存到：\n{output_path}\n\n"
            "请确认这个文件没有被 Excel 打开，或者换一个文件名/位置再试一次。"
        )

    return output_path
