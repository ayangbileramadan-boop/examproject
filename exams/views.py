from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Sum, Q
from django.core.mail import send_mail
from django.conf import settings
import json, random

from .models import Exam, Question, Submission, Answer
from .forms import ExamForm, QuestionForm, JoinExamForm, EssayGradeForm
from accounts.models import User


# ─── PUBLIC ────────────────────────────────────────────────────────────────────

def landing(request):
    # Always show the landing page - let user choose to go to dashboard if logged in
    return render(request, 'landing.html')


def landing_page(request):
    # Always show the landing page - let user choose to go to dashboard if logged in
    return render(request, 'landing.html')


# ─── STUDENT ───────────────────────────────────────────────────────────────────

def _student_required(view_func):
    """Decorator: must be logged in as approved student."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        if not request.user.is_student:
            messages.error(request, "Access denied.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


@_student_required
def student_dashboard(request):
    student = request.user
    submissions = Submission.objects.filter(
        student=student, is_submitted=True
    ).select_related('exam').order_by('-submitted_at')

    completed = submissions.count()
    avg_score = submissions.aggregate(avg=Avg('score_percentage'))['avg'] or 0

    # Upcoming/live exams from APPROVED instructors only
    taken_exam_ids = submissions.values_list('exam_id', flat=True)
    available_exams = Exam.objects.filter(
        is_published=True,
        instructor__is_approved=True  # Only show exams from approved instructors
    ).exclude(id__in=taken_exam_ids).order_by('start_time')[:5]

    # In-progress
    in_progress = Submission.objects.filter(
        student=student, is_submitted=False
    ).select_related('exam').first()

    # Subject performance
    subject_data = {}
    for sub in submissions:
        subj = sub.exam.subject or sub.exam.title
        if subj not in subject_data:
            subject_data[subj] = []
        subject_data[subj].append(sub.score_percentage)
    subject_avg = {k: round(sum(v)/len(v), 1) for k, v in subject_data.items()}

    context = {
        'student': student,
        'completed': completed,
        'avg_score': round(avg_score, 1),
        'recent_submissions': submissions[:5],
        'available_exams': available_exams,
        'in_progress': in_progress,
        'subject_avg': subject_avg,
        'join_form': JoinExamForm(),
    }
    return render(request, 'student_dashboard.html', context)


@_student_required
def join_exam(request):
    if request.method == 'POST':
        form = JoinExamForm(request.POST)
        if form.is_valid():
            exam = form.exam
            # Check already submitted
            existing = Submission.objects.filter(student=request.user, exam=exam).first()
            if existing:
                if existing.is_submitted:
                    messages.info(request, "You've already completed this exam.")
                    return redirect('exams:exam_result', pk=existing.pk)
                return redirect('exams:take_exam', pk=exam.pk)
            return redirect('exams:take_exam', pk=exam.pk)
        else:
            messages.error(request, "Invalid exam code. Please check and try again.")
    return redirect('exams:student_dashboard')


@_student_required
def take_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk, is_published=True)
    student = request.user
    now = timezone.now()

    # Check if instructor is approved
    if not exam.instructor.is_approved:
        messages.error(request, "This exam is not available yet. The instructor's account is pending approval.")
        return redirect('exams:student_dashboard')

    # Check already submitted
    existing = Submission.objects.filter(student=student, exam=exam, is_submitted=True).first()
    if existing:
        messages.info(request, "You have already submitted this exam.")
        return redirect('exams:exam_result', pk=existing.pk)

    # Check exam is upcoming - REDIRECT if not started yet (don't show questions!)
    exam_is_upcoming = exam.status == 'upcoming'
    if exam.status == 'closed':
        messages.warning(request, "This exam is closed.")
        return redirect('exams:student_dashboard')
    
    # If exam has a start time and hasn't started yet, redirect to dashboard with info
    if exam.start_time and exam.start_time > now:
        messages.info(request, f"This exam hasn't started yet. It will begin on {exam.start_time.strftime('%B %d, %Y at %I:%M %p')}.")
        return redirect('exams:student_dashboard')

    # Create or resume submission
    submission, created = Submission.objects.get_or_create(student=student, exam=exam)

    questions = list(exam.questions.all())
    if exam.shuffle_questions and created:
        random.shuffle(questions)

    if request.method == 'POST':
        # Save all answers
        for question in questions:
            ans_text = request.POST.get(f'q_{question.pk}', '').strip()
            Answer.objects.update_or_create(
                submission=submission,
                question=question,
                defaults={'answer_text': ans_text}
            )
        # Mark submitted
        submission.is_submitted = True
        submission.submitted_at = timezone.now()
        elapsed = (submission.submitted_at - submission.started_at).seconds
        submission.time_taken_seconds = elapsed
        submission.save()
        # Auto-grade
        submission.calculate_score()
        messages.success(request, "Exam submitted successfully!")
        return redirect('exams:exam_result', pk=submission.pk)

    # Load existing answers
    existing_answers = {a.question_id: a.answer_text for a in submission.answers.all()}

    # Time remaining
    deadline = None
    if exam.end_time:
        deadline = exam.end_time
    exam_deadline_ts = int(deadline.timestamp() * 1000) if deadline else None
    start_ts = int(submission.started_at.timestamp() * 1000)
    duration_ms = exam.duration_minutes * 60 * 1000
    auto_submit_ts = start_ts + duration_ms

    context = {
        'exam': exam,
        'submission': submission,
        'questions': questions,
        'existing_answers': existing_answers,
        'auto_submit_ts': auto_submit_ts,
        'exam_deadline_ts': exam_deadline_ts,
        'exam_is_upcoming': exam_is_upcoming,
    }
    return render(request, 'take_exam.html', context)


@_student_required
def exam_result(request, pk):
    submission = get_object_or_404(Submission, pk=pk, student=request.user, is_submitted=True)
    exam = submission.exam
    answers = submission.answers.select_related('question').order_by('question__order')

    # Class rank
    all_submissions = Submission.objects.filter(
        exam=exam, is_submitted=True
    ).order_by('-score_percentage')
    rank = list(all_submissions.values_list('id', flat=True)).index(submission.id) + 1

    context = {
        'submission': submission,
        'exam': exam,
        'answers': answers,
        'rank': rank,
        'total_in_class': all_submissions.count(),
    }
    return render(request, 'exam_result.html', context)


@_student_required
def my_results(request):
    submissions = Submission.objects.filter(
        student=request.user, is_submitted=True
    ).select_related('exam').order_by('-submitted_at')
    return render(request, 'my_results.html', {'submissions': submissions})


# ─── INSTRUCTOR ────────────────────────────────────────────────────────────────

def _instructor_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        if not request.user.is_instructor:
            messages.error(request, "Access denied. Instructors only.")
            return redirect('landing')
        if not request.user.is_approved:
            messages.warning(request, "Your account is pending approval.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


@_instructor_required
def instructor_dashboard(request):
    instructor = request.user
    exams = Exam.objects.filter(instructor=instructor).annotate(
        sub_count=Count('submissions', filter=Q(submissions__is_submitted=True))
    )

    total_students = Submission.objects.filter(
        exam__instructor=instructor, is_submitted=True
    ).values('student').distinct().count()
    
    # Active students - currently taking an exam (in-progress submissions)
    active_students = Submission.objects.filter(
        exam__instructor=instructor, is_submitted=False
    ).select_related('student', 'exam')

    avg_score = Submission.objects.filter(
        exam__instructor=instructor, is_submitted=True
    ).aggregate(avg=Avg('score_percentage'))['avg'] or 0

    # Essays pending grading
    pending_essays = Answer.objects.filter(
        question__question_type='essay',
        question__exam__instructor=instructor,
        instructor_marks__isnull=True,
        submission__is_submitted=True
    ).select_related('submission__student', 'question__exam').order_by('-submission__submitted_at')

    # Recent submissions
    recent_submissions = Submission.objects.filter(
        exam__instructor=instructor, is_submitted=True
    ).select_related('student', 'exam').order_by('-submitted_at')[:8]

    # Top students
    top_students = Submission.objects.filter(
        exam__instructor=instructor, is_submitted=True
    ).select_related('student', 'exam').order_by('-score_percentage')[:5]

    context = {
        'instructor': instructor,
        'exams': exams,
        'total_exams': exams.count(),
        'total_students': total_students,
        'active_students': active_students,
        'active_students_count': active_students.count(),
        'avg_score': round(avg_score, 1),
        'pending_essays': pending_essays,
        'pending_essays_count': pending_essays.count(),
        'recent_submissions': recent_submissions,
        'top_students': top_students,
        'exam_form': ExamForm(),
    }
    return render(request, 'instructor_dashboard.html', context)


@_instructor_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.instructor = request.user
            exam.save()
            messages.success(request, f"Exam '{exam.title}' created! Code: {exam.code}")
            return redirect('exams:manage_exam', pk=exam.pk)
        else:
            for field, errors in form.errors.items():
                for e in errors:
                    messages.error(request, f"{field}: {e}")
    return redirect('exams:instructor_dashboard')


@_instructor_required
def manage_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk, instructor=request.user)
    questions = exam.questions.all()
    question_form = QuestionForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_question':
            qform = QuestionForm(request.POST)
            if qform.is_valid():
                q = qform.save(commit=False)
                q.exam = exam
                q.order = questions.count() + 1
                q.save()
                messages.success(request, "Question added.")
                return redirect('exams:manage_exam', pk=pk)
            else:
                question_form = qform
                for field, errors in qform.errors.items():
                    for e in errors:
                        messages.error(request, f"{e}")
        elif action == 'delete_question':
            qid = request.POST.get('question_id')
            Question.objects.filter(pk=qid, exam=exam).delete()
            messages.success(request, "Question deleted.")
            return redirect('exams:manage_exam', pk=pk)
        elif action == 'update_exam':
            eform = ExamForm(request.POST, instance=exam)
            if eform.is_valid():
                eform.save()
                messages.success(request, "Exam updated.")
                return redirect('exams:manage_exam', pk=pk)

    submissions = exam.submissions.filter(is_submitted=True).select_related('student').order_by('-score_percentage')

    context = {
        'exam': exam,
        'questions': questions,
        'question_form': question_form,
        'exam_form': ExamForm(instance=exam),
        'submissions': submissions,
    }
    return render(request, 'manage_exam.html', context)


@_instructor_required
def delete_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk, instructor=request.user)
    if request.method == 'POST':
        title = exam.title
        exam.delete()
        messages.success(request, f"Exam '{title}' deleted.")
    return redirect('exams:instructor_dashboard')


@_instructor_required
def grade_essay(request, answer_pk):
    answer = get_object_or_404(
        Answer,
        pk=answer_pk,
        question__exam__instructor=request.user,
        question__question_type='essay'
    )
    if request.method == 'POST':
        form = EssayGradeForm(request.POST, instance=answer)
        if form.is_valid():
            form.save()
            # Recalculate submission score adding manual marks
            sub = answer.submission
            auto_score = sub.answers.filter(
                is_correct=True
            ).aggregate(total=Sum('question__marks'))['total'] or 0
            essay_score = sub.answers.filter(
                question__question_type='essay',
                instructor_marks__isnull=False
            ).aggregate(total=Sum('instructor_marks'))['total'] or 0
            sub.score = auto_score + essay_score
            total = sub.exam.total_marks
            sub.score_percentage = round((sub.score / total * 100), 1) if total else 0
            sub.save()
            messages.success(request, f"Essay graded. {answer.submission.student.username} now scores {sub.score_percentage}%.")
            return redirect('exams:instructor_dashboard')
    else:
        form = EssayGradeForm(instance=answer)

    context = {
        'answer': answer,
        'form': form,
        'max_marks': answer.question.marks,
    }
    return render(request, 'grade_essay.html', context)


@_instructor_required
def exam_analytics(request, pk):
    exam = get_object_or_404(Exam, pk=pk, instructor=request.user)
    submissions = exam.submissions.filter(is_submitted=True).select_related('student')

    # Per-question accuracy
    question_stats = []
    for q in exam.questions.all():
        total = submissions.count()
        correct = Answer.objects.filter(
            submission__exam=exam,
            question=q,
            is_correct=True
        ).count()
        question_stats.append({
            'question': q,
            'correct': correct,
            'total': total,
            'accuracy': round(correct / total * 100, 1) if total else 0,
        })

    context = {
        'exam': exam,
        'submissions': submissions,
        'question_stats': question_stats,
        'avg_score': exam.average_score,
        'pass_rate': round(
            submissions.filter(score_percentage__gte=exam.pass_mark).count() / submissions.count() * 100, 1
        ) if submissions.count() else 0,
    }
    return render(request, 'exam_analytics.html', context)


# ─── ADMIN ─────────────────────────────────────────────────────────────────────

def _admin_required(view_func):
    """Decorator: must be logged in as admin."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        if not request.user.is_admin:
            messages.error(request, "Access denied. Admin only.")
            return redirect('landing')
        return view_func(request, *args, **kwargs)
    return wrapper


@_admin_required
def admin_dashboard(request):
    # Get all users by role
    students = User.objects.filter(role=User.ROLE_STUDENT).order_by('-date_joined')
    instructors = User.objects.filter(role=User.ROLE_INSTRUCTOR).order_by('-date_joined')
    admins = User.objects.filter(role=User.ROLE_ADMIN).order_by('-date_joined')
    
    # Get all exams
    exams = Exam.objects.all().order_by('-created_at')
    
    # Get stats
    total_students = students.count()
    total_instructors = instructors.count()
    total_exams = exams.count()
    total_submissions = Submission.objects.filter(is_submitted=True).count()
    
    # Recent activity
    recent_submissions = Submission.objects.filter(
        is_submitted=True
    ).select_related('student', 'exam').order_by('-submitted_at')[:10]
    
    # Pending instructor approvals
    pending_instructors = instructors.filter(is_approved=False)
    
    context = {
        'students': students,
        'instructors': instructors,
        'admins': admins,
        'exams': exams,
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_exams': total_exams,
        'total_submissions': total_submissions,
        'recent_submissions': recent_submissions,
        'pending_instructors': pending_instructors,
        'pending_count': pending_instructors.count(),
    }
    return render(request, 'admin_dashboard.html', context)


@_admin_required
def manage_user(request, user_id):
    """View to manage a specific user - approve/revoke instructors"""
    user = get_object_or_404(User, pk=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if user.role == User.ROLE_INSTRUCTOR and action == 'approve':
            user.is_approved = True
            user.save()
            # Send congratulatory email with login link
            try:
                login_link = request.build_absolute_uri('/')
                subject = '🎉 Congratulations! Your Instructor Account Has Been Approved'
                message = f"""Dear {user.full_name or user.username},

We are thrilled to inform you that your instructor account has been approved!

You can now log in to your dashboard and start creating exams for your students.

Login Link: {login_link}

Your Credentials:
- Username: {user.username}
- Email: {user.email}

If you have any questions, feel free to reach out to the admin team.

Best regards,
ExamSystem Team
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, f"Instructor {user.username} has been approved and notified via email.")
            except Exception as e:
                messages.warning(request, f"Instructor {user.username} has been approved but email could not be sent. Error: {str(e)}")
        elif user.role == User.ROLE_INSTRUCTOR and action == 'revoke':
            user.is_approved = False
            user.save()
            # Send revocation email notification
            try:
                subject = '⚠️ Access Revoked - Your Instructor Account'
                message = f"""Dear {user.full_name or user.username},

We regret to inform you that your instructor access has been revoked by the administrator.

If you believe this was a mistake or would like to discuss this further, please contact the admin team.

Best regards,
ExamSystem Team
"""
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.warning(request, f"Approval revoked for {user.username} and they have been notified via email.")
            except Exception as e:
                messages.warning(request, f"Approval revoked for {user.username} but email could not be sent. Error: {str(e)}")
        elif action == 'delete':
            username = user.username
            if user == request.user:
                messages.error(request, "You cannot delete yourself.")
            else:
                user.delete()
                messages.success(request, f"User {username} has been deleted.")
        return redirect('exams:admin_dashboard')
    
    return redirect('exams:admin_dashboard')

