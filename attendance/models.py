# attendance/models.py
from django.db import models
from django.contrib.auth.models import User


# ─────────────────────────────────────────────────────────
#  WorkDay：1 ユーザー × 1 日付 = 1 レコード
# ─────────────────────────────────────────────────────────
class WorkDay(models.Model):

    class Status(models.TextChoices):
        DRAFT     = "DRAFT",     "一時保存"
        SUBMITTED = "SUBMITTED", "提出済み"

    user      = models.ForeignKey(
                    User, on_delete=models.CASCADE,
                    related_name="workdays", verbose_name="社員")
    date      = models.DateField(verbose_name="日付")
    clock_in  = models.TimeField(null=True, blank=True, verbose_name="出勤時刻")
    clock_out = models.TimeField(null=True, blank=True, verbose_name="退勤時刻")
    break_min = models.IntegerField(default=60, verbose_name="休憩時間（分）")
    note      = models.TextField(blank=True, default="", verbose_name="備考")
    status    = models.CharField(
                    max_length=16,
                    choices=Status.choices,
                    default=Status.DRAFT,
                    verbose_name="ステータス")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True,     null=True)

    class Meta:
        unique_together = [("user", "date")]
        ordering        = ["-date"]
        verbose_name      = "勤怠レコード"
        verbose_name_plural = "勤怠レコード"

    def calc_work_min(self):
        """実働時間（分）を返す。未入力なら 0。"""
        if not (self.clock_in and self.clock_out):
            return 0
        # 文字列で来た場合も吸収する
        ci = self.clock_in  if hasattr(self.clock_in,  "hour") \
             else __import__("datetime").time.fromisoformat(str(self.clock_in))
        co = self.clock_out if hasattr(self.clock_out, "hour") \
             else __import__("datetime").time.fromisoformat(str(self.clock_out))
        total = (co.hour * 60 + co.minute) - (ci.hour * 60 + ci.minute)
        return max(0, total - self.break_min)

    def __str__(self):
        return f"{self.user.username} | {self.date} | {self.get_status_display()}"


# ─────────────────────────────────────────────────────────
#  ChangeLog：勤怠の変更履歴
# ─────────────────────────────────────────────────────────
class ChangeLog(models.Model):
    workday    = models.ForeignKey(
                    WorkDay, on_delete=models.CASCADE,
                    related_name="changelogs", verbose_name="勤怠レコード")
    changed_by = models.ForeignKey(
                    User, on_delete=models.SET_NULL,
                    null=True, related_name="changelogs", verbose_name="変更者")
    field_name   = models.CharField(max_length=32, verbose_name="フィールド名")
    before_value = models.TextField(blank=True, default="", verbose_name="変更前")
    after_value  = models.TextField(blank=True, default="", verbose_name="変更後")
    changed_at   = models.DateTimeField(auto_now_add=True, verbose_name="変更日時")

    class Meta:
        ordering = ["-changed_at"]
        verbose_name = "変更ログ"
        verbose_name_plural = "変更ログ"

    def __str__(self):
        return f"{self.workday} | {self.field_name} | {self.changed_at:%Y-%m-%d %H:%M}"


# ─────────────────────────────────────────────────────────
#  ImportRun：CSV インポートの実行記録
# ─────────────────────────────────────────────────────────
class ImportRun(models.Model):
    user        = models.ForeignKey(
                    User, on_delete=models.CASCADE,
                    related_name="import_runs", verbose_name="実行者")
    filename    = models.CharField(max_length=255, verbose_name="ファイル名")
    total_rows  = models.IntegerField(default=0, verbose_name="総行数")
    ok_count    = models.IntegerField(default=0, verbose_name="成功件数")
    skip_count  = models.IntegerField(default=0, verbose_name="スキップ件数")
    error_count = models.IntegerField(default=0, verbose_name="エラー件数")
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name="実行日時")

    class Meta:
        ordering = ["-executed_at"]
        verbose_name = "CSVインポート記録"
        verbose_name_plural = "CSVインポート記録"

    def __str__(self):
        return f"{self.user.username} | {self.filename} | {self.executed_at:%Y-%m-%d %H:%M}"


# ─────────────────────────────────────────────────────────
#  ValidationError：インポート時のバリデーションエラー
# ─────────────────────────────────────────────────────────
class ValidationError(models.Model):
    import_run = models.ForeignKey(
                    ImportRun, on_delete=models.CASCADE,
                    related_name="validation_errors", verbose_name="インポート記録")
    row_number = models.IntegerField(verbose_name="行番号")
    error_code = models.CharField(max_length=32, verbose_name="エラーコード")
    message    = models.TextField(verbose_name="エラーメッセージ")

    class Meta:
        ordering = ["row_number"]
        verbose_name = "バリデーションエラー"
        verbose_name_plural = "バリデーションエラー"

    def __str__(self):
        return f"{self.import_run} | {self.row_number}行目 | {self.error_code}"