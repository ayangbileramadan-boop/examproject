# Render Deployment Fix - TODO

## Plan Steps (Approved by user):
1. [x] Create TODO.md with breakdown
2. [x] Update exam/proclife: Fix gunicorn command to 'gunicorn exam.examproject.wsgi:application'
3. [x] Edit exam/examproject/settings.py: Fix MIDDLEWARE comma, consolidate DEBUG/ALLOWED_HOSTS/STATIC_ROOT, add PostgreSQL DATABASES config
4. [x] Create exam/runtime.txt with 'python-3.14.3'
6. [ ] attempt_completion with push/deploy instructions

## Notes
- After all steps: git add/commit/push to trigger Render redeploy
- Set DATABASE_URL on Render dashboard after push

