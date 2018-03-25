
from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required


app_name = 'web_med'

urlpatterns = [

    # /web_med/
    url(r'^$', views.index, name='index'),

    ############ Authentication System ############
    url(r'^login/$', views.login_view, name = 'login'),
    url(r'^register/$', views.register_view, name = 'register'),
    url(r'^logout/$', views.logout_view, name = 'logout'),
    url(r'^profile/$', views.view_profile, name='view_profile'),
    url(r'^profile/(?P<pk>[0-9]+)/$', views.view_profile, name='view_profile_with_pk'),
    url(r'^profile/edit/$', views.edit_profile, name='edit_profile'),
    
    ### Patients

    # /web_med/patients/
    # /web_med/patients/add/
    # /web_med/patients/pk/slug/
    # /web_med/patients/pk/slug/update/
    # /web_med/patients/pk/slug/delete/

    ############ Patient ############
    url(r'^patients/$', views.patients_list, name='patients'),
    url(r'^patients/add/$', views.patientadd, name='patient-add'),
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)$', views.DetailView.as_view(), name='patient_detail'),
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/update/$', views.patientupdate, name='patient-update'),    
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/delete/$', views.patientdelete, name='patient-delete'),

    ############ Photo ############
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/progress-bar-upload/$', views.ProgressBarUploadView.as_view(), name='progress_bar_upload'),
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/drag-and-drop-upload/$', views.DragAndDropUploadView.as_view(), name='drag_and_drop_upload'),
   
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/clear/$', views.clear_files, name='clear_files'),

    ############ Nii & VTK ############
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/drag-and-drop-upload-nii/$', views.DragAndDropUploadViewNii.as_view(), name='drag_and_drop_upload_nii'),
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/drag-and-drop-upload-vtk/$', views.DragAndDropUploadViewVTK.as_view(), name='drag_and_drop_upload_vtk'),

    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/clear-nii/$', views.clear_files_nii, name='clear_files_nii'),
    url(r'^patients/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/clear-vtk/$', views.clear_files_vtk, name='clear_files_vtk'),

    ##### Cornerstone Dicom Processing #####
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/$', views.dicomprocess, name='dicom-process'),
    
    ## Nii Visualizer 
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/Nii$', views.niiprocess, name='nii-process'),
    
    # VTK Visualizer 
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/VTK$', views.vtkprocess, name='vtk-process'),
 
    ##### Algorithms #####
    
        ##Filtering
            ##Image Denoising:Linear
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/mean$', views.mean, name='mean'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/median$', views.median, name='median'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/BinomialBlur$', views.BinomialBlur, name='BinomialBlur'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/RecursiveGaussian$', views.RecursiveGaussian, name='RecursiveGaussian'),
            ##Image Denoising:Non-Linear
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/CurvatureAnisotropicDiffusion$', views.CurvatureAnisotropicDiffusion, name='CurvatureAnisotropicDiffusion'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/CurvatureFlow$', views.CurvatureFlow, name='CurvatureFlow'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/GradientAnisotropicDiffusion$', views.GradientAnisotropicDiffusion, name='GradientAnisotropicDiffusion'),
            ##Image Morphology        
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/BinaryDilate$', views.BinaryDilate, name='BinaryDilate'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/BinaryErode$', views.BinaryErode, name='BinaryErode'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/GrayScaleDilate$', views.GrayScaleDilate, name='GrayScaleDilate'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/GrayScaleErode$', views.GrayScaleErode, name='GrayScaleErode'),
            ##Edge Detection & Feature Extraction
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/CannyEdgeDetection$', views.CannyEdgeDetection, name='CannyEdgeDetection'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/SobelEdgeDetection$', views.SobelEdgeDetection, name='SobelEdgeDetection'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/LaplacianRecursive$', views.LaplacianRecursive, name='LaplacianRecursive'),
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/GradientMagnitude$', views.GradientMagnitude, name='GradientMagnitude'),
            ##Image Intensity Transformations
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/Sigmoid$', views.Sigmoid, name='Sigmoid'),        
        ##Segmentation
            ##Thresholding 
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/BinaryThreshold$', views.BinaryThreshold, name='BinaryThreshold'),        
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/OtsuThreshold$', views.OtsuThreshold, name='OtsuThreshold'),        
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/Threshold$', views.Threshold, name='Threshold'),        
            ##Region Growing
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/ConfidenceConnected$', views.ConfidenceConnected, name='ConfidenceConnected'),        
            ##Watershed
            url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/(?P<name>[\w\W.]+)/Watershed$', views.Watershed, name='Watershed'),        


    ##### SliceDrop #####
    url(r'^patients/process/SliceDrop/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)$', views.SliceDrop, name='SliceDrop'),

    ##### AMI Volume Rendering #####
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/l15$', views.l15process, name='l15-process'),

    ##### Volume Segmentation #####
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/VolumeSegmentation$', views.VolumeSegmentation, name='VolumeSegmentation'),

    ##### Volume Segmentation View #####
    url(r'^patients/process/(?P<pk>[0-9]+)/(?P<slug>[\w-]+)/VolumeSegmentationView$', views.vtksegview, name='vtksegview'),   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
