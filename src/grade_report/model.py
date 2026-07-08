"""解析原始表格：识别表头结构、科目列，并把每一行数据转成学生记录。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# 六级等级从高到低的顺序，用于等级分布表的列顺序。
GRADE_ORDER = ["A+", "A", "B+", "B", "C+", "C"]

GRADE_SCORE_HEADER = "分数"
GRADE_LEVEL_HEADER = "等级"

TITLE_ROW = 0
GROUP_ROW = 1
SUB_ROW = 2
DATA_START_ROW = 3


class HeaderFormatError(ValueError):
    """输入表格的表头结构不是预期的样子。"""


@dataclass
class Subject:
    name: str  # 原始列名，如"英语"、"英语合并"
    display_name: str  # 输出中使用的名字，如"英语笔试"、"英语"
    score_col: int
    grade_col: int


@dataclass
class ParsedSheet:
    base_columns: Dict[str, int]
    subjects: List[Subject]
    component_display_names: Set[str]  # 被拆分英语等合并出来的原始分量，如{"英语笔试","英语听说"}
    total_display_name: str


@dataclass
class Student:
    row: Dict[str, Any]  # 基础列：学号/考号/姓名/学校/区域/考生类型1/考生类型2 等
    class_code: str  # 原始班级代码，如 "01"
    class_label: int  # 换算后的班级标签，如 901
    scores: Dict[str, Tuple[Optional[float], Optional[str]]] = field(default_factory=dict)

    def score_of(self, subject_display_name: str) -> Optional[float]:
        return self.scores.get(subject_display_name, (None, None))[0]

    def grade_of(self, subject_display_name: str) -> Optional[str]:
        return self.scores.get(subject_display_name, (None, None))[1]


def _normalize_class_code(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, float):
        return f"{int(raw):02d}"
    text = str(raw).strip()
    if text.isdigit():
        return text.zfill(2)
    return text


def class_label_for(class_code: str, grade_prefix: str = "9") -> Optional[int]:
    """按老师给定的规则换算班级标签，如 "01" -> 901（九年级一班）。"""
    if not class_code or not class_code.isdigit():
        return None
    return int(f"{grade_prefix}{class_code}")


def parse_header(rows: List[List[Any]]) -> ParsedSheet:
    if len(rows) < DATA_START_ROW:
        raise HeaderFormatError("表格行数太少，无法识别表头（需要标题行+科目行+分数等级行）")

    group_row = rows[GROUP_ROW]
    sub_row = rows[SUB_ROW]
    ncols = len(sub_row)

    base_columns: Dict[str, int] = {}
    col = 0
    while col < ncols and sub_row[col] is None:
        name = group_row[col]
        if name:
            base_columns[str(name)] = col
        col += 1

    required = ["学号", "姓名", "行政班级"]
    missing = [name for name in required if name not in base_columns]
    if missing:
        raise HeaderFormatError(f"表头缺少必要的列：{'、'.join(missing)}")

    subjects: List[Subject] = []
    while col < ncols:
        if (
            sub_row[col] == GRADE_SCORE_HEADER
            and col + 1 < ncols
            and sub_row[col + 1] == GRADE_LEVEL_HEADER
        ):
            name = group_row[col]
            if not name:
                raise HeaderFormatError(f"第 {col + 1} 列是分数列，但上方缺少科目名称")
            subjects.append(Subject(name=str(name), display_name=str(name), score_col=col, grade_col=col + 1))
            col += 2
        else:
            col += 1

    if not subjects:
        raise HeaderFormatError("没有识别到任何科目的“分数/等级”列，请检查表头格式")

    subject_names = [s.name for s in subjects]
    component_display_names: Set[str] = set()

    if "英语合并" in subject_names:
        for s in subjects:
            if s.name == "英语合并":
                s.display_name = "英语"
            elif s.name == "英语":
                s.display_name = "英语笔试"
                component_display_names.add(s.display_name)
            elif s.name == "英语听力":
                s.display_name = "英语听说"
                component_display_names.add(s.display_name)

    total_candidates = [s.display_name for s in subjects if s.name == "总分"]
    total_display_name = total_candidates[0] if total_candidates else subjects[-1].display_name

    return ParsedSheet(
        base_columns=base_columns,
        subjects=subjects,
        component_display_names=component_display_names,
        total_display_name=total_display_name,
    )


def parse_students(rows: List[List[Any]], parsed: ParsedSheet, grade_prefix: str = "9") -> List[Student]:
    students: List[Student] = []
    for raw_row in rows[DATA_START_ROW:]:
        if raw_row[parsed.base_columns["学号"]] is None and raw_row[parsed.base_columns["姓名"]] is None:
            continue  # 跳过表格末尾的空行

        base = {name: raw_row[idx] for name, idx in parsed.base_columns.items()}
        class_code = _normalize_class_code(base.get("行政班级"))
        class_label = class_label_for(class_code, grade_prefix)

        scores: Dict[str, Tuple[Optional[float], Optional[str]]] = {}
        for subject in parsed.subjects:
            score = raw_row[subject.score_col]
            grade = raw_row[subject.grade_col]
            if isinstance(score, str):
                score = score.strip() or None
                if score is not None:
                    score = float(score)
            if isinstance(grade, str):
                grade = grade.strip() or None
            scores[subject.display_name] = (score, grade)

        students.append(
            Student(row=base, class_code=class_code, class_label=class_label, scores=scores)
        )
    return students
