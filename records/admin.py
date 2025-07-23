from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import UploadedFile, PatientData, CroppedImage
from datetime import datetime
from django.core.validators import RegexValidator
from django.views.generic.detail import  DetailView
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, path

from .inference import get_cropped_images, batch_predict, DinoModelWrapper, get_preprocess_transform, draw_bounding_box_pil
from skimage.segmentation import mark_boundaries
import cv2
import os
import torch

# Register your models here.
class PatientUpload(admin.StackedInline):
    model = UploadedFile

class PatientDataForm(forms.ModelForm):
    current_date = datetime.now().date()

    class Meta:
        model = PatientData
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patientID'].disabled = True

        # If the instance is not provided (i.e., when creating a new patient), generate no_pasien
        if not self.instance.pk:
            latest_patient = PatientData.objects.order_by('-patientID').first()
            if latest_patient:
                numeric_part = int(latest_patient.patientID[3:])
                next_numeric_part = numeric_part + 1
                self.initial['patientID'] = f'PAS{next_numeric_part:03}'
            else:
                self.initial['patientID'] = 'PAS001'

    patientName = forms.CharField(
        validators=[RegexValidator(regex=r'^[a-zA-Z\s]*$', message='Enter only alphabetic characters.')],
        label='Nama Pasien'
    )

    patientBirthDate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'max': str(current_date)}),
        label='Tanggal Lahir Pasien',
    )

class PatientDetail(admin.ModelAdmin):
   form = PatientDataForm
   list_display = ('patientID', 'patientName', 'patientBirthDate', 'patientGender') 

admin.site.register(PatientData, PatientDetail)

class PatientDetailView(DetailView):
    template_name = "patient_with_image.html"
    model = PatientData

    def get_context_data(self, **kwargs):
        
        patient = self.get_object()  # Retrieves the PatientDataModel instance for the patient

        # Retrieve all uploaded files for this patient
        uploaded_files = UploadedFile.objects.filter(patientName=patient)

        # Check if each uploaded file has a corresponding CroppedImage
        predicted_files = [
            uploaded_file for uploaded_file in uploaded_files 
            if CroppedImage.objects.filter(rawImage=uploaded_file).exists()
        ]
    

        # Add the necessary context data
        context = super().get_context_data(**kwargs)
        context.update({
            **admin.site.each_context(self.request),
            "opts": self.model._meta,
            "predicted_files": predicted_files            
        })
        
        return context
        # return {
        #     **super().get_context_data(**kwargs),
        #     **admin.site.each_context(self.request),
        #     "opts": self.model._meta,
        # }
    
    def post(self, request, *args, **kwargs):
       

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'inference':
                selected_files = request.POST.getlist('selected_files')
                if not selected_files:

                    return HttpResponse(f'<script>alert("Silahkan Pilih Salah satu image yang mau didiagnosa"); window.history.back();</script>')

                else:
                    MODEL_PATH = "media/best_model_multitask_part_4.pt"
                    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                    model = DinoModelWrapper(device=device)
                    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
                    model.to(device)

                    for param in model.parameters():
                        param.requires_grad = False
                    model.eval()


                    files = UploadedFile.objects.filter(id__in=selected_files)
                    
                    label_task_1 = {
                        0: 'HSIL',
                        1: 'Kelompokan Endoserviks',
                        2: 'LSIL',
                        3: 'Limfosit',
                        4: 'Netrofil',
                        5: 'SCC',
                        6: 'Sel Intermediate',
                        7: 'Sel Parabasal',
                        8: 'Sel Superficial'
                    }
                    
                    label_task_2 = {
                        0: 'Benign',
                        1: 'Inflammation',
                        2: 'Malignant',
                        3: 'SIL'
                    }
                    for file in files: 
                        path_annotation = file.annotation.path
                        path_image = file.image.path
                        
                        annotated_image = draw_bounding_box_pil(path_image, path_annotation)
                        filename = f"annotated_{file.id}.jpg"
                        save_path = os.path.join('media/static', filename)
                        annotated_image.save(save_path)

                        file_object = UploadedFile.objects.get(id=file.id)
                        file_object.annotated_image = filename
                        file_object.save()
                        
                        # crop raw image
                        cropped_images = get_cropped_images(path_image, path_annotation)
                        
                        # predict cropped images
                        _, pred_labels = batch_predict(model, cropped_images, transform=get_preprocess_transform())
                        

                        # save cropped images into storage
                        for idx,image in enumerate(cropped_images):
                            filename = f"cropped_{file.id}_{idx}.jpg"
                            save_path = os.path.join('media/static', filename)
                            image.save(save_path)
                        
                            # save to database
                            CroppedImage.objects.create(rawImage_id=file.id, image=filename, predictionResult=label_task_1[pred_labels[idx]], predictionDate=datetime.now())
                    
                    return redirect(request.get_full_path())

        return render(request, self.template_name)

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, list):
            # Allow processing multiple files
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class PatientChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.patientID} - {obj.patientName}'


def validate_image_type(value):
    if not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise ValidationError(_('Silahkan upload gambar dengan tipe file PNG, JPEG atau JPG'))


def validate_label_type(value):
    if not value.name.lower().endswith(('.geojson')):
        raise ValidationError(_('Silahkan upload label dengan tipe file GEOJSON'))

class UploadFileForm(forms.Form):
    patientName = PatientChoiceField(
        queryset= PatientData.objects.all(),
        empty_label='Pilih Nama Pasien',  # Remove the empty label (optional)
        to_field_name='id',
        label="Nama Pasien"
    )
    
    image = MultipleFileField(validators=[validate_image_type])
    
    annotation = MultipleFileField(validators=[validate_label_type])

    current_date = datetime.now().date()

    imageDate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'max': str(current_date)}),
        label='Tanggal Diambil',
    )

    class Meta:
        model = UploadedFile
        fields = ['image', 'annotation', 'patientName', 'imageDate']

class UploadedFile_list(admin.ModelAdmin):
    list_display = ('get_patient_name', 'detail')
    list_display_links = None
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return False 
   
    def get_urls(self):
        urls = super().get_urls()

        custom_urls = [
            # Define your custom URL patterns here
            path('upload-image/', self.upload_image),
            path('<pk>/detail', self.admin_site.admin_view(PatientDetailView.as_view()), name='patient_detail'),
        ]

        return custom_urls + urls

    def upload_image(self, request):
        files = UploadedFile.objects.all()
        # Create a dictionary to store unique entries based on a specific field (e.g., 'field_to_check')
        unique_entries = {}
        # Iterate through the queryset and store unique entries in the dictionary
        for file in files:
            key = file.patientName_id  # Use the field you want to check for uniqueness
            if key not in unique_entries:
                unique_entries[key] = file

        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                selected_patient = form.cleaned_data['patientName']
                selected_patient_id = selected_patient.id
                selected_tanggaldiambil = form.cleaned_data['imageDate']
                images = request.FILES.getlist('image')
                annotations = request.FILES.getlist('annotation')
                for image_file, annotation_file in zip(images, annotations):                  
                    UploadedFile.objects.create(
                        image=image_file, annotation=annotation_file, patientName_id=selected_patient_id, imageDate=selected_tanggaldiambil
                    )
                return redirect('../')
        else:
            form = UploadFileForm()

        return render(request, "upload_and_display.html", {'form': form, 'files': unique_entries.values()})
        
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Create a dictionary to store the latest record for each unique patient
        latest_records = {}
        
        for file in queryset:
            patient_id = file.patientName.id
            if patient_id not in latest_records:
                latest_records[patient_id] = file
            else:
                # Check if this record has a more recent uploaded_at date
                if file.uploaded_at > latest_records[patient_id].uploaded_at:
                    latest_records[patient_id] = file
        
        # Convert the dictionary values back to a queryset
        return UploadedFile.objects.filter(pk__in=[record.id for record in latest_records.values()])

    def get_patient_name(self, obj):
   		return obj.patientName.patientName  # Replace 'name' with the actual field name in your Patient model
    
    get_patient_name.short_description = 'Patient Name'  # This sets the column header text in the admin list view



    def detail(self, obj: PatientData) -> str:
        foreign_key_value = obj.patientName_id
        url = reverse("admin:patient_detail", args=[foreign_key_value])
        return format_html(f'<a href="{url}">📝</a>')

admin.site.register(UploadedFile, UploadedFile_list)