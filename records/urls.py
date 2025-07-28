from django.urls import path
from .admin import UploadedFile_list  # Import your custom admin class
from . import views
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from .views import print_item_view, delete_uploaded_view, show_prediction_view, delete_prediction_view

urlpatterns = [
    
    # path('admin/', admin.site.urls),
    path('print/<int:item_id>', print_item_view, name='print_item_view'), 
    path('delete_uploaded/<int:item_id>', delete_uploaded_view, name='delete_uploaded_view'), 
    path('item/<int:item_id>/', show_prediction_view, name='show_prediction_view'),
    path('delete_prediction/<int:item_id>', delete_prediction_view, name='delete_prediction_view'), 
    # path('uploadedfile', print_item_view, name='print_item_view'),
    # *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
   ]