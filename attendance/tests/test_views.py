# attendance/tests/test_views.py
import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from attendance.models import WorkDay


class AuthRedirectTest(TestCase):
    """未ログイン時のリダイレクトテスト"""

    def setUp(self):
        self.client = Client()

    def test_workday_list_requires_login(self):
        """未ログインで / → /login/ にリダイレクト"""
        response = self.client.get(reverse("workday_list"))
        self.assertRedirects(response, "/login/?next=/")

    def test_workday_edit_requires_login(self):
        """未ログインで /workdays/edit/ → /login/ にリダイレクト"""
        response = self.client.get(reverse("workday_edit"))
        self.assertRedirects(response, "/login/?next=/workdays/edit/")

    def test_admin_dash_requires_login(self):
        """未ログインで /admin-panel/ → /login/ にリダイレクト"""
        response = self.client.get(reverse("admin_dash"))
        self.assertRedirects(response, "/login/?next=/admin-panel/")


class StaffOnlyViewTest(TestCase):
    """管理者専用ビューの権限テスト"""

    def setUp(self):
        self.client = Client()
        self.user  = User.objects.create_user("tanaka", password="pass")
        self.admin = User.objects.create_user("admin",  password="pass", is_staff=True)

    def test_general_user_cannot_access_admin_dash(self):
        """一般ユーザーが /admin-panel/ にアクセス → ブロック"""
        self.client.login(username="tanaka", password="pass")
        response = self.client.get(reverse("admin_dash"))
        # StaffRequiredMixin はリダイレクトを返す設計
        self.assertNotEqual(response.status_code, 200)

    def test_admin_can_access_admin_dash(self):
        """管理者は /admin-panel/ にアクセスできる"""
        self.client.login(username="admin", password="pass")
        response = self.client.get(reverse("admin_dash"))
        self.assertEqual(response.status_code, 200)


class WorkDayOwnershipTest(TestCase):
    """他人のデータにアクセスできないことのテスト"""

    def setUp(self):
        self.client  = Client()
        self.tanaka  = User.objects.create_user("tanaka", password="pass")
        self.sato    = User.objects.create_user("sato",   password="pass")
        # 田中さんの WorkDay
        self.tanaka_wd = WorkDay.objects.create(
            user=self.tanaka,
            date=datetime.date(2025, 6, 1),
            status=WorkDay.Status.DRAFT,
        )

    def test_user_can_see_own_workday(self):
        """自分の WorkDay 詳細は見られる"""
        self.client.login(username="tanaka", password="pass")
        response = self.client.get(
            reverse("workday_detail", args=[self.tanaka_wd.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_see_others_workday(self):
        """他人の WorkDay 詳細は 404"""
        self.client.login(username="sato", password="pass")
        response = self.client.get(
            reverse("workday_detail", args=[self.tanaka_wd.pk])
        )
        self.assertEqual(response.status_code, 404)

class WorkDaySubmitTest(TestCase):
    """勤怠提出フローのテスト"""

    def setUp(self):
        self.client = Client()
        self.user   = User.objects.create_user("tanaka", password="pass")
        self.client.login(username="tanaka", password="pass")

    def test_submit_valid_workday(self):
        """正常なデータを提出すると SUBMITTED になる"""
        response = self.client.post(
            reverse("workday_edit"),
            {
                "clock_in":  "09:00",
                "clock_out": "18:00",
                "break_min": 60,
                "note":      "",
                "action":    "submit",
            },
        )
        # 成功 → / にリダイレクト
        self.assertRedirects(response, reverse("workday_list"))

        # DB を確認
        wd = WorkDay.objects.get(user=self.user, date=datetime.date.today())
        self.assertEqual(wd.status, WorkDay.Status.SUBMITTED)

    def test_submit_invalid_workday_stays_draft(self):
        """バリデーションエラーのある提出はステータスが変わらない"""
        # まず DRAFT レコードを作る
        WorkDay.objects.create(
            user=self.user,
            date=datetime.date.today(),
            status=WorkDay.Status.DRAFT,
        )
        response = self.client.post(
            reverse("workday_edit"),
            {
                "clock_in":  "18:00",   # 退勤より遅い
                "clock_out": "09:00",   # → ERR_ORDER
                "break_min": 60,
                "note":      "",
                "action":    "submit",
            },
        )
        # リダイレクトせずフォームを再表示
        self.assertEqual(response.status_code, 200)
        # ステータスが DRAFT のまま
        wd = WorkDay.objects.get(user=self.user, date=datetime.date.today())
        self.assertEqual(wd.status, WorkDay.Status.DRAFT)

    def test_draft_save_does_not_validate_strictly(self):
        """一時保存は strict バリデーションなしで保存できる"""
        response = self.client.post(
            reverse("workday_edit"),
            {
                "clock_in":  "",   # 未入力でも一時保存は OK
                "clock_out": "",
                "break_min": 60,
                "note":      "",
                "action":    "draft",
            },
        )
        self.assertRedirects(response, reverse("workday_list"))