from django.contrib import admin
from .models import Exam, Question, Submission, Answer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['question_type', 'text', 'marks', 'correct_answer', 'order']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'answer_text', 'is_correct']
    fields = ['question', 'answer_text', 'is_correct', 'instructor_marks', 'instructor_feedback']


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'subject', 'code', 'status', 'total_questions', 'total_submissions', 'is_published', 'created_at']
    list_filter = ['is_published', 'instructor']
    search_fields = ['title', 'code', 'subject']
    inlines = [QuestionInline]
    readonly_fields = ['code']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question_type', 'text', 'marks', 'order']
    list_filter = ['question_type', 'exam']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam', 'score_percentage', 'grade_letter', 'is_submitted', 'submitted_at']
    list_filter = ['is_submitted', 'exam']
    readonly_fields = ['score', 'score_percentage']
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['submission', 'question', 'answer_text', 'is_correct', 'instructor_marks']
    list_filter = ['is_correct', 'question__question_type']
