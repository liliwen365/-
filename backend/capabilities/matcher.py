# -*- coding: utf-8 -*-
"""多策略级联匹配引擎 - 通用能力，不绑定具体业务"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class MatchRule:
    """单条匹配规则。

    定义一轮匹配中如何比较两方记录。
    多条规则组成级联管线，先精确后模糊。
    """
    name: str                              # 策略名（如"精确匹配"、"容差匹配"）
    key_fields: list[str]                   # 参与匹配的字段名（两方记录都用这个名字）
    match_type: str = "exact"               # "exact" | "tolerance"
    field_types: list[str] = field(default_factory=lambda: [])  # 每个字段类型 "string"|"number"|"date"
    tolerances: list[float] = field(default_factory=lambda: [])  # tolerance 类型的容差值

    def __post_init__(self):
        if not self.field_types:
            self.field_types = ["string"] * len(self.key_fields)
        if not self.tolerances:
            self.tolerances = [0] * len(self.key_fields)


@dataclass
class MatchPair:
    """一对匹配结果。"""
    source: dict           # A方记录
    target: dict           # B方记录
    strategy: str          # 使用的策略名
    score: float = 1.0     # 匹配置信度
    notes: str = ""        # 说明


@dataclass
class MatchReport:
    """完整匹配报告。"""
    matched: list = field(default_factory=list)          # list[MatchPair]
    unmatched_source: list = field(default_factory=list)  # list[dict]
    unmatched_target: list = field(default_factory=list)  # list[dict]
    summary: dict = field(default_factory=dict)

    def __post_init__(self):
        total_s = len(self.matched) + len(self.unmatched_source)
        total_t = len(self.matched) + len(self.unmatched_target)
        self.summary = {
            "source_total": total_s,
            "target_total": total_t,
            "matched": len(self.matched),
            "unmatched_source": len(self.unmatched_source),
            "unmatched_target": len(self.unmatched_target),
            "match_rate": round(len(self.matched) / total_s, 2) if total_s else 0,
        }


def match_records(sources, targets, rules):
    """多轮级联匹配。

    按规则顺序执行，每轮匹配消耗已匹配的记录，剩余未匹配进入下一轮。
    规则从严格到宽松排列：精确匹配 → 容差匹配 → 宽松匹配。

    Args:
        sources: list[dict] A方记录
        targets: list[dict] B方记录
        rules: list[MatchRule] 匹配规则（有序）

    Returns: MatchReport
    """
    remaining_source = list(sources)
    remaining_target = list(targets)
    all_matched = []

    for rule in rules:
        if not remaining_source or not remaining_target:
            break

        matched_pairs, still_source, still_target = _apply_rule(
            remaining_source, remaining_target, rule
        )
        all_matched.extend(matched_pairs)
        remaining_source = still_source
        remaining_target = still_target

    return MatchReport(
        matched=all_matched,
        unmatched_source=remaining_source,
        unmatched_target=remaining_target,
    )


def _apply_rule(sources, targets, rule):
    """应用单条规则进行匹配。"""
    matched_pairs = []
    matched_source_idx = set()
    matched_target_idx = set()

    # 为 targets 建立索引加速查找
    target_index = _build_index(targets, rule)
    total_targets = len(targets)

    for si, source in enumerate(sources):
        if si in matched_source_idx:
            continue

        source_key = _extract_key(source, rule)
        if source_key is None:
            continue

        candidates = _find_candidates(source_key, target_index, rule, total_targets)

        best_ti = None
        best_score = 0
        best_notes = ""

        for ti in candidates:
            if ti in matched_target_idx:
                continue
            target = targets[ti]
            target_key = _extract_key(target, rule)
            if target_key is None:
                continue

            score, notes = _compare_keys(source_key, target_key, rule)
            if score > 0 and score > best_score:
                best_ti = ti
                best_score = score
                best_notes = notes

        if best_ti is not None:
            matched_pairs.append(MatchPair(
                source=source,
                target=targets[best_ti],
                strategy=rule.name,
                score=best_score,
                notes=best_notes,
            ))
            matched_source_idx.add(si)
            matched_target_idx.add(best_ti)

    still_source = [s for i, s in enumerate(sources) if i not in matched_source_idx]
    still_target = [t for i, t in enumerate(targets) if i not in matched_target_idx]

    return matched_pairs, still_source, still_target


def _build_index(targets, rule):
    """为 target 记录构建索引。精确匹配时用 key 查找，容差时线性扫描。"""
    if rule.match_type == "exact":
        idx = {}
        for i, t in enumerate(targets):
            key = _extract_key(t, rule)
            if key is not None:
                k = _hashable_key(key, rule)
                if k not in idx:
                    idx[k] = []
                idx[k].append(i)
        return idx
    else:
        return None


def _find_candidates(source_key, target_index, rule, total_targets):
    """根据 source_key 找候选 target。"""
    if rule.match_type == "exact" and target_index is not None:
        k = _hashable_key(source_key, rule)
        return target_index.get(k, [])
    else:
        # 容差匹配或无索引时，返回全部 target 索引
        return range(total_targets)


def _extract_key(record, rule):
    """从记录中提取参与匹配的字段值。"""
    values = []
    for fname in rule.key_fields:
        val = record.get(fname)
        if val is None:
            return None
        values.append(val)
    return values


def _compare_keys(source_key, target_key, rule):
    """比较两方 key，返回 (score, notes)。

    score > 0 表示匹配，= 0 表示不匹配。
    """
    total_score = 0
    max_score = len(rule.key_fields)
    notes_parts = []

    for i, (sv, tv) in enumerate(zip(source_key, target_key)):
        ftype = rule.field_types[i] if i < len(rule.field_types) else "string"
        tolerance = rule.tolerances[i] if i < len(rule.tolerances) else 0

        if ftype == "string":
            if str(sv).strip() == str(tv).strip():
                total_score += 1
            else:
                return 0, ""
        elif ftype == "number":
            sn = _to_number(sv)
            tn = _to_number(tv)
            if sn is None or tn is None:
                return 0, ""
            diff = abs(sn - tn)
            if diff <= (tolerance or 0.01):
                total_score += 1
                if diff > 0:
                    notes_parts.append(f"差额{diff:.2f}")
            else:
                return 0, f"金额差异{diff:.2f}"
        elif ftype == "date":
            sd = _to_date(sv)
            td = _to_date(tv)
            if sd is None or td is None:
                return 0, ""
            day_diff = abs((sd - td).days)
            if day_diff <= (tolerance or 0):
                total_score += 1
                if day_diff > 0:
                    notes_parts.append(f"日期差{day_diff}天")
            else:
                return 0, f"日期差{day_diff}天"

    score = total_score / max_score if max_score > 0 else 0
    notes = "; ".join(notes_parts) if notes_parts else ""
    return score, notes


def _hashable_key(key_values, rule):
    """将 key 值转为可哈希的元组（用于精确匹配索引）。"""
    parts = []
    for i, val in enumerate(key_values):
        ftype = rule.field_types[i] if i < len(rule.field_types) else "string"
        if ftype == "number":
            parts.append(round(_to_number(val) or 0, 2))
        elif ftype == "date":
            d = _to_date(val)
            parts.append(d.isoformat() if d else None)
        else:
            parts.append(str(val).strip())
    return tuple(parts)


def _to_number(val):
    """将值转为 float，处理千分位逗号。"""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(',', '').replace('，', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def _to_date(val):
    """将值转为 date，支持多种日期格式。"""
    if isinstance(val, datetime):
        return val.date()
    from datetime import date as date_cls
    if isinstance(val, date_cls):
        return val
    s = str(val).strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d', '%Y%m%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None
