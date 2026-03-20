# attendance/tests/test_validators.py
import datetime
from django.test import TestCase
from attendance.validators import validate_workday


class ValidateWorkdayTest(TestCase):
    """validate_workday() の全エラーコードをテスト"""

    # ── 正常系 ────────────────────────────────────────────
    def test_ok_8h_with_60min_break(self):
        """9:00〜18:00 休憩 60 分 → エラーなし"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(18, 0), 60
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_ok_6h_exactly_with_45min_break(self):
        """9:00〜15:00 休憩 45 分（境界値）→ エラーなし"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(15, 0), 45
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_ok_8h_exactly_with_60min_break(self):
        """9:00〜17:00 休憩 60 分（境界値）→ エラーなし"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(17, 0), 60
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    # ── ERR_NO_CLOCK_IN ───────────────────────────────────
    def test_err_no_clock_in(self):
        """出勤時刻 None → ERR_NO_CLOCK_IN"""
        ok, errors = validate_workday(None, datetime.time(18, 0), 60)
        self.assertFalse(ok)
        self.assertIn("ERR_NO_CLOCK_IN", errors)

    # ── ERR_NO_CLOCK_OUT ──────────────────────────────────
    def test_err_no_clock_out(self):
        """退勤時刻 None → ERR_NO_CLOCK_OUT"""
        ok, errors = validate_workday(datetime.time(9, 0), None, 60)
        self.assertFalse(ok)
        self.assertIn("ERR_NO_CLOCK_OUT", errors)

    def test_err_both_none(self):
        """両方 None → ERR_NO_CLOCK_IN + ERR_NO_CLOCK_OUT"""
        ok, errors = validate_workday(None, None, 60)
        self.assertFalse(ok)
        self.assertIn("ERR_NO_CLOCK_IN", errors)
        self.assertIn("ERR_NO_CLOCK_OUT", errors)

    # ── ERR_ORDER ─────────────────────────────────────────
    def test_err_order_reversed(self):
        """退勤 < 出勤 → ERR_ORDER"""
        ok, errors = validate_workday(
            datetime.time(18, 0), datetime.time(9, 0), 60
        )
        self.assertFalse(ok)
        self.assertIn("ERR_ORDER", errors)

    def test_err_order_same_time(self):
        """退勤 = 出勤 → ERR_ORDER"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(9, 0), 0
        )
        self.assertFalse(ok)
        self.assertIn("ERR_ORDER", errors)

    # ── ERR_WORK_TOO_LONG ─────────────────────────────────
    def test_err_work_too_long(self):
        """9:00〜22:00 休憩 0 分（780 分）→ ERR_WORK_TOO_LONG"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(22, 0), 0
        )
        self.assertFalse(ok)
        self.assertIn("ERR_WORK_TOO_LONG", errors)

    def test_work_exactly_720min_is_ok(self):
        """実働ちょうど 720 分 → エラーなし（境界値）"""
        ok, errors = validate_workday(
            datetime.time(9, 0),
            datetime.time(22, 0),
            60,
        )
        self.assertTrue(ok)
        self.assertEqual(errors, [])
    # ── ERR_BREAK_NEGATIVE ────────────────────────────────
    def test_err_break_negative(self):
        """break_min=-1 → ERR_BREAK_NEGATIVE"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(18, 0), -1
        )
        self.assertFalse(ok)
        self.assertIn("ERR_BREAK_NEGATIVE", errors)

    # ── ERR_BREAK_6H ──────────────────────────────────────
    def test_err_break_6h(self):
        """9:00〜15:00（6 時間）休憩 44 分 → ERR_BREAK_6H"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(15, 0), 44
        )
        self.assertFalse(ok)
        self.assertIn("ERR_BREAK_6H", errors)

    def test_no_break_6h_when_short(self):
        """9:00〜14:59（5h59m）→ 6H ルール適用外"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(14, 59), 0
        )
        self.assertTrue(ok)

    # ── ERR_BREAK_8H ──────────────────────────────────────
    def test_err_break_8h(self):
        """9:00〜18:00（9 時間）休憩 59 分 → ERR_BREAK_8H"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(18, 0), 59
        )
        self.assertFalse(ok)
        self.assertIn("ERR_BREAK_8H", errors)

    def test_err_break_8h_boundary(self):
        """9:00〜17:00（8 時間ちょうど）休憩 59 分 → ERR_BREAK_8H"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(17, 0), 59
        )
        self.assertFalse(ok)
        self.assertIn("ERR_BREAK_8H", errors)

    # ── 複数エラー同時 ────────────────────────────────────
    def test_multiple_errors(self):
        """8 時間勤務で休憩 -1 分 → ERR_BREAK_NEGATIVE + ERR_BREAK_8H"""
        ok, errors = validate_workday(
            datetime.time(9, 0), datetime.time(17, 0), -1
        )
        self.assertFalse(ok)
        self.assertIn("ERR_BREAK_NEGATIVE", errors)
        self.assertIn("ERR_BREAK_8H", errors)