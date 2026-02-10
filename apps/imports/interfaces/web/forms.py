from django import forms


class ImportStartForm(forms.Form):
    csv_file = forms.FileField(required=True, label="CSV file")
    # Django 5.1+ uses allow_multiple_selected instead of widget attrs for multiple files
    images = forms.FileField(
        required=False,
        label="Images",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )
