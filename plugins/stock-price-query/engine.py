# -*- coding: utf-8 -*-
"""股票行情查询引擎 - 新浪财经API"""
import re
import requests


def _parse_sina_response(text: str) -> dict[str, dict]:
    """解析新浪行情API返回数据。"""
    result = {}
    for line in text.strip().split('\n'):
        m = re.match(r'var hq_str_(\w+)="(.+)"', line)
        if not m:
            continue
        code = m.group(1)
        fields = m.group(2).split(',')
        if len(fields) < 32:
            continue
        result[code] = {
            "name": fields[0],
            "open": _safe_float(fields[1]),
            "prev_close": _safe_float(fields[2]),
            "current": _safe_float(fields[3]),
            "high": _safe_float(fields[4]),
            "low": _safe_float(fields[5]),
            "bid": _safe_float(fields[6]),
            "ask": _safe_float(fields[7]),
            "volume": _safe_int(fields[8]),
            "amount": _safe_float(fields[9]),
            "date": fields[30],
            "time": fields[31],
        }
    return result


def _safe_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val: str) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def query_prices(params: dict, on_progress=None) -> dict:
    """查询股票实时行情。"""
    stocks = params.get('stocks', [])
    codes = [s['code'].strip().lower() for s in stocks if s.get('code', '').strip()]

    if not codes:
        return {"status": "error", "summary": "请输入至少一个股票代码", "data": {}}

    if on_progress:
        on_progress(1, 3, "查询行情", "")

    try:
        url = f"https://hq.sinajs.cn/list={','.join(codes)}"
        resp = requests.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
        resp.encoding = 'gbk'
        prices = _parse_sina_response(resp.text)
    except Exception as e:
        return {"status": "error", "summary": f"查询失败: {e}", "data": {}}

    if on_progress:
        on_progress(2, 3, "汇总结果", "")

    rows = []
    for s in stocks:
        code = s['code'].strip().lower()
        info = prices.get(code)
        if not info:
            rows.append({
                "code": s['code'], "name": s.get('name', ''),
                "error": "未找到行情数据",
            })
            continue

        current = info['current']
        prev = info['prev_close']
        change = round(current - prev, 3) if prev else 0
        change_pct = round(change / prev * 100, 2) if prev else 0

        rows.append({
            "code": s['code'],
            "name": info['name'],
            "remark": s.get('name', ''),
            "current": current,
            "change": change,
            "change_pct": change_pct,
            "open": info['open'],
            "high": info['high'],
            "low": info['low'],
            "prev_close": prev,
            "volume": info['volume'],
            "amount": info['amount'],
            "date": info['date'],
            "time": info['time'],
        })

    # 统计
    up = sum(1 for r in rows if r.get('change', 0) > 0)
    down = sum(1 for r in rows if r.get('change', 0) < 0)
    flat = sum(1 for r in rows if r.get('change', 0) == 0)
    errors = sum(1 for r in rows if 'error' in r)

    if on_progress:
        on_progress(3, 3, "完成", "")

    summary_parts = [f"共{len(rows)}只"]
    if up:
        summary_parts.append(f"{up}涨")
    if down:
        summary_parts.append(f"{down}跌")
    if errors:
        summary_parts.append(f"{errors}异常")

    return {
        "status": "success",
        "summary": "、".join(summary_parts),
        "data": {
            "rows": rows,
            "summary": {"total": len(rows), "up": up, "down": down, "flat": flat, "errors": errors},
        },
    }
