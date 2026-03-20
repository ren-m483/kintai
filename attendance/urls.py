from django.urls import path
from . import views
from django.views.defaults import page_not_found

urlpatterns = [
    path("admin-login/", views.LoginRedirectView.as_view(), name="login_redirect"),

    path("",                              views.WorkDayListView.as_view(),   name="workday_list"),
    path("workdays/<int:pk>/",            views.WorkDayDetailView.as_view(), name="workday_detail"),
    path("workdays/edit/",                views.WorkDayEditView.as_view(),   name="workday_edit"),
    path("workdays/edit/<str:date_str>/", views.WorkDayEditView.as_view(),   name="workday_edit_date"),
    path("unsubmitted/",                  views.UnsubmittedUserView.as_view(),  name="unsubmitted_user"),
    path("csv/import/",               views.CsvImportView.as_view(),     name="csv_import"),
    path("csv/sample/",               views.csv_sample_download,         name="csv_sample"),

    # 管理者
    path("admin-panel/",             views.AdminDashView.as_view(),   name="admin_dash"),
    path("admin-panel/workdays/",    views.AdminUsersView.as_view(),  name="admin_workdays"),
    path("admin-panel/unsubmitted/", views.AdminUnsubView.as_view(),  name="admin_unsub"),
    path("admin-panel/users/",        views.AdminUserListView.as_view(),  name="admin_user_list"),
    path("admin-panel/users/create/", views.AdminUserCreateView.as_view(), name="admin_user_create"),
    path("admin-panel/users/<int:pk>/edit/", views.AdminUserEditView.as_view(), name="admin_user_edit"),
    path("admin-panel/csv/export/",   views.AdminCsvExportView.as_view(), name="admin_csv_export"),
    path("admin-panel/changelog/",    views.AdminChangelogView.as_view(), name="admin_changelog"),
]

urlpatterns += [
    path("test-404/", lambda req: page_not_found(req, None)),
]