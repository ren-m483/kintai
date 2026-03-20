# attendance/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth.models import User
from attendance.forms import UserCreateForm, UserEditForm, WorkDayForm


class UserCreateFormTest(TestCase):
    """UserCreateForm のバリデーションテスト"""

    def _valid_data(self, **override):
        data = {
            "username":   "newuser",
            "last_name":  "新",
            "first_name": "ユーザー",
            "email":      "new@example.com",
            "password1":  "SecurePass123!",
            "password2":  "SecurePass123!",
        }
        data.update(override)
        return data

    def test_valid_form(self):
        """正常入力は is_valid() = True"""
        form = UserCreateForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_password_mismatch(self):
        """パスワード不一致 → バリデーションエラー"""
        form = UserCreateForm(data=self._valid_data(password2="DifferentPass!"))
        self.assertFalse(form.is_valid())

    def test_duplicate_username(self):
        """既存のユーザー名 → バリデーションエラー"""
        User.objects.create_user("newuser", password="pass")
        form = UserCreateForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_short_password(self):
        """短いパスワード → バリデーションエラー"""
        form = UserCreateForm(data=self._valid_data(
            password1="abc", password2="abc"
        ))
        self.assertFalse(form.is_valid())


class WorkDayFormTest(TestCase):
    """WorkDayForm のバリデーションテスト"""

    def test_valid_form(self):
        """正常入力は is_valid() = True"""
        form = WorkDayForm(data={
            "clock_in":  "09:00",
            "clock_out": "18:00",
            "break_min": 60,
            "note":      "",
        })
        self.assertTrue(form.is_valid())

    def test_empty_form_is_valid(self):
        """全フィールド空でも is_valid() = True（一時保存用）"""
        form = WorkDayForm(data={
            "clock_in":  "",
            "clock_out": "",
            "break_min": 60,
            "note":      "",
        })
        self.assertTrue(form.is_valid())

    def test_invalid_time_format(self):
        """時刻フォーマット不正 → is_valid() = False"""
        form = WorkDayForm(data={
            "clock_in":  "25:00",   # 存在しない時刻
            "clock_out": "18:00",
            "break_min": 60,
            "note":      "",
        })
        self.assertFalse(form.is_valid())