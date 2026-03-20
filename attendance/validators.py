# attendance/validators.py
import datetime

# エラーコードと日本語メッセージの対応表
ERROR_MESSAGES = {
    "ERR_NO_CLOCK_IN":    "出勤時刻が入力されていません",
    "ERR_NO_CLOCK_OUT":   "退勤時刻が入力されていません",
    "ERR_ORDER":          "退勤時刻は出勤時刻より後にしてください",
    "ERR_WORK_TOO_LONG":  "実働時間が 12 時間（720 分）を超えています",
    "ERR_BREAK_NEGATIVE": "休憩時間は 0 分以上にしてください",
    "ERR_BREAK_6H":       "6 時間以上の勤務には 45 分以上の休憩が必要です",
    "ERR_BREAK_8H":       "8 時間以上の勤務には 60 分以上の休憩が必要です",
}


def _to_minutes(t):
    """time オブジェクトまたは文字列を「分」に変換する"""
    if t is None:
        return None
    if isinstance(t, str):
        t = datetime.time.fromisoformat(t)
    return t.hour * 60 + t.minute


def validate_workday(clock_in, clock_out, break_min):
    """
    勤怠レコードを strict バリデーションする。

    Returns:
        (bool, list[str])  →  (OK フラグ, エラーコードのリスト)
    """
    errors = []

    # ── 1. 必須チェック ───────────────────────────────────
    if clock_in is None:
        errors.append("ERR_NO_CLOCK_IN")
    if clock_out is None:
        errors.append("ERR_NO_CLOCK_OUT")

    # 両方入力されていない場合はここで終了
    if errors:
        return False, errors

    # ── 2. 数値変換 ──────────────────────────────────────
    ci_min = _to_minutes(clock_in)
    co_min = _to_minutes(clock_out)

    # ── 3. 順序チェック ──────────────────────────────────
    if co_min <= ci_min:
        errors.append("ERR_ORDER")
        return False, errors   # 順序が逆なら以降の計算が無意味

    # ── 4. 実働時間の計算 ────────────────────────────────
    work_min = co_min - ci_min - break_min

    # ── 5. 各チェック ────────────────────────────────────
    if work_min > 720:
        errors.append("ERR_WORK_TOO_LONG")
    if break_min < 0:
        errors.append("ERR_BREAK_NEGATIVE")
    if (co_min - ci_min) >= 360 and break_min < 45:
        errors.append("ERR_BREAK_6H")
    if (co_min - ci_min) >= 480 and break_min < 60:
        errors.append("ERR_BREAK_8H")

    return len(errors) == 0, errors


def get_error_messages(error_codes):
    """エラーコードのリストから日本語メッセージのリストを返す"""
    return [ERROR_MESSAGES.get(code, code) for code in error_codes]