from django import forms


class ImportStartForm(forms.Form):
    csv_file = forms.FileField(required=True, label="CSV file")
    images = forms.FileField(
        required=False,
        label="Images",
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
    )
