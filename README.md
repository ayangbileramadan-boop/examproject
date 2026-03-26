# ExamSystem — Django Project

A full-featured online exam platform built with Django.

---

## 🚀 Quick Setup

```bash
# 1. Create & activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py makemigrations accounts
python manage.py makemigrations exams
python manage.py migrate

# 4. Create a superuser (admin)
python manage.py createsuperuser

# 5. Run the server
python manage.py runserver
```

Then open: http://127.0.0.1:8000

---

## 📁 Project Structure

```
examproject/
├── examproject/          # Project config (settings, urls, wsgi)
├── accounts/             # Custom User model, auth views
│   ├── models.py         # User (student/instructor roles)
│   ├── views.py          # signup, login, logout
│   └── forms.py
├── exams/                # Core exam logic
│   ├── models.py         # Exam, Question, Submission, Answer
│   ├── views.py          # All exam views
│   └── forms.py
├── templates/            # All HTML templates
│   ├── base.html
│   ├── landing.html
│   ├── student_dashboard.html
│   ├── instructor_dashboard.html
│   ├── take_exam.html
│   ├── exam_result.html
│   ├── my_results.html
│   ├── manage_exam.html
│   ├── grade_essay.html
│   └── exam_analytics.html
├── static/               # CSS, JS, images
├── manage.py
└── requirements.txt
```

---

## 👤 User Roles

| Role       | Access | Notes |
|------------|--------|-------|
| Student    | Student dashboard, take exams, view results | Auto-approved on signup |
| Instructor | Instructor dashboard, create/manage exams, grade essays | Requires admin approval |
| Admin      | Django admin panel (/admin/) | Created via createsuperuser |

---

## ✅ Features

### Students
- Sign up and log in
- Join exams by 6-character code
- Take timed exams (auto-submit on timeout)
- MCQ, True/False, Short Answer, Essay
- Instant results after submission
- Per-question review with correct answers
- Class rank display
- Results history

### Instructors
- Sign up (pending admin approval)
- Create exams with full settings (duration, pass mark, shuffle, publish)
- Add questions (MCQ, True/False, Essay, Short Answer)
- View all submissions with scores
- Grade essay questions manually
- Exam analytics (per-question accuracy, pass rate)

### Admin
- Approve/revoke instructor accounts from /admin/
- Full CRUD on all models

---

## 🔑 Approving Instructors

1. Go to http://127.0.0.1:8000/admin/
2. Log in with your superuser credentials
3. Go to **Accounts > Users**
4. Find the instructor, check **is_approved**, and save
   *(Or select multiple and use the "Approve selected instructors" action)*

---

## 🎨 Design

- Dark theme — indigo/cyan for students, orange/rose for instructors
- Fonts: Syne (headings) + DM Sans (body)
- Fully responsive with mobile sidebar
- Animated counters, progress bars, live clock

---

## 🔧 Key URLs

| URL | View |
|-----|------|
| `/` | Landing page |
| `/accounts/signup/student/` | Student signup (POST) |
| `/accounts/signup/instructor/` | Instructor signup (POST) |
| `/accounts/login/` | Login (POST) |
| `/accounts/logout/` | Logout |
| `/dashboard/` | Student dashboard |
| `/instructor/` | Instructor dashboard |
| `/join/` | Join exam by code |
| `/exam/<pk>/take/` | Take exam |
| `/exam/<pk>/result/` | View result |
| `/results/` | All my results |
| `/instructor/exam/create/` | Create exam |
| `/instructor/exam/<pk>/manage/` | Manage exam + questions |
| `/instructor/exam/<pk>/analytics/` | Exam analytics |
| `/instructor/essay/<pk>/grade/` | Grade essay |
| `/admin/` | Django admin |
