from django.db import models

# Create your models here.
class PatientData(models.Model):
	GENDER_CHOICES = ( 
		('L', 'Laki-laki'), 
		('P', 'Perempuan'), 
	)

	patientName = models.CharField('Nama Pasien', max_length = 225)
	patientBirthDate = models.DateField('Tanggal Lahir', auto_now_add=False, auto_now=False)
	patientGender = models.CharField('Jenis Kelamin', max_length = 1, choices=GENDER_CHOICES, default='L')
	patientID = models.CharField('No Pasien', max_length = 16, unique=True, default=None)

	def __str__(self):
		return self.patientName

	class Meta:
		verbose_name_plural = 'Patient Data'  # Change the display name here

class UploadedFile(models.Model):
    patientName = models.ForeignKey(PatientData, on_delete=models.CASCADE)
    image = models.FileField(upload_to='uploads/')
    annotation = models.FileField(upload_to='uploads/')
    annotated_image = models.FileField(upload_to='static/')
    imageDate = models.DateField('Tanggal Image diambil (mm/dd/yyyy)', auto_now_add=False, auto_now=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.image}"
    
    def patient_data(self):
        return self.patientName
	
class CroppedImage(models.Model):
	rawImage = models.ForeignKey(UploadedFile, on_delete=models.CASCADE)
	image = models.FileField(upload_to='static/')
	predictionResult = models.TextField(null=True, blank=True)
	predictionDate = models.DateField('Tanggal Image diprediksi (mm/dd/yyyy)', auto_now_add=False, auto_now=False)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.image}"