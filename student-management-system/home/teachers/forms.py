from django import forms
from .models import Teacher

class TeacherForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password", required=True)

    class Meta:
        model = Teacher
        fields = [
            'teacher_id', 'first_name', 'last_name', 'gender', 'date_of_birth',
            'mobile', 'joining_date', 'qualification', 'username', 'email',
            'address', 'city', 'state', 'zip_code', 'country', 'teacher_image'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data