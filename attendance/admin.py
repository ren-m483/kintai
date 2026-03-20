# attendance/admin.py
from django.contrib import admin
from .models import WorkDay, ChangeLog, ImportRun, ValidationError


@admin.register(WorkDay)
class WorkDayAdmin(admin.ModelAdmin):
    list_display  = ("user", "date", "clock_in", "clock_out",
                     "break_min", "calc_work_min", "status")
    list_filter   = ("status", "date")
    search_fields = ("user__username", "user__last_name")
    ordering      = ("-date",)
    date_hierarchy = "date"

    def calc_work_min(self, obj):
        """実働時間を Admin 一覧に表示するカラム"""
        m = obj.calc_work_min()
        return f"{m // 60}h{m % 60:02d}m" if m else "—"
    calc_work_min.short_description = "実働"


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display  = ("workday", "changed_by", "field_name",
                     "before_value", "after_value", "changed_at")
    list_filter   = ("field_name",)
    search_fields = ("workday__user__username",)
    readonly_fields = ("changed_at",)


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display  = ("user", "filename", "total_rows",
                     "ok_count", "error_count", "executed_at")
    readonly_fields = ("executed_at",)


@admin.register(ValidationError)
class ValidationErrorAdmin(admin.ModelAdmin):
    list_display  = ("import_run", "row_number", "error_code", "message")
    list_filter   = ("error_code",)

admin.site.site_header = "KINTAI 管理サイト"
admin.site.site_title  = "KINTAI Admin"
admin.site.index_title = "管理メニュー"