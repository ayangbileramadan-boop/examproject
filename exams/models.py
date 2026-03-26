from django.db import models
from django.utils import timezone
from django.conf import settings
import random
import string


def generate_exam_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Exam(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_UPCOMING = 'upcoming'
    STATUS_LIVE = 'live'
    STATUS_CLOSED = 'closed'

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='created_exams', limit_choices_to={'role': 'instructor'}
    )
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    code = models.CharField(max_length=10, unique=True, default=generate_exam_code)
    duration_minutes = models.PositiveIntegerField(default=60)
    pass_mark = models.PositiveIntegerField(default=50, help_text="Pass mark as percentage")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    shuffle_questions = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def status(self):
        now = timezone.now()
        if not self.is_published:
            return self.STATUS_DRAFT
        if self.start_time and now < self.start_time:
            return self.STATUS_UPCOMING
        if self.end_time and now > self.end_time:
            return self.STATUS_CLOSED
        return self.STATUS_LIVE

    @property
    def total_questions(self):
        return self.questions.count()

    @property
    def total_marks(self):
        return self.questions.aggregate(
            total=models.Sum('marks')
        )['total'] or 0

    @property
    def total_submissions(self):
        return self.submissions.filter(is_submitted=True).count()

    @property
    def average_score(self):
        from django.db.models import Avg
        result = self.submissions.filter(is_submitted=True).aggregate(avg=Avg('score_percentage'))
        return round(result['avg'] or 0, 1)


class Question(models.Model):
    TYPE_MCQ = 'mcq'
    TYPE_TRUE_FALSE = 'true_false'
    TYPE_ESSAY = 'essay'
    TYPE_SHORT = 'short'
    TYPE_CHOICES = [
        (TYPE_MCQ, 'Multiple Choice'),
        (TYPE_TRUE_FALSE, 'True / False'),
        (TYPE_ESSAY, 'Essay'),
        (TYPE_SHORT, 'Short Answer'),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_MCQ)
    text = models.TextField()
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    # For MCQ
    option_a = models.CharField(max_length=300, blank=True)
    option_b = models.CharField(max_length=300, blank=True)
    option_c = models.CharField(max_length=300, blank=True)
    option_d = models.CharField(max_length=300, blank=True)
    correct_answer = models.CharField(max_length=300, blank=True,
        help_text="For MCQ: A/B/C/D. For True/False: True/False. For short: exact answer.")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"

    @property
    def is_auto_gradable(self):
        return self.question_type in [self.TYPE_MCQ, self.TYPE_TRUE_FALSE, self.TYPE_SHORT]


class Submission(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='submissions', limit_choices_to={'role': 'student'}
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='submissions')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    score_percentage = models.FloatField(default=0)
    time_taken_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'exam']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} — {self.exam.title}"

    @property
    def passed(self):
        return self.score_percentage >= self.exam.pass_mark

    @property
    def grade_letter(self):
        p = self.score_percentage
        if p >= 70: return 'A'
        if p >= 60: return 'B'
        if p >= 50: return 'C'
        if p >= 40: return 'D'
        return 'F'

    def calculate_score(self):
        """Auto-grade all auto-gradable answers and save score."""
        total_marks = 0
        earned_marks = 0
        for answer in self.answers.all():
            q = answer.question
            total_marks += q.marks
            if q.is_auto_gradable:
                given = (answer.answer_text or '').strip().upper()
                correct = (q.correct_answer or '').strip().upper()
                if given == correct:
                    earned_marks += q.marks
                    answer.is_correct = True
                else:
                    answer.is_correct = False
                answer.save()
        self.score = earned_marks
        self.score_percentage = round((earned_marks / total_marks * 100), 1) if total_marks else 0
        self.save()


class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    instructor_marks = models.FloatField(null=True, blank=True, help_text="Manual marks for essays")
    instructor_feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ['submission', 'question']

    def __str__(self):
        return f"{self.submission.student.username} — Q{self.question.order}"
