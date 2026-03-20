# attendance/context_processors.py
from .models import WorkDay


def global_context(request):
    """全テンプレートに渡すグローバル変数"""
    if not request.user.is_authenticated:
        return {}

    # ログイン中ユーザーの未提出件数
    unsubmitted_count = WorkDay.objects.filter(
        user=request.user,
        status=WorkDay.Status.DRAFT,
        clock_in__isnull=False,
        clock_out__isnull=False,
    ).count()

    return {
        "unsubmitted_count": unsubmitted_count,
    }