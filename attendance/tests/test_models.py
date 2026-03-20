# attendance/tests/test_models.py
import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from attendance.models import WorkDay, ChangeLog


class WorkDayCalcWorkMinTest(TestCase):
    """WorkDay.calc_work_min() のテスト"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass")

    def _make_wd(self, clock_in, clock_out, break_min=60):
        return WorkDay(
            user=self.user,
            date=datetime.date(2025, 6, 1),
            clock_in=clock_in,
            clock_out=clock_out,
            break_min=break_min,
        )

    def test_normal_8h(self):
        """9:00〜18:00 休憩 60 分 → 実働 480 分"""
        wd = self._make_wd(datetime.time(9, 0), datetime.time(18, 0), 60)
        self.assertEqual(wd.calc_work_min(), 480)

    def test_no_break(self):
        """9:00〜17:00 休憩 0 分 → 実働 480 分"""
        wd = self._make_wd(datetime.time(9, 0), datetime.time(17, 0), 0)
        self.assertEqual(wd.calc_work_min(), 480)

    def test_clock_in_none(self):
        """出勤時刻 None → 0"""
        wd = self._make_wd(None, datetime.time(18, 0))
        self.assertEqual(wd.calc_work_min(), 0)

    def test_clock_out_none(self):
        """退勤時刻 None → 0"""
        wd = self._make_wd(datetime.time(9, 0), None)
        self.assertEqual(wd.calc_work_min(), 0)

    def test_both_none(self):
        """両方 None → 0"""
        wd = self._make_wd(None, None)
        self.assertEqual(wd.calc_work_min(), 0)

    def test_overtime(self):
        """9:00〜22:00 休憩 60 分 → 実働 720 分"""
        wd = self._make_wd(datetime.time(9, 0), datetime.time(22, 0), 60)
        self.assertEqual(wd.calc_work_min(), 720)

    def test_string_input(self):
        """文字列で渡しても正しく計算できる"""
        wd = self._make_wd("09:00", "18:00", 60)
        self.assertEqual(wd.calc_work_min(), 480)


class WorkDayUniquenessTest(TestCase):
    """WorkDay の unique_together 制約テスト"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass")
        WorkDay.objects.create(
            user=self.user,
            date=datetime.date(2025, 6, 1),
            status=WorkDay.Status.DRAFT,
        )

    def test_duplicate_raises_integrity_error(self):
        """同じ user + date のレコードを作ると IntegrityError"""
        with self.assertRaises(IntegrityError):
            WorkDay.objects.create(
                user=self.user,
                date=datetime.date(2025, 6, 1),  # 同じ日付
                status=WorkDay.Status.DRAFT,
            )

    def test_different_date_is_ok(self):
        """日付が違えば問題なく作れる"""
        wd = WorkDay.objects.create(
            user=self.user,
            date=datetime.date(2025, 6, 2),  # 別の日付
            status=WorkDay.Status.DRAFT,
        )
        self.assertIsNotNone(wd.pk)


class WorkDayStatusTest(TestCase):
    """WorkDay のステータス管理テスト"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", password="pass")

    def test_default_status_is_draft(self):
        """デフォルトのステータスは DRAFT"""
        wd = WorkDay.objects.create(
            user=self.user,
            date=datetime.date(2025, 6, 1),
        )
        self.assertEqual(wd.status, WorkDay.Status.DRAFT)

    def test_status_display(self):
        """get_status_display() の日本語表示"""
        wd = WorkDay(status=WorkDay.Status.SUBMITTED)
        self.assertEqual(wd.get_status_display(), "提出済み")
        wd.status = WorkDay.Status.DRAFT
        self.assertEqual(wd.get_status_display(), "一時保存")