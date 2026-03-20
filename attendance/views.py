# attendance/views.py
import datetime, csv, io
import csv as csv_module
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, TemplateView, View
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.views import View
from .forms import WorkDayForm, UserCreateForm, UserEditForm, CsvImportForm, CsvExportForm
from .models import WorkDay, ChangeLog, ImportRun, ValidationError
from .validators import validate_workday, get_error_messages
import logging
logger = logging.getLogger("attendance")

class LoginRedirectView(LoginRequiredMixin, View):
    """ログイン後のロール別リダイレクト"""
    def get(self, request):
        if request.user.is_staff:
            return redirect("admin_dash")
        return redirect("workday_list") 

class WorkDayListView(LoginRequiredMixin, ListView):
    template_name       = "attendance/workday_list.html"
    context_object_name = "workdays"

    def get_queryset(self):
        year  = int(self.request.GET.get("year",  datetime.date.today().year))
        month = int(self.request.GET.get("month", datetime.date.today().month))
        return WorkDay.objects.filter(
            user=self.request.user,
            date__year=year,
            date__month=month,
        )

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = datetime.date.today()
        year  = int(self.request.GET.get("year",  today.year))
        month = int(self.request.GET.get("month", today.month))

        total_min = sum(wd.calc_work_min() for wd in ctx["workdays"])
        submitted = ctx["workdays"].filter(status=WorkDay.Status.SUBMITTED).count()

        first_of_month = datetime.date(year, month, 1)
        prev_month = (first_of_month - datetime.timedelta(days=1)).replace(day=1)
        if month == 12:
            next_month = datetime.date(year + 1, 1, 1)
        else:
            next_month = datetime.date(year, month + 1, 1)

        ctx.update({
            "year":       year,
            "month":      month,
            "total_min":  total_min,
            "total_h":    total_min // 60,
            "total_m":    total_min % 60,
            "submitted":  submitted,
            "prev_year":  prev_month.year,
            "prev_month": prev_month.month,
            "next_year":  next_month.year,
            "next_month": next_month.month,
            "page_title": f"{year}年{month}月の勤怠",
        })
        return ctx

class WorkDayDetailView(LoginRequiredMixin, DetailView):
    template_name       = "attendance/workday_detail.html"
    context_object_name = "workday"

    def get_queryset(self):
        return WorkDay.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["changelogs"] = self.object.changelogs.all()
        ctx["page_title"] = f"{self.object.date} の勤怠詳細"
        return ctx


class WorkDayEditView(LoginRequiredMixin, View):
    template_name = "attendance/workday_edit.html"

    def _get_or_init_workday(self, request, date):
        wd, _ = WorkDay.objects.get_or_create(
            user=request.user,
            date=date,
            defaults={"break_min": 60, "status": WorkDay.Status.DRAFT},
        )
        return wd

    def get(self, request, date_str=None):
        target_date = self._parse_date(date_str)
        wd   = self._get_or_init_workday(request, target_date)

        if wd.status == WorkDay.Status.SUBMITTED:
            messages.warning(request, "提出済みのため編集できません。")
            return redirect("workday_list")

        form = WorkDayForm(instance=wd)
        return render(request, self.template_name, {
            "form": form, "workday": wd,
            "page_title": f"{target_date} の勤怠入力",
        })

    def post(self, request, date_str=None):
        target_date = self._parse_date(date_str)
        wd     = self._get_or_init_workday(request, target_date)
        form   = WorkDayForm(request.POST, instance=wd)
        action = request.POST.get("action", "draft")

        if not form.is_valid():
            return render(request, self.template_name, {
                "form": form, "workday": wd,
                "page_title": f"{target_date} の勤怠入力",
            })

        # ChangeLog 用に変更前の値を記録
        before = {
            "clock_in":  str(wd.clock_in),
            "clock_out": str(wd.clock_out),
            "break_min": str(wd.break_min),
            "status":    wd.status,
        }

        if action == "submit":
            # 提出：strict バリデーション
            cd = form.cleaned_data
            ok, error_codes = validate_workday(
                cd.get("clock_in"),
                cd.get("clock_out"),
                cd.get("break_min", 60),
            )
            if not ok:
                return render(request, self.template_name, {
                    "form":       form,
                    "workday":    wd,
                    "page_title": f"{target_date} の勤怠入力",
                    "val_errors": get_error_messages(error_codes),
                })
            wd_saved = form.save(commit=False)
            wd_saved.status = WorkDay.Status.SUBMITTED
            wd_saved.save()
            messages.success(request, f"{target_date} の勤怠を提出しました")
        else:
            # 一時保存
            wd_saved = form.save(commit=False)
            wd_saved.status = WorkDay.Status.DRAFT
            wd_saved.save()
            messages.success(request, f"{target_date} を一時保存しました")

        self._record_changelog(wd_saved, before, request.user)
        return redirect("workday_list")

    def _parse_date(self, date_str):
        if date_str:
            try:
                return datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return datetime.date.today()

    def _record_changelog(self, wd, before, changed_by):
        after = {
            "clock_in":  str(wd.clock_in),
            "clock_out": str(wd.clock_out),
            "break_min": str(wd.break_min),
            "status":    wd.status,
        }
        for field, bval in before.items():
            aval = after[field]
            if bval != aval:
                ChangeLog.objects.create(
                    workday=wd,
                    changed_by=changed_by,
                    field_name=field,
                    before_value=bval,
                    after_value=aval,
                )

