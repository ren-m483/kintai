# attendance/management/commands/seed_dev.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import WorkDay, ChangeLog
import datetime
import random


class Command(BaseCommand):
    help = "開発用テストデータを投入する"

    def handle(self, *args, **options):
        self.stdout.write("テストデータを投入中...")

        # ── ユーザー作成 ────────────────────────────────────
        admin = self._get_or_create_user(
            "admin", "管理", "者", "admin@example.com",
            password="password", is_staff=True,
        )
        tanaka = self._get_or_create_user(
            "tanaka", "田中", "一郎", "tanaka@example.com",
            password="password"
        )
        sato = self._get_or_create_user(
            "sato", "佐藤", "花子", "sato@example.com",
            password="password"
        )
        suzuki = self._get_or_create_user(
            "suzuki", "鈴木", "次郎", "suzuki@example.com",
            password="password"
        )

        # ── WorkDay 作成（直近 10 営業日分） ────────────────
        users = [tanaka, sato, suzuki]
        today = datetime.date.today()
        work_days = self._get_recent_workdays(today, count=10)

        for user in users:
            for i, day in enumerate(work_days):
                # 最後の 2 日は未提出（下書き）にする
                if i < len(work_days) - 2:
                    status = WorkDay.Status.SUBMITTED
                    ci = datetime.time(9, 0)
                    co = datetime.time(random.choice([17, 18, 19]), 0)
                else:
                    status = WorkDay.Status.DRAFT
                    ci = datetime.time(9, 0) if i < len(work_days) - 1 else None
                    co = datetime.time(18, 0) if i < len(work_days) - 1 else None

                WorkDay.objects.update_or_create(
                    user=user, date=day,
                    defaults={
                        "clock_in":  ci,
                        "clock_out": co,
                        "break_min": 60,
                        "status":    status,
                    }
                )

        count = WorkDay.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"完了: ユーザー 4 名 / 勤怠レコード {count} 件を投入しました"
        ))
        self.stdout.write("")
        self.stdout.write("ログイン情報:")
        self.stdout.write("  admin   / password  (管理者)")
        self.stdout.write("  tanaka  / password  (一般)")
        self.stdout.write("  sato    / password  (一般)")
        self.stdout.write("  suzuki  / password  (一般)")

    def _get_or_create_user(self, username, last, first, email,
                             password, is_staff=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "last_name":  last,
                "first_name": first,
                "email":      email,
                "is_staff":   is_staff,
            }
        )
        user.set_password(password)
        user.is_active = True
        user.save()
        return user

    def _get_recent_workdays(self, today, count):
        """土日を除いた直近 count 日分を返す"""
        days = []
        d = today
        while len(days) < count:
            if d.weekday() < 5:   # 0=月〜4=金
                days.append(d)
            d -= datetime.timedelta(days=1)
        return list(reversed(days))