#!/usr/bin/env bash
set -o errexit   # エラーが起きたら即終了

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate