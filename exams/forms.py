from django import forms
from django.core.exceptions import ValidationError
from .models import Exam, Question, Answer
from django.utils.safestring import mark_safe
import json

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'subject', 'instructions', 'duration_minutes', 'pass_mark', 'start_time', 'end_time', 'shuffle_questions']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 300}),
            'pass_mark': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'shuffle_questions': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_type', 'text', 'marks', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        widgets = {
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_answer': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UploadQuestionsForm(forms.Form):
    upload_file = forms.FileField(
        label='JSON/CSV Questions File',
        help_text='Upload JSON file with questions data',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    exam = forms.ModelChoiceField(queryset=Exam.objects.none())

    def __init__(self, *args, **kwargs):
        instructor = kwargs.pop('instructor', None)
        super().__init__(*args, **kwargs)
        if instructor:
            self.fields['exam'].queryset = Exam.objects.filter(instructor=instructor)

class JoinExamForm(forms.Form):
    exam_code = forms.CharField(
        max_length=10,
        label='Exam Code',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter 6-character exam code'}),
    )

    def clean_exam_code(self):
        code = self.cleaned_data['exam_code'].upper()
        from .models import Exam
        try:
            exam = Exam.objects.get(code__iexact=code, is_published=True)
        except Exam.DoesNotExist:
            raise ValidationError("Invalid or unpublished exam code.")
        return exam

class EssayGradeForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['instructor_marks', 'instructor_feedback']
        widgets = {
            'instructor_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'instructor_feedback': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

