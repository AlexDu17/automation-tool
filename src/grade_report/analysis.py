"""根据解析好的学生数据，计算各张分析表需要的数据。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .model import GRADE_ORDER, ParsedSheet, Student

OVERALL_LABEL = "整体"
SEGMENT_SIZE = 5
SEGMENT_LABEL = "均分/排名"


def sorted_class_codes(students: List[Student]) -> List[str]:
    return sorted({s.class_code for s in students})


def class_label_of(students: List[Student], class_code: str) -> Any:
    for s in students:
        if s.class_code == class_code:
            return s.class_label
    return class_code


def distribution_subjects(parsed: ParsedSheet) -> List[str]:
    """等级分布 / 各科平均分 使用的科目顺序：总分打头，其余按原表列顺序，排除被拆分出来的英语分量。"""
    names: List[str] = [parsed.total_display_name]
    for subject in parsed.subjects:
        name = subject.display_name
        if name == parsed.total_display_name or name in parsed.component_display_names:
            continue
        if name not in names:
            names.append(name)
    return names


def rank_sheet_subjects(parsed: ParsedSheet) -> List[str]:
    """分段排名表使用的科目顺序：总分 -> 常规科目 -> 英语的两个分量（笔试/听说）放最后。"""
    names = distribution_subjects(parsed)
    for subject in parsed.subjects:
        if subject.display_name in parsed.component_display_names and subject.display_name not in names:
            names.append(subject.display_name)
    return names


@dataclass
class GradeDistributionRow:
    label: Any  # 班级标签(如901) 或 "整体"
    counts: Dict[str, int]  # 每个等级的人数，如 {"A+": 4, "A": 16, ...}
    total: int  # 该行有效（非缺考）人数


def _grade_counts(students: List[Student], subject: str) -> Tuple[Dict[str, int], int]:
    counts = {g: 0 for g in GRADE_ORDER}
    total = 0
    for s in students:
        grade = s.grade_of(subject)
        if grade is None:
            continue
        total += 1
        if grade in counts:
            counts[grade] += 1
    return counts, total


def build_grade_distribution(students: List[Student], subject: str) -> List[GradeDistributionRow]:
    rows: List[GradeDistributionRow] = []
    for class_code in sorted_class_codes(students):
        class_students = [s for s in students if s.class_code == class_code]
        counts, total = _grade_counts(class_students, subject)
        rows.append(GradeDistributionRow(class_label_of(students, class_code), counts, total))
    counts, total = _grade_counts(students, subject)
    rows.append(GradeDistributionRow(OVERALL_LABEL, counts, total))
    return rows


def distribution_metric_values(counts: Dict[str, int], total: int) -> List[Tuple[int, Optional[float]]]:
    """返回 9 个指标 (A+, A, A以上, B+, B+以上, B, B以上, C+, C) 的 (人数, 占比)。"""
    a_plus = counts["A+"]
    a = counts["A"]
    a_above = a_plus + a
    b_plus = counts["B+"]
    b_plus_above = a_above + b_plus
    b = counts["B"]
    b_above = b_plus_above + b
    c_plus = counts["C+"]
    c = counts["C"]
    values = [a_plus, a, a_above, b_plus, b_plus_above, b, b_above, c_plus, c]
    ratio = lambda n: (n / total) if total else None
    return [(v, ratio(v)) for v in values]


@dataclass
class SubjectAverageRow:
    label: Any
    average: Optional[float]
    rank: Optional[int]


def build_subject_averages(students: List[Student], subject: str) -> List[SubjectAverageRow]:
    class_codes = sorted_class_codes(students)
    class_averages: Dict[str, Optional[float]] = {}
    for class_code in class_codes:
        scores = [s.score_of(subject) for s in students if s.class_code == class_code and s.score_of(subject) is not None]
        class_averages[class_code] = (sum(scores) / len(scores)) if scores else None

    ranked = sorted(
        (code for code in class_codes if class_averages[code] is not None),
        key=lambda code: class_averages[code],
        reverse=True,
    )
    rank_of = {code: i + 1 for i, code in enumerate(ranked)}

    rows = [
        SubjectAverageRow(class_label_of(students, code), class_averages[code], rank_of.get(code))
        for code in class_codes
    ]

    all_scores = [s.score_of(subject) for s in students if s.score_of(subject) is not None]
    overall_avg = (sum(all_scores) / len(all_scores)) if all_scores else None
    rows.append(SubjectAverageRow(OVERALL_LABEL, overall_avg, None))
    return rows


@dataclass
class SegmentRow:
    label: Any  # 名次数字 或 "均分/排名"
    cells: Dict[str, Tuple[Optional[str], Optional[float]]]  # class_code -> (姓名或None, 分数或均分)
    is_average_row: bool = False


def build_rank_segments(
    students: List[Student], subject: str, required_subjects: Optional[List[str]] = None
) -> Tuple[List[str], List[SegmentRow]]:
    """按 subject 的分数从高到低分段排名。

    required_subjects：要计入本表，学生必须"全部"有成绩的科目列表；默认就是 [subject] 自己
    （即普通科目缺考就排除）。合并出来的最终"英语"是特例——只要求"英语笔试"，"英语听说"
    缺考不影响；"总分"则要求除"英语听说"外的所有科目都有成绩，缺任意一门主科都不计入。
    """
    required_subjects = required_subjects or [subject]
    class_codes = sorted_class_codes(students)
    per_class: Dict[str, List[Tuple[str, float]]] = {}
    for class_code in class_codes:
        entries = [
            (s.row.get("姓名"), s.score_of(subject))
            for s in students
            if s.class_code == class_code
            and s.score_of(subject) is not None
            and all(s.score_of(req) is not None for req in required_subjects)
        ]
        entries.sort(key=lambda item: item[1], reverse=True)
        per_class[class_code] = entries

    max_len = max((len(v) for v in per_class.values()), default=0)

    def average_row(up_to: int) -> SegmentRow:
        cells = {}
        for class_code in class_codes:
            entries = per_class[class_code]
            take = entries[: min(up_to, len(entries))]
            avg = (sum(score for _, score in take) / len(take)) if take else None
            # 与参考表格一致：均分写在“姓名”那一列，分数列留空。
            cells[class_code] = (round(avg, 2) if avg is not None else None, None)
        return SegmentRow(label=SEGMENT_LABEL, cells=cells, is_average_row=True)

    rows: List[SegmentRow] = []
    for rank in range(1, max_len + 1):
        cells = {}
        for class_code in class_codes:
            entries = per_class[class_code]
            cells[class_code] = entries[rank - 1] if rank - 1 < len(entries) else (None, None)
        rows.append(SegmentRow(label=rank, cells=cells))
        if rank % SEGMENT_SIZE == 0:
            rows.append(average_row(rank))

    if max_len % SEGMENT_SIZE != 0:
        rows.append(average_row(max_len))

    return class_codes, rows


def competition_ranks(values: List[Optional[float]]) -> List[Optional[int]]:
    """1224 排名法：分数相同名次相同，下一名按人数跳号；None 不参与排名。"""
    ranks: List[Optional[int]] = [None] * len(values)
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda item: item[1], reverse=True)
    rank = 0
    prev_value = None
    for position, (original_index, value) in enumerate(indexed, start=1):
        if value != prev_value:
            rank = position
            prev_value = value
        ranks[original_index] = rank
    return ranks


def build_raw_scores(students: List[Student], parsed: ParsedSheet) -> List[Student]:
    totals = [s.score_of(parsed.total_display_name) for s in students]
    ranks = competition_ranks(totals)
    order = sorted(
        range(len(students)),
        key=lambda i: (totals[i] is None, -(totals[i] or 0)),
    )
    ordered_students = [students[i] for i in order]
    ordered_ranks = [ranks[i] for i in order]
    return list(zip(ordered_students, ordered_ranks))


def build_class_roster(students: List[Student], class_code: str, parsed: ParsedSheet) -> List[Student]:
    class_students = [s for s in students if s.class_code == class_code]
    class_students.sort(
        key=lambda s: (
            s.score_of(parsed.total_display_name) is None,
            -(s.score_of(parsed.total_display_name) or 0),
        )
    )
    return class_students
