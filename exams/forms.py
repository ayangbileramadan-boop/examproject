from django import forms
from .models import Exam, Question, Answer


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'subject', 'instructions', 'duration_minutes',
                  'pass_mark', 'start_time', 'end_time', 'shuffle_questions', 'is_published']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_type', 'text', 'marks', 'order',
                  'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }


class AnswerForm(forms.Form):
    """Dynamic form built per-question during exam taking."""
    def __init__(self, *args, question=None, **kwargs):
        super().__init__(*args, **kwargs)
        if question:
            self.question = question
            if question.question_type == 'mcq':
                choices = [('', '— Select an answer —')]
                for opt, label in [('A', question.option_a), ('B', question.option_b),
                                   ('C', question.option_c), ('D', question.option_d)]:
                    if label:
                        choices.append((opt, f"{opt}. {label}"))
                self.fields['answer'] = forms.ChoiceField(
                    choices=choices, required=False,
                    widget=forms.RadioSelect
                )
            elif question.question_type == 'true_false':
                self.fields['answer'] = forms.ChoiceField(
                    choices=[('TRUE', 'True'), ('FALSE', 'False')],
                    required=False, widget=forms.RadioSelect
                )
            else:
                self.fields['answer'] = forms.CharField(
                    required=False,
                    widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Your answer...'})
                )


class EssayGradeForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['instructor_marks', 'instructor_feedback']
        widgets = {
            'instructor_feedback': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_instructor_marks(self):
        marks = self.cleaned_data.get('instructor_marks')
        if marks is not None and marks < 0:
            raise forms.ValidationError("Marks cannot be negative.")
        return marks


class JoinExamForm(forms.Form):
    code = forms.CharField(
        max_length=10,
        label='Exam Code',
        widget=forms.TextInput(attrs={'placeholder': 'ABC123', 'autocomplete': 'off'})
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        from .models import Exam
        try:
            exam = Exam.objects.get(code=code, is_published=True)
        except Exam.DoesNotExist:
            raise forms.ValidationError("No active exam found with this code.")
        self.exam = exam
        return code