class UnsubmittedUserView(LoginRequiredMixin, TemplateView):
    template_name = "attendance/unsubmitted_user.html"

    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = datetime.date.today()

        workdays_in_period = []
        d = today
        for _ in range(30):
            if d.weekday() < 5:
                workdays_in_period.append(d)
            d -= datetime.timedelta(days=1)
        workdays_in_period.reverse()

        submitted_dates = set(
            WorkDay.objects.filter(
                user=self.request.user,
                status=WorkDay.Status.SUBMITTED,
            ).values_list("date", flat=True)
        )

        unsubmitted = [
            d for d in workdays_in_period
            if d < today and d not in submitted_dates
        ]

        ctx.update({
            "unsubmitted": unsubmitted,
            "count":       len(unsubmitted),
            "page_title":  "未提出一覧",
        })
        return ctx

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """管理者専用ビューの共通 Mixin"""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        messages.error(self.request, "管理者権限が必要です")
        return redirect("workday_list")

# ── 管理者向けビュー ──────────────────────────────────────
 
class AdminDashView(StaffRequiredMixin, TemplateView):
    template_name = "attendance/admin_dash.html"
 
    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = datetime.date.today()
 
        all_users = User.objects.filter(is_active=True, is_staff=False)
 
        submitted_today = WorkDay.objects.filter(
            date=today,
            status=WorkDay.Status.SUBMITTED,
            user__is_staff=False,
        ).values("user").distinct().count()
 
        submitted_ids = WorkDay.objects.filter(
            date=today,
            status=WorkDay.Status.SUBMITTED,
        ).values_list("user_id", flat=True)
 
        not_submitted_users = all_users.exclude(pk__in=submitted_ids)
 
        recent_logs = ChangeLog.objects.select_related(
            "workday__user", "changed_by"
        ).order_by("-changed_at")[:10]
 
        ctx.update({
            "page_title":          "管理者ダッシュボード",
            "all_users_count":     all_users.count(),
            "submitted_today":     submitted_today,
            "not_submitted_count": not_submitted_users.count(),
            "not_submitted_users": not_submitted_users,
            "recent_logs":         recent_logs,
            "today":               today,
        })
        return ctx
 
 
class AdminUsersView(StaffRequiredMixin, ListView):
    template_name       = "attendance/admin_users.html"
    context_object_name = "workdays"
    paginate_by         = 50
 
    def get_queryset(self):
        qs     = WorkDay.objects.select_related("user").all()
        year   = self.request.GET.get("year")
        month  = self.request.GET.get("month")
        uid    = self.request.GET.get("user")
        status = self.request.GET.get("status")
 
        if year and month:
            qs = qs.filter(date__year=year, date__month=month)
        if uid:
            qs = qs.filter(user_id=uid)
        if status:
            qs = qs.filter(status=status)
        return qs
 
    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = datetime.date.today()
        ctx.update({
            "page_title":     "全社員勤怠一覧",
            "users":          User.objects.filter(is_active=True).order_by("username"),
            "cur_year":       self.request.GET.get("year",   str(today.year)),
            "cur_month":      self.request.GET.get("month",  str(today.month)),
            "cur_user":       self.request.GET.get("user",   ""),
            "cur_status":     self.request.GET.get("status", ""),
            "status_choices": WorkDay.Status.choices,
            "year_choices":   ["2024", "2025", "2026"],
            "month_choices":  [str(m) for m in range(1, 13)],
        })
        return ctx
 
 
class AdminUnsubView(StaffRequiredMixin, TemplateView):
    template_name = "attendance/admin_unsub.html"
 
    def get_context_data(self, **kwargs):
        ctx   = super().get_context_data(**kwargs)
        today = datetime.date.today()
 
        days = []
        d = today
        while len(days) < 5:
            if d.weekday() < 5:
                days.append(d)
            d -= datetime.timedelta(days=1)
        days.reverse()
 
        all_users = User.objects.filter(is_active=True, is_staff=False)
        report = []
        for day in days:
            submitted_ids = set(
                WorkDay.objects.filter(
                    date=day, status=WorkDay.Status.SUBMITTED
                ).values_list("user_id", flat=True)
            )
            not_submitted = [u for u in all_users if u.pk not in submitted_ids]
            report.append({
                "date":          day,
                "not_submitted": not_submitted,
                "count":         len(not_submitted),
            })
 
        ctx.update({
            "page_title": "未提出者一覧",
            "report":     report,
        })
        return ctx
 
class AdminUserListView(StaffRequiredMixin, ListView):
    """社員一覧（検索付き）"""
    template_name       = "attendance/admin_user_list.html"
    context_object_name = "users"

    def get_queryset(self):
        qs = User.objects.all().order_by("username")
        q  = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(last_name__icontains=q) |
                Q(first_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"]          = self.request.GET.get("q", "")
        ctx["page_title"] = "社員管理"
        return ctx


class AdminUserCreateView(StaffRequiredMixin, View):
    """社員新規登録"""
    template_name = "attendance/admin_user_form.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": UserCreateForm(),
            "page_title": "社員登録",
            "action": "create",
        })

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"{user.username} を登録しました")
            return redirect("admin_user_list")
        return render(request, self.template_name, {
            "form": form,
            "page_title": "社員登録",
            "action": "create",
        })


class AdminUserEditView(StaffRequiredMixin, View):
    """社員編集"""
    template_name = "attendance/admin_user_form.html"

    def _get_user(self, pk):
        return get_object_or_404(User, pk=pk)

    def get(self, request, pk):
        target = self._get_user(pk)
        form = UserEditForm(instance=target, initial={
            "is_staff":  target.is_staff,
            "is_active": target.is_active,
        })
        return render(request, self.template_name, {
            "form":       form,
            "target":     target,
            "page_title": f"{target.username} の編集",
            "action":     "edit",
        })

    def post(self, request, pk):
        target = self._get_user(pk)
        form   = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f"{target.username} を更新しました")
            return redirect("admin_user_list")
        return render(request, self.template_name, {
            "form":       form,
            "target":     target,
            "page_title": f"{target.username} の編集",
            "action":     "edit",
        })

class CsvImportView(LoginRequiredMixin, View):
    template_name = "attendance/csv_import.html"

    def get(self, request):
        return render(request, self.template_name, {
            "form": CsvImportForm(),
            "page_title": "CSV インポート",
        })

    def post(self, request):
        form = CsvImportForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, self.template_name,
                          {"form": form, "page_title": "CSV インポート"})

        csv_file = request.FILES["csv_file"]
        filename = csv_file.name

        # ── 文字コード判定 ────────────────────────────
        raw_bytes = csv_file.read()
        content   = self._decode(raw_bytes)
        if content is None:
            messages.error(request, "CSV ファイルの文字コードを判定できませんでした")
            return redirect("csv_import")

        # ── CSV パース ────────────────────────────────
        reader = csv.DictReader(io.StringIO(content))
        rows   = list(reader)

        # ── ImportRun 作成 ────────────────────────────
        run = ImportRun.objects.create(
            user=request.user,
            filename=filename,
            total_rows=len(rows),
        )

        ok_count    = 0
        skip_count  = 0
        error_count = 0
        result_rows = []   # 画面表示用

        # ── 1 行ずつ処理 ──────────────────────────────
        for i, row in enumerate(rows, start=2):  # ヘッダーが 1 行目なので 2 から
            date_str      = row.get("date",      "").strip().strip().lstrip("\ufeff").lstrip("\u200b")
            clock_in_str  = row.get("clock_in",  "").strip()
            clock_out_str = row.get("clock_out", "").strip()
            break_min_str = row.get("break_min", "60").strip()
            note          = row.get("note",      "").strip()

            row_errors = []

            # ── 日付パース ────────────────────────────
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                row_errors.append(f"日付の形式が不正です（{date_str}）")

            # ── 時刻パース ────────────────────────────
            clock_in  = None
            clock_out = None
            if clock_in_str:
                try:
                    clock_in = datetime.time.fromisoformat(clock_in_str)
                except ValueError:
                    row_errors.append(f"出勤時刻の形式が不正です（{clock_in_str}）")
            if clock_out_str:
                try:
                    clock_out = datetime.time.fromisoformat(clock_out_str)
                except ValueError:
                    row_errors.append(f"退勤時刻の形式が不正です（{clock_out_str}）")

            # ── 休憩時間パース ────────────────────────
            try:
                break_min = int(break_min_str) if break_min_str else 60
            except ValueError:
                break_min = 60
                row_errors.append("休憩時間は整数で入力してください")

            if row_errors:
                for msg in row_errors:
                    ValidationError.objects.create(
                        import_run=run, row_number=i,
                        error_code="ERR_FORMAT", message=msg,
                    )
                error_count += 1
                result_rows.append({"row": i, "date": date_str,
                                    "status": "error", "messages": row_errors})
                continue

            # ── 提出済みチェック（上書き禁止） ──────────
            existing = WorkDay.objects.filter(
                user=request.user, date=target_date
            ).first()
            if existing and existing.status == WorkDay.Status.SUBMITTED:
                skip_count += 1
                result_rows.append({
                    "row": i, "date": date_str,
                    "status": "skip",
                    "messages": ["提出済みのため上書きできません"],
                })
                continue

            # ── WorkDay を保存 ────────────────────────
            wd, _ = WorkDay.objects.update_or_create(
                user=request.user, date=target_date,
                defaults={
                    "clock_in":  clock_in,
                    "clock_out": clock_out,
                    "break_min": break_min,
                    "note":      note,
                    "status":    WorkDay.Status.DRAFT,
                }
            )
            ok_count += 1
            result_rows.append({"row": i, "date": date_str,
                                 "status": "ok", "messages": []})

        # ── ImportRun を更新 ──────────────────────────
        run.ok_count    = ok_count
        run.skip_count  = skip_count
        run.error_count = error_count
        run.save()

        return render(request, self.template_name, {
            "form":        CsvImportForm(),
            "page_title":  "CSV インポート",
            "result_rows": result_rows,
            "ok_count":    ok_count,
            "skip_count":  skip_count,
            "error_count": error_count,
            "run":         run,
        })

    def _decode(self, raw_bytes):
        """UTF-8-sig → Shift_JIS → UTF-8 の順に試みる"""
        for enc in ("utf-8-sig", "shift_jis", "utf-8"):
            try:
                text = raw_bytes.decode(enc)
                # BOM が残っていれば除去
                return text.lstrip("\ufeff")
            except UnicodeDecodeError:
                continue
        return None


def csv_sample_download(request):
    today = datetime.date.today()
    days  = []
    d = today
    while len(days) < 5:
        if d.weekday() < 5:
            days.append(d)
        d -= datetime.timedelta(days=1)
    days.reverse()

    response = HttpResponse(
        content_type="text/csv; charset=utf-8-sig"
    )
    response["Content-Disposition"] = (
        'attachment; filename="kintai_sample.csv"'
    )

    # BOM は content_type の utf-8-sig が自動付与するので
    # response.write("\ufeff") は書かない
    writer = csv_module.writer(response)
    writer.writerow(["date", "clock_in", "clock_out", "break_min", "note"])
    for day in days:
        writer.writerow([
            day.isoformat(),
            "09:00",
            "18:00",
            60,
            "",
        ])

    return response

class AdminCsvExportView(StaffRequiredMixin, View):
    template_name = "attendance/admin_csv_export.html"

    def get(self, request):
        form         = CsvExportForm(request.GET or None)
        preview_count = None

        if request.GET.get("download") and form.is_valid():
            return self._export_csv(form.cleaned_data)

        # "download" なしで条件が入力されていれば件数プレビュー
        if request.GET and form.is_valid():
            cd     = form.cleaned_data
            qs     = WorkDay.objects.filter(
                date__year=int(cd["year"]),
                date__month=int(cd["month"]),
            )
            if cd.get("user"):
                qs = qs.filter(user=cd["user"])
            if cd.get("status"):
                qs = qs.filter(status=cd["status"])
            preview_count = qs.count()

        return render(request, self.template_name, {
            "form":          form,
            "page_title":    "CSV エクスポート",
            "preview_count": preview_count,
        })

    def _export_csv(self, cleaned):
        year   = int(cleaned["year"])
        month  = int(cleaned["month"])
        user   = cleaned.get("user")
        status = cleaned.get("status")

        # ── クエリセット構築 ──────────────────────────
        qs = WorkDay.objects.select_related("user").filter(
            date__year=year, date__month=month
        )
        if user:
            qs = qs.filter(user=user)
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by("user__username", "date")

        # ── レスポンス生成 ────────────────────────────
        filename = f"kintai_{year}{month:02d}.csv"
        response = HttpResponse(
            content_type="text/csv; charset=utf-8-sig"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{filename}"'
        )
        # BOM を先頭に書き込む（Excel 対策）
        response.write("\ufeff")

        writer = csv_module.writer(response)

        # ── ヘッダー行 ────────────────────────────────
        writer.writerow([
            "社員ID", "ユーザー名", "氏名",
            "日付", "出勤時刻", "退勤時刻",
            "休憩時間(分)", "実働時間(分)", "ステータス", "備考",
        ])

        # ── データ行 ──────────────────────────────────
        for wd in qs:
            u = wd.user
            writer.writerow([
                u.pk,
                u.username,
                f"{u.last_name} {u.first_name}",
                wd.date.isoformat(),
                wd.clock_in.strftime("%H:%M")  if wd.clock_in  else "",
                wd.clock_out.strftime("%H:%M") if wd.clock_out else "",
                wd.break_min,
                wd.calc_work_min(),
                wd.get_status_display(),
                wd.note,
            ])

        return response

class AdminChangelogView(StaffRequiredMixin, ListView):
    """変更ログ一覧（管理者用）"""
    template_name       = "attendance/admin_changelog.html"
    context_object_name = "logs"
    paginate_by         = 50

    def get_queryset(self):
        qs = ChangeLog.objects.select_related(
            "workday__user", "changed_by"
        ).all()

        # フィルタ
        uid = self.request.GET.get("user")
        if uid:
            qs = qs.filter(workday__user_id=uid)

        field = self.request.GET.get("field")
        if field:
            qs = qs.filter(field_name=field)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "page_title":    "変更ログ",
            "users":         User.objects.filter(is_active=True).order_by("username"),
            "field_choices": ["clock_in", "clock_out", "break_min", "status", "note"],
            "cur_user":      self.request.GET.get("user", ""),
            "cur_field":     self.request.GET.get("field", ""),
        })
        return ctx