from django.db import models

# Create your models here.
class RecordData(models.Model):

	recordNum = models.CharField('Nomor Rekam Medis', max_length = 225, default='UNKNOWN')
	institutionName = models.CharField('Institusi', max_length = 225)
	recordDate = models.DateField('Tanggal Pengambilan', auto_now_add=False, auto_now=False)
	project = models.FileField('Qupath Project', upload_to='uploads/')
	recordID = models.CharField('Record ID', max_length = 16, unique=True, default=None)

	def __str__(self):
		return self.recordNum

	class Meta:
		verbose_name_plural = 'Medical Records'  # Change the display name here

class UploadedFile(models.Model):
    recordNum = models.ForeignKey(RecordData, on_delete=models.CASCADE)
    image = models.FileField(upload_to='uploads/')
    annotation = models.FileField(upload_to='uploads/')
    annotated_image = models.FileField(upload_to='static/')
    imageDate = models.DateField('Tanggal Image diambil (mm/dd/yyyy)', auto_now_add=False, auto_now=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.image}"
    
    def record_data(self):
        return self.recordNum
	
class CroppedImage(models.Model):
	rawImage = models.ForeignKey(UploadedFile, on_delete=models.CASCADE)
	image = models.FileField(upload_to='static/')
	originalLabel = models.TextField(null=True, blank=True)
	predictionResult = models.TextField(null=True, blank=True)
	predictionDate = models.DateField('Tanggal Image diprediksi (mm/dd/yyyy)', auto_now_add=False, auto_now=False)
	uploaded_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.image}"