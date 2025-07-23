from django import forms
from .models import UploadedFile, PatientData
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PatientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.patientNationalID} - {obj.patientName}'

def validate_file_type(value):
    if not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise ValidationError(_('File type is not supported. Only PNG and JPEG are allowed.'))

class UploadFileForm(forms.ModelForm):
    patientName = PatientChoiceField(
        queryset= PatientData.objects.all(),
        empty_label='Pilih Nama Pasien',  # Remove the empty label (optional)
        to_field_name='id'
    )
    
    image = MultipleFileField()
    annotation = MultipleFileField()

    class Meta:
        model = UploadedFile
        fields = ['image', 'annotation', 'patientName', 'imageDate']

    imageDate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Tanggal Diambil',
    )

    document = forms.FileField(validators=[validate_file_type])    



class PatientData(forms.ModelForm):
    class Meta:
        model = PatientData

        widgets = {
            'patientGender': forms.RadioSelect(),
        }

        fields = [
            "patientNationalID",
            "patientName",
            "patientGender",
            "patientBirthDate"
        ]