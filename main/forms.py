import datetime

from django import forms


class DatetimePicker(forms.Form):
    ts = datetime.datetime.now()

    from_time = forms.TimeField(
        label='От',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}, format='%H:%M'),
    )

    from_date = forms.DateField(
        label='От',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    to_time = forms.TimeField(
        label='До',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}, format='%H:%M'),
    )

    to_date = forms.DateField(
        label='До',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    name = forms.ChoiceField(
        label='Группа',
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.choices = kwargs['choices']
        del kwargs['choices']

        super().__init__(*args, **kwargs)

        self.fields['name'].choices = self.choices
