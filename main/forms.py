import datetime

from django import forms


class DatetimePicker(forms.Form):
    ts = datetime.datetime.now()

    from_time = forms.TimeField(
        label='От',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}, format='%H:%M'),
    )

    from_date = forms.DateField(
        label='От',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )

    to_time = forms.TimeField(
        label='До',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control form-control-sm'}, format='%H:%M'),
    )

    to_date = forms.DateField(
        label='До',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )

    tag = forms.ChoiceField(
        label='Группа',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=True
    )

    aggregate_window = forms.ChoiceField(
        label='Интервал',
        choices=[('3m', '3 минуты'), ('30m', '30 минут'), ('1d', '1 день')],
        widget=forms.Select(
            attrs={'class': 'form-select form-select-sm'},
        ),
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.choices = kwargs['choices']
        del kwargs['choices']

        super().__init__(*args, **kwargs)

        self.fields['tag'].choices = self.choices
