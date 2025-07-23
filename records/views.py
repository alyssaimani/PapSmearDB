from django.shortcuts import render

from django.contrib.admin.views.decorators import staff_member_required

from django.shortcuts import render, redirect, get_object_or_404
from .models import UploadedFile, PatientData as PatientDataModel, CroppedImage
from django.http import HttpResponse
from django.urls import reverse 
from django.contrib import messages


def print_item_view(request, item_id):
    item = get_object_or_404(UploadedFile, id=item_id)
    prediction_results = CroppedImage.objects.filter(rawImage_id=item.id)

    data_to_print = UploadedFile.objects.get(id=item.id)

    return render(request, "inference_print.html", {"data_to_print":data_to_print, "prediction_results": prediction_results})

def delete_uploaded_view(request, item_id):
	item = get_object_or_404(UploadedFile, id=item_id)

	file_to_delete = UploadedFile.objects.filter(id=item.id)
                
	context = {'file_to_delete': file_to_delete}

	action = request.POST.get('action')

	if action == 'verify':
		selected_file = request.POST.get('idPrint')
		file_to_delete = UploadedFile.objects.filter(id=selected_file)

		entered_password = request.POST.get('password')
		user = request.user
		if user.check_password(entered_password):
			file = get_object_or_404(UploadedFile, id=selected_file)
			file.delete()
			messages.success(request, 'Data Berhasil dihapus')
			return redirect('../admin/hibahs/uploadedfile/')
		else:
			messages.error(request, 'Password salah')
			return render(request, "delete_image.html", {'password_error': True, 'file_to_delete': file_to_delete})

	return render(request, "delete_image.html",  context)

def show_prediction_view(request, item_id):
	predicted_images = CroppedImage.objects.filter(rawImage_id=item_id)

	return render(request, "inference_output.html", {'predicted_images':predicted_images})


def delete_prediction_view(request, item_id):
	item = get_object_or_404(CroppedImage, id=item_id)

	file_to_delete = CroppedImage.objects.filter(id=item.id)
                
	context = {'file_to_delete': file_to_delete}

	action = request.POST.get('action')

	if action == 'verify':
		selected_file = request.POST.get('idPrint')
		file_to_delete = CroppedImage.objects.filter(id=selected_file)

		entered_password = request.POST.get('password')
		user = request.user
		if user.check_password(entered_password):
			file = get_object_or_404(CroppedImage, id=selected_file)
			file.delete()
			messages.success(request, 'Data Berhasil dihapus')
			return redirect('../admin/hibahs/uploadedfile/')
		else:
			messages.error(request, 'Password salah')
			return render(request, "delete_prediction.html", {'password_error': True, 'file_to_delete': file_to_delete})

	return render(request, "delete_prediction.html",  context)