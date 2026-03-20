# attendance/forms.py
from django import forms
from .models import WorkDay
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class WorkDayForm(forms.ModelForm):
    """勤怠入力フォーム（一時保存・提出共用）"""

    class Meta:
        model  = WorkDay
        fields = ["clock_in", "clock_out", "break_min", "note"]
        widgets = {
            "clock_in":  forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "clock_out": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "break_min": forms.NumberInput(
                attrs={"min": 0, "max": 480, "class": "form-control"}
            ),
            "note": forms.Textarea(
                attrs={"rows": 2, "class": "form-control",
                       "placeholder": "備考があれば入力してください"}
            ),
        }
        labels = {
            "clock_in":  "出勤時刻",
            "clock_out": "退勤時刻",
            "break_min": "休憩時間（分）",
            "note":      "備考",
        }

class UserCreateForm(forms.ModelForm):
    """社員新規登録フォーム"""
    password1 = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="パスワード（確認）",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    is_staff = forms.BooleanField(
        label="管理者権限",
        required=False,
    )

    class Meta:
        model  = User
        fields = ["username", "last_name", "first_name", "email"]
        widgets = {
            "username":   forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
        }
        labels = {
            "username":   "ユーザー名（ログイン ID）",
            "last_name":  "姓",
            "first_name": "名",
            "email":      "メールアドレス",
        }

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("password1")
        pw2 = cleaned.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("パスワードが一致しません")
        if pw1:
            try:
                validate_password(pw1)
            except Exception as e:
                raise forms.ValidationError(str(e))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = self.cleaned_data.get("is_staff", False)
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """社員編集フォーム（パスワード変更は任意）"""
    password_new = forms.CharField(
        label="新しいパスワード（変更する場合のみ入力）",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
    )
    is_staff  = forms.BooleanField(label="管理者権限", required=False)
    is_active = forms.BooleanField(label="有効（無効にするとログイン不可）", required=False)

    class Meta:
        model  = User
        fields = ["username", "last_name", "first_name", "email"]
        widgets = {
            "username":   forms.TextInput(attrs={"class": "form-control"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "email":      forms.EmailInput(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff  = self.cleaned_data.get("is_staff",  False)
        user.is_active = self.cleaned_data.get("is_active", True)
        pw = self.cleaned_data.get("password_new")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user


class CsvImportForm(forms.Form):
    """CSV インポートフォーム"""
    csv_file = forms.FileField(
        label="CSV ファイル",
        widget=forms.FileInput(attrs={"accept": ".csv", "class": "form-control"}),
    )

class CsvExportForm(forms.Form):
    """CSV エクスポートフォーム（管理者用）"""

    year = forms.ChoiceField(
        label="年",
        choices=[],   # __init__ で動的に生成
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    month = forms.ChoiceField(
        label="月",
        choices=[(m, f"{m}月") for m in range(1, 13)],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    user = forms.ModelChoiceField(
        label="社員（空欄 = 全員）",
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        empty_label="全社員",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    status = forms.ChoiceField(
        label="ステータス",
        choices=[
            ("",          "すべて"),
            ("SUBMITTED", "提出済み"),
            ("DRAFT",     "下書き"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import datetime
        today = datetime.date.today()
        years = [(y, f"{y}年") for y in range(today.year - 2, today.year + 1)]
        self.fields["year"].choices  = years
        self.fields["year"].initial  = today.year
        self.fields["month"].initial = today.month