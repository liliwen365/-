# -*- coding: utf-8 -*-
"""银行对账引擎 - 编排 excel_reader + matcher 能力"""
import json
import os

from backend.capabilities.excel_reader import read_excel
from backend.capabilities.matcher import match_records, MatchRule


def _load_bank_formats(plugin_dir):
    """加载银行格式映射表。"""
    path = os.path.join(plugin_dir, 'bank_formats.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _normalize_transaction(record):
    """将解析后的记录标准化为统一格式。"""
    income = record.get('income')
    expense = record.get('expense')
    amount = 0
    direction = ""
    if income and float(income) != 0:
        amount = abs(float(income))
        direction = "income"
    elif expense and float(expense) != 0:
        amount = abs(float(expense))
        direction = "expense"
    return {
        "date": record.get('date'),
        "amount": amount,
        "direction": direction,
        "summary": record.get('summary', ''),
        "counterparty": record.get('counterparty', ''),
        "reference": record.get('reference', ''),
        "balance": record.get('balance'),
    }


def _parse_match_rules(rules_config):
    """将前端匹配规则配置转为 MatchRule 列表。"""
    rules = []
    for r in rules_config:
        if not r.get('enabled', True):
            continue
        name = r.get('rule_name', '')
        tol_days = int(r.get('tolerance_days', '3') or '3')
        tol_amount = float(r.get('amount_tolerance', '0.01') or '0.01')

        if '精确' in name:
            rules.append(MatchRule(
                name=name,
                key_fields=['date', 'amount'],
                field_types=['date', 'number'],
                tolerances=[0, tol_amount],
            ))
        elif '容差' in name:
            rules.append(MatchRule(
                name=name,
                key_fields=['date', 'amount'],
                field_types=['date', 'number'],
                match_type='tolerance',
                tolerances=[tol_days, tol_amount],
            ))
        elif '仅金额' in name:
            rules.append(MatchRule(
                name=name,
                key_fields=['amount'],
                field_types=['number'],
                tolerances=[tol_amount],
            ))
    return rules


def _build_reconciliation_statement(bank_balance, journal_balance, matched, unmatched_bank, unmatched_journal):
    """生成银行存款余额调节表。"""
    # 企业已收银行未收（journal有income但bank未匹配）
    bank_in_unmatched = sum(r.get('amount', 0) for r in unmatched_journal if r.get('direction') == 'income')
    # 企业已付银行未付（journal有expense但bank未匹配）
    bank_out_unmatched = sum(r.get('amount', 0) for r in unmatched_journal if r.get('direction') == 'expense')
    # 银行已收企业未收（bank有income但journal未匹配）
    ent_in_unmatched = sum(r.get('amount', 0) for r in unmatched_bank if r.get('direction') == 'income')
    # 银行已付企业未付（bank有expense但journal未匹配）
    ent_out_unmatched = sum(r.get('amount', 0) for r in unmatched_bank if r.get('direction') == 'expense')

    adj_bank = bank_balance + bank_in_unmatched - bank_out_unmatched
    adj_journal = journal_balance + ent_in_unmatched - ent_out_unmatched

    return {
        "bank_side": {
            "bank_balance": bank_balance,
            "journal_in_unmatched": bank_in_unmatched,
            "journal_out_unmatched": bank_out_unmatched,
            "adjusted_balance": adj_bank,
            "items": [
                {"type": "企业已收银行未收", "records": [r for r in unmatched_journal if r.get('direction') == 'income']},
                {"type": "企业已付银行未付", "records": [r for r in unmatched_journal if r.get('direction') == 'expense']},
            ],
        },
        "journal_side": {
            "journal_balance": journal_balance,
            "bank_in_unmatched": ent_in_unmatched,
            "bank_out_unmatched": ent_out_unmatched,
            "adjusted_balance": adj_journal,
            "items": [
                {"type": "银行已收企业未收", "records": [r for r in unmatched_bank if r.get('direction') == 'income']},
                {"type": "银行已付企业未付", "records": [r for r in unmatched_bank if r.get('direction') == 'expense']},
            ],
        },
        "is_balanced": abs(adj_bank - adj_journal) < 0.01,
    }


def reconcile(params, plugin_dir, on_progress=None):
    """执行银行对账主流程。

    Args:
        params: 插件参数（bank_file, bank_name, skip_rows, journal, match_rules）
        plugin_dir: 插件目录路径
        on_progress: 进度回调

    Returns: {"status", "summary", "data"}
    """
    bank_file = params.get('bank_file', '').strip()
    bank_name = params.get('bank_name', '通用模板')
    skip_rows = int(params.get('skip_rows', '0') or '0')
    journal_data = params.get('journal', [])
    match_rules_config = params.get('match_rules', [])

    if not bank_file or not os.path.exists(bank_file):
        return {"status": "error", "summary": "请指定有效的银行流水文件路径", "data": {}}
    if not journal_data:
        return {"status": "error", "summary": "请输入企业日记账数据", "data": {}}

    if on_progress:
        on_progress(1, 4, "解析银行流水", "")

    # 1. 解析银行流水
    formats = _load_bank_formats(plugin_dir)
    column_mapping = formats.get(bank_name, formats.get('通用模板', {}))

    try:
        bank_records, col_map = read_excel(bank_file, column_mapping, skip_rows=skip_rows)
    except Exception as e:
        return {"status": "error", "summary": f"解析银行流水失败: {e}", "data": {}}

    bank_transactions = [_normalize_transaction(r) for r in bank_records]

    if on_progress:
        on_progress(2, 4, "准备日记账", "")

    # 2. 准备日记账数据
    journal_transactions = []
    for row in journal_data:
        t = _normalize_transaction(row)
        if t['amount'] > 0 or t['date']:
            journal_transactions.append(t)

    # 3. 获取期末余额
    bank_balance = bank_transactions[-1].get('balance') if bank_transactions else 0
    journal_balance = journal_transactions[-1].get('balance') if journal_transactions else 0
    if isinstance(bank_balance, str):
        bank_balance = float(bank_balance.replace(',', ''))
    if isinstance(journal_balance, str):
        journal_balance = float(journal_balance.replace(',', ''))

    if on_progress:
        on_progress(3, 4, "执行匹配", "")

    # 4. 执行匹配
    rules = _parse_match_rules(match_rules_config)
    if not rules:
        rules = [
            MatchRule(name='精确匹配', key_fields=['date', 'amount'], field_types=['date', 'number'], tolerances=[0, 0.01]),
            MatchRule(name='日期容差3天', key_fields=['date', 'amount'], field_types=['date', 'number'], match_type='tolerance', tolerances=[3, 0.01]),
        ]

    report = match_records(bank_transactions, journal_transactions, rules)

    if on_progress:
        on_progress(4, 4, "生成调节表", "")

    # 5. 生成余额调节表
    statement = _build_reconciliation_statement(
        bank_balance, journal_balance,
        report.matched, report.unmatched_source, report.unmatched_target,
    )

    matched_detail = []
    for p in report.matched:
        matched_detail.append({
            "bank_date": p.source.get('date'),
            "bank_amount": p.source.get('amount'),
            "bank_summary": p.source.get('summary', ''),
            "journal_date": p.target.get('date'),
            "journal_amount": p.target.get('amount'),
            "journal_summary": p.target.get('summary', ''),
            "strategy": p.strategy,
            "notes": p.notes,
        })

    balance_status = "✓ 调节后余额一致" if statement['is_balanced'] else "✗ 调节后余额不一致，请检查"

    return {
        "status": "success",
        "summary": f"匹配完成: {report.summary['matched']}/{report.summary['source_total']}笔, {balance_status}",
        "data": {
            "column_mapping": col_map,
            "bank_count": len(bank_transactions),
            "journal_count": len(journal_transactions),
            "matched": matched_detail,
            "unmatched_bank": report.unmatched_source,
            "unmatched_journal": report.unmatched_target,
            "statement": statement,
            "match_summary": report.summary,
        },
    }
