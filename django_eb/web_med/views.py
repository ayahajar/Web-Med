# -*- coding: utf-8 -*-

import __future__
#from __future__ import unicode_literals
import time
import os
import shutil
import dicom
import numpy
import mritopng
import itk
import vtk
import boto3
import botocore
from vtk.util import numpy_support
import json as simplejson
from django.views import generic
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.views import View
from django.contrib.auth.models import User
from .models import Patient, Photo, Photopng, UserProfile, Nii, VTK
from .forms import PatientForm, PhotoForm, NiiForm, VTKForm, UsersLoginForm, UsersRegisterForm, EditProfileForm
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

stl_name=""

def index(request):
    return render(request, 'web_med/mainpage.html')

############ Authentication System ############

def login_view(request, *args, **kwargs):
        form = UsersLoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username = username, password = password)
            login(request, user)
            return redirect("/web_med/profile/")
        
        return render(request, "web_med/form.html", {
            "form" : form,
            "title" : "Login",
        })

#@login_required(login_url='/web_med/login/')
def view_profile(request, pk=None):
    if pk:
        user = User.objects.get(pk=pk)
    else:
        user = request.user
    args = {'user': user}
    return render(request, 'web_med/profile.html', args)

#@login_required(login_url='/web_med/login/')
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            return redirect(reverse('web_med:view_profile'))
    else:
        form = EditProfileForm(instance=request.user)
        args = {'form': form}
        return render(request, 'web_med/edit_profile.html', args)

def register_view(request):
    form = UsersRegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        password = form.cleaned_data.get("password")	
        user.set_password(password)
        user.save()
        new_user = authenticate(username=user.username, password=password)
        login(request, new_user)
        return redirect("/web_med/login")
    return render(request, "web_med/form.html", {
        "title" : "Register",
        "form" : form,
    })

def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/web_med/login")

#@login_required(login_url='/web_med/login/')
def profile_for_users(request):
    profile = UserProfile.objects.flter(user=request.user)
    return render (request, 'web_med/patients.html', {'profile' : profile})


############ Patient ############
#@login_required(login_url='/web_med/login/')
def patients_list(request):
    patients = Patient.objects.filter(doctor=request.user.id)
    return render(request, 'web_med/patients.html', {'patients':patients})    
#@login_required(login_url='/web_med/login/')
def save_patient_form(request, form, template_name):
    data = dict()
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            data['form_is_valid'] = True
            patients = Patient.objects.filter(doctor=request.user.id)
            data['html_patient_list'] = render_to_string('web_med/includes/partial_patients_list.html', {
                'patients': patients
            })
        else:
            data['form_is_valid'] = False
    context = {'form': form}
    data['html_form'] = render_to_string(template_name, context, request=request)
    return JsonResponse(data)
#@login_required(login_url='/web_med/login/')
def patientadd(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        obj = form.save(commit=False)
        obj.doctor = request.user.id
        obj.save()
    else:
        form = PatientForm()   
    return save_patient_form(request, form, 'web_med/includes/partial_patient_create.html')
#@login_required(login_url='/web_med/login/')
def patientupdate(request, *args, **kwargs):
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
    else:
        form = PatientForm(instance=patient)
    return save_patient_form(request, form, 'web_med/includes/partial_patient_update.html')    
#@login_required(login_url='/web_med/login/')
def patientdelete(request, *args, **kwargs):
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    patient = get_object_or_404(Patient, pk=patient_id)
    data = dict()
    if request.method == 'POST':
        patient.delete()
        data['form_is_valid'] = True
        patients = Patient.objects.all().all().filter(doctor=request.user.id)
        data['html_patient_list'] = render_to_string('web_med/includes/partial_patients_list.html', {
            'patients': patients
        })
    else:
        context = {'patient': patient}
        data['html_form'] = render_to_string('web_med/includes/partial_patient_delete.html',
            context,
            request=request,
        )
    return JsonResponse(data)

class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Patient
    template_name = 'web_med/detail.html'
    #login_url = '/web_med/login'
    #redirect_field_name = 'web_med/login'


############ Photo ############

class ProgressBarUploadView(View):
    
    def get(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('pk', None)
        patient_slug = self.kwargs.get('slug', None)        
        pat = get_object_or_404(Patient, pk=patient_id)
        photos_list = Photo.objects.all().filter(patient=pat)
        return render(self.request, 'web_med/progress_bar_upload/index.html', {'patient': pat, 'pi': patient_id, 'ps': patient_slug, 'photos': photos_list})

    def post(self, request, *args, **kwargs):        
        form = PhotoForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            # Photo Object
            photo = Photo(file=request.FILES['file'])
            patient_id = self.kwargs.get('pk', None)
            photo.patient = get_object_or_404(Patient, pk=patient_id)
            photo.save()
            photo_name = photo.get_file_name()
            photo_name2 = photo.get_file_name_withoutExtension()
            photo_path = 'media/dicom/%s/%s' % (patient_id, photo_name)
            photo_path21 = 'media/png/%s' % (patient_id)
            photo_path22 = 'media/png/%s/%s.png' % (patient_id, photo_name2)
                
            # Converting         
            if not os.path.exists(photo_path21):
                os.makedirs(photo_path21)

            if not os.path.exists(photo_path22):
                mritopng.convert_file(photo_path, photo_path22)
            
	    # Photopng Object
            photopng = Photopng()
            photopng.patient = get_object_or_404(Patient, pk=patient_id)
            photopng.image = photo_path22
            photopng.save()
            
            data = {'is_valid': True, 'name': photo_name, 'url': photo.file.url}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)

class DragAndDropUploadView(View):
    def get(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('pk', None)
        patient_slug = self.kwargs.get('slug', None)        
        pat = get_object_or_404(Patient, pk=patient_id)
        photos_list = Photo.objects.all().filter(patient=pat)
        return render(self.request, 'web_med/drag_and_drop_upload/index.html', {'patient': pat, 'pi': patient_id, 'ps': patient_slug, 'photos': photos_list})

    def post(self, request, *args, **kwargs):
        form = PhotoForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            # Photo Object
            photo = Photo(file=request.FILES['file'])
            patient_id = self.kwargs.get('pk', None)
            photo.patient = get_object_or_404(Patient, pk=patient_id)
            photo.save()
            # Converting            
            photo_name = photo.get_file_name()
            photo_name2 = photo.get_file_name_withoutExtension()
            photo_path = 'media/dicom/%s/%s' % (patient_id, photo_name)
            photo_path21 = 'media/png/%s' % (patient_id)
            if not os.path.exists(photo_path21):
                os.makedirs(photo_path21)
            photo_path22 = 'media/png/%s/%s.png' % (patient_id, photo_name2)
            if not os.path.exists(photo_path22):
                mritopng.convert_file(photo_path, photo_path22)
            # Photopng Object
            photopng = Photopng()
            photopng.patient = get_object_or_404(Patient, pk=patient_id)
            photopng.image = photo_path22
            photopng.save()

            data = {'is_valid': True, 'name': photo_name, 'url': photo.file.url}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)

class DragAndDropUploadViewNii(View):
    def get(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('pk', None)
        patient_slug = self.kwargs.get('slug', None)        
        pat = get_object_or_404(Patient, pk=patient_id)
        nii_list = Nii.objects.all().filter(patient=pat)
        return render(self.request, 'web_med/drag_and_drop_upload/index_nii.html', {'patient': pat, 'pi': patient_id, 'ps': patient_slug, 'niis': nii_list})

    def post(self, request, *args, **kwargs):
        form = NiiForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            # Nii Object
            nii = Nii(file=request.FILES['file'])
            patient_id = self.kwargs.get('pk', None)
            nii.patient = get_object_or_404(Patient, pk=patient_id)
            nii.save()
            
            nii_name = nii.get_file_name()
            
            data = {'is_valid': True, 'name': nii_name, 'url': nii.file.url}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)

class DragAndDropUploadViewVTK(View):
    def get(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('pk', None)
        patient_slug = self.kwargs.get('slug', None)        
        pat = get_object_or_404(Patient, pk=patient_id)
        vtk_list = VTK.objects.all().filter(patient=pat)
        return render(self.request, 'web_med/drag_and_drop_upload/index_vtk.html', {'patient': pat, 'pi': patient_id, 'ps': patient_slug, 'vtks': vtk_list})

    def post(self, request, *args, **kwargs):
        form = VTKForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            # VTK Object
            vtk = VTK(file=request.FILES['file'])
            patient_id = self.kwargs.get('pk', None)
            vtk.patient = get_object_or_404(Patient, pk=patient_id)
            vtk.save()
            
            vtk_name = vtk.get_file_name()
            
            data = {'is_valid': True, 'name': vtk_name, 'url': vtk.file.url}
        else:
            data = {'is_valid': False}
        return JsonResponse(data)


def clear_files(request, *args, **kwargs):

    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    pat = get_object_or_404(Patient, pk=patient_id)
    photos_list = Photo.objects.all().filter(patient=pat)
    for photo in photos_list:
        photo.file.delete()
        photo.delete()   

    dicom_path = 'media/dicom/%s/' % (patient_id)
    if os.path.exists(dicom_path):
        shutil.rmtree(dicom_path)
    
    png_path = 'media/png/%s/' % (patient_id)
    if os.path.exists(png_path):
        shutil.rmtree(png_path)
        photospng_list = Photopng.objects.all().filter(patient=pat)
        for photopng in photospng_list:
            photopng.image.delete()
            photopng.delete()
    return redirect(request.POST.get('next'))

def clear_files_nii(request, *args, **kwargs):

    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    pat = get_object_or_404(Patient, pk=patient_id)
    nii_list = Nii.objects.all().filter(patient=pat)
    for nii in nii_list:
        nii.file.delete()
        nii.delete()    
    nii_path = 'media/nii/%s/' % (patient_id)
    if os.path.exists(nii_path):
        shutil.rmtree(nii_path)
        
    return redirect(request.POST.get('next'))

def clear_files_vtk(request, *args, **kwargs):

    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    pat = get_object_or_404(Patient, pk=patient_id)
    vtk_list = VTK.objects.all().filter(patient=pat)
    for vtk in vtk_list:
        vtk.file.delete()
        vtk.delete()    
    vtk_path = 'media/vtk/%s/' % (patient_id)
    if os.path.exists(vtk_path):
        shutil.rmtree(vtk_path)
        
    return redirect(request.POST.get('next'))


##### Cornerstone Dicom Processing #####

def dicomprocess(request, *args, **kwargs):
  
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    photo_name_clicked = kwargs.get('name', None)

    photo_png_path = 'media/png/%s/%s.png' % (patient_id, photo_name_clicked)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    template_name = 'web_med/processing.html'

    return render(request,template_name, {
        'photo_png_path':photo_png_path,
        'photo_dcm_path':photo_dcm_path,
        'pi': patient_id,
        'ps': patient_slug,
        'photo_name_clicked': photo_name_clicked,
    })


def niiprocess(request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    nii_name_clicked = kwargs.get('name', None)

    nii_path = 'media/nii/%s/%s.nii' % (patient_id, nii_name_clicked)
    
    template_name = 'web_med/niiprocessing.html'
  
    return render(request, template_name, {
        'nii_path':nii_path
    })    

def vtkprocess(request, *args, **kwargs):
   
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    vtk_name_clicked = kwargs.get('name', None)

    vtk_path = 'media/vtk/%s/%s.vtk' % (patient_id, vtk_name_clicked)
  
    template_name = 'web_med/vtk.html'  
    return render(request, template_name, {
        'vtk_path':vtk_path
    }) 

    
##### Algorithms #####

##Filtering

##Image Denoising:Linear
def mean(request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Mean Filtering Of An Image ###      
        #Apply mean filtering on an image.

        radius = request.POST.get("radius_mean","")
        radius = int(radius)

        photo_name_processed = photo_name_clicked + "_mean" + str(radius)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        meanFilter = itk.MeanImageFilter[ImageType, ImageType].New()
        meanFilter.SetInput(reader.GetOutput())
        meanFilter.SetRadius(radius)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(meanFilter.GetOutput())

        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)

def median (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Median Filtering Of An Image ###
        #Apply median filtering on an image.

        radius = request.POST.get("radius_median","")
        radius = int(radius)
        
        photo_name_processed = photo_name_clicked + "_median" + str(radius)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        medianFilter = itk.MedianImageFilter[ImageType, ImageType].New()
        medianFilter.SetInput(reader.GetOutput())
        medianFilter.SetRadius(radius)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(medianFilter.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)
    
def BinomialBlur (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Blurring An Image Using A Binomial Kernel ###
        #The BinomialBlurImageFilter computes a nearest neighbor average along each dimension. The process is repeated a number of times, as specified by the user. In principle, after a large number of iterations the result will approach the convolution with a Gaussian.

        numberOfRepetitions = request.POST.get("numberOfRepetitions_BinomialBlur","")
        numberOfRepetitions = int(numberOfRepetitions)

        photo_name_processed = photo_name_clicked + "_BinomialBlur" + str(numberOfRepetitions)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        reader = itk.ImageFileReader[InputImageType].New()
        reader.SetFileName(str(inputImage))

        binomialFilter = itk.BinomialBlurImageFilter.New(reader)
        binomialFilter.SetRepetitions(numberOfRepetitions)

        rescaler = itk.RescaleIntensityImageFilter[
            InputImageType,
            OutputImageType].New()
        rescaler.SetInput(binomialFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[OutputImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def RecursiveGaussian (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Computes the smoothing with Gaussian kernel ###
        #Computes the smoothing of an image by convolution with Gaussian kernels.

        sigma = request.POST.get("sigma_RecursiveGaussian","")
        sigma = float(sigma)

        photo_name_processed = photo_name_clicked + "_RecursiveGaussian" + str(sigma)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        smoothFilter = itk.SmoothingRecursiveGaussianImageFilter[
                ImageType,
                ImageType].New()
        smoothFilter.SetInput(reader.GetOutput())
        smoothFilter.SetSigma(sigma)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(smoothFilter.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

##Image Denoising:Non-Linear    
def CurvatureAnisotropicDiffusion (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Compute Curvature Anisotropic Diffusion ###
        #Perform anisotropic diffusion on an image.

        numberOfIterations = request.POST.get("numberOfIterations_CurvatureAnisotropicDiffusion","")
        numberOfIterations = int(numberOfIterations)
        timeStep = request.POST.get("timeStep_CurvatureAnisotropicDiffusion","")
        timeStep = float(timeStep)
        conductance = request.POST.get("conductance_CurvatureAnisotropicDiffusion","")
        conductance = float(conductance)

        photo_name_processed = photo_name_clicked + "_CurvatureAnisotropicDiffusion" + str(numberOfIterations) + str(timeStep) + str(conductance)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)
 
        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        ReaderType = itk.ImageFileReader[InputImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        FilterType = itk.CurvatureAnisotropicDiffusionImageFilter[
            InputImageType, InputImageType]
        curvatureAnisotropicDiffusionFilter = FilterType.New()

        curvatureAnisotropicDiffusionFilter.SetInput(reader.GetOutput())
        curvatureAnisotropicDiffusionFilter.SetNumberOfIterations(numberOfIterations)
        curvatureAnisotropicDiffusionFilter.SetTimeStep(timeStep)
        curvatureAnisotropicDiffusionFilter.SetConductanceParameter(conductance)

        RescaleFilterType = itk.RescaleIntensityImageFilter[
            InputImageType, OutputImageType]
        rescaler = RescaleFilterType.New()
        rescaler.SetInput(curvatureAnisotropicDiffusionFilter.GetOutput())

        outputPixelTypeMinimum = itk.NumericTraits[OutputPixelType].min()
        outputPixelTypeMaximum = itk.NumericTraits[OutputPixelType].max()

        rescaler.SetOutputMinimum(outputPixelTypeMinimum)
        rescaler.SetOutputMaximum(outputPixelTypeMaximum)

        WriterType = itk.ImageFileWriter[OutputImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def CurvatureFlow (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Compute Curvature Flow ###
        #Denoise an image using curvature driven flow.

        numberOfIterations = request.POST.get("numberOfIterations_CurvatureFlow","")
        numberOfIterations = int(numberOfIterations)
        timeStep = request.POST.get("timeStep_CurvatureFlow","")
        timeStep = float(timeStep)

        photo_name_processed = photo_name_clicked + "_CurvatureFlow" + str(numberOfIterations) + str(timeStep)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        ReaderType = itk.ImageFileReader[InputImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        FilterType = itk.CurvatureFlowImageFilter[
            InputImageType, InputImageType]
        curvatureFlowFilter = FilterType.New()

        curvatureFlowFilter.SetInput(reader.GetOutput())
        curvatureFlowFilter.SetNumberOfIterations(numberOfIterations)
        curvatureFlowFilter.SetTimeStep(timeStep)

        RescaleFilterType = itk.RescaleIntensityImageFilter[
            InputImageType, OutputImageType]
        rescaler = RescaleFilterType.New()
        rescaler.SetInput(curvatureFlowFilter.GetOutput())

        outputPixelTypeMinimum = itk.NumericTraits[OutputPixelType].min()
        outputPixelTypeMaximum = itk.NumericTraits[OutputPixelType].max()

        rescaler.SetOutputMinimum(outputPixelTypeMinimum)
        rescaler.SetOutputMaximum(outputPixelTypeMaximum)

        WriterType = itk.ImageFileWriter[OutputImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def GradientAnisotropicDiffusion (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Compute Gradient Anisotropic Diffusion ###
        #Perform anisotropic diffusion on an image.

        numberOfIterations = request.POST.get("numberOfIterations_GradientAnisotropicDiffusion","")
        numberOfIterations = int(numberOfIterations)
        timeStep = request.POST.get("timeStep_GradientAnisotropicDiffusion","")
        timeStep = float(timeStep)
        conductance = request.POST.get("conductance_GradientAnisotropicDiffusion","")
        conductance = float(conductance)

        photo_name_processed = photo_name_clicked + "_GradientAnisotropicDiffusion" + str(numberOfIterations) + str(timeStep) + str(conductance)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
 
        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        ReaderType = itk.ImageFileReader[InputImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        FilterType = itk.GradientAnisotropicDiffusionImageFilter[
            InputImageType, InputImageType]
        gradientAnisotropicDiffusionFilter = FilterType.New()

        gradientAnisotropicDiffusionFilter.SetInput(reader.GetOutput())
        gradientAnisotropicDiffusionFilter.SetNumberOfIterations(numberOfIterations)
        gradientAnisotropicDiffusionFilter.SetTimeStep(timeStep)
        gradientAnisotropicDiffusionFilter.SetConductanceParameter(conductance)

        RescaleFilterType = itk.RescaleIntensityImageFilter[
            InputImageType, OutputImageType]
        rescaler = RescaleFilterType.New()
        rescaler.SetInput(gradientAnisotropicDiffusionFilter.GetOutput())

        outputPixelTypeMinimum = itk.NumericTraits[OutputPixelType].min()
        outputPixelTypeMaximum = itk.NumericTraits[OutputPixelType].max()

        rescaler.SetOutputMinimum(outputPixelTypeMinimum)
        rescaler.SetOutputMaximum(outputPixelTypeMaximum)

        WriterType = itk.ImageFileWriter[OutputImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

##Image Morphology
def BinaryDilate (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Dilate a Binary Image ###
        #Dilate regions by using a specified kernel, also known as a structuring element. In this example, the white regions are enlarged.

        radiusValue = request.POST.get("radiusValue_BinaryDilate","")
        radiusValue = int(radiusValue)

        photo_name_processed = photo_name_clicked + "_BinaryDilate" + str(radiusValue)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)
    
        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        ReaderType = itk.ImageFileReader[ImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        StructuringElementType = itk.FlatStructuringElement[Dimension]
        structuringElement = StructuringElementType.Ball(radiusValue)

        DilateFilterType = itk.BinaryDilateImageFilter[ImageType,
                                                    ImageType,
                                                    StructuringElementType]
        dilateFilter = DilateFilterType.New()
        dilateFilter.SetInput(reader.GetOutput())
        dilateFilter.SetKernel(structuringElement)

        WriterType = itk.ImageFileWriter[ImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(dilateFilter.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)
    
def BinaryErode (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
            
        ### Erode a Binary Image ###
        #Erode regions by using a specified kernel, also known as a structuring element. In this example, the white regions shrink.

        radiusValue = request.POST.get("radiusValue_BinaryErode","")
        radiusValue = int(radiusValue)

        photo_name_processed = photo_name_clicked + "_BinaryErode" + str(radiusValue)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        ReaderType = itk.ImageFileReader[ImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        StructuringElementType = itk.FlatStructuringElement[Dimension]
        structuringElement = StructuringElementType.Ball(radiusValue)

        ErodeFilterType = itk.BinaryErodeImageFilter[ImageType,
                                                    ImageType,
                                                    StructuringElementType]
        erodeFilter = ErodeFilterType.New()
        erodeFilter.SetInput(reader.GetOutput())
        erodeFilter.SetKernel(structuringElement)

        WriterType = itk.ImageFileWriter[ImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(erodeFilter.GetOutput())

        writer.Update()    

        return HttpResponse(photo_dcm_processed_path)
    
def GrayScaleDilate (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Dilate a grayscale image ###
        #Dilate regions by using a specified kernel, also known as a structuring element. In this example, the white regions are enlarged.

        radiusValue = request.POST.get("radiusValue_GrayScaleDilate","")
        radiusValue = int(radiusValue)

        photo_name_processed = photo_name_clicked + "_GrayScaleDilate" + str(radiusValue)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        StructuringElementType = itk.FlatStructuringElement[Dimension]
        structuringElement = StructuringElementType.Ball(radiusValue)

        grayscaleFilter = itk.GrayscaleDilateImageFilter[
            ImageType, ImageType, StructuringElementType].New()
        grayscaleFilter.SetInput(reader.GetOutput())
        grayscaleFilter.SetKernel(structuringElement)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(grayscaleFilter.GetOutput())

        writer.Update()    
    
        return HttpResponse(photo_dcm_processed_path)
    
def GrayScaleErode (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Erode a grayscale image ###
        #Erode regions by using a specified kernel, also known as a structuring element. In this example, the white regions shrink.

        radiusValue = request.POST.get("radiusValue_GrayScaleErode","")
        radiusValue = int(radiusValue)

        photo_name_processed = photo_name_clicked + "_GrayScaleErode" + str(radiusValue)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        ReaderType = itk.ImageFileReader[ImageType]
        reader = ReaderType.New()
        reader.SetFileName(str(inputImage))

        StructuringElementType = itk.FlatStructuringElement[Dimension]
        structuringElement = StructuringElementType.Ball(radiusValue)

        GrayscaleFilterType = itk.GrayscaleErodeImageFilter[
            ImageType, ImageType, StructuringElementType]
        grayscaleFilter = GrayscaleFilterType.New()
        grayscaleFilter.SetInput(reader.GetOutput())
        grayscaleFilter.SetKernel(structuringElement)

        WriterType = itk.ImageFileWriter[ImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(grayscaleFilter.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)
      
##Edge Detection & Feature Extraction
def CannyEdgeDetection (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Detect Edges With Canny Edge Detection Filter ###
        #Apply CannyEdgeDetectionImageFilter to an image

        variance = request.POST.get("variance_CannyEdgeDetection","")
        variance = float(variance)
        lowerThreshold = request.POST.get("lowerThreshold_CannyEdgeDetection","")
        lowerThreshold = float(lowerThreshold)
        upperThreshold = request.POST.get("upperThreshold_CannyEdgeDetection","")
        upperThreshold = float(upperThreshold)

        photo_name_processed = photo_name_clicked + "_CannyEdgeDetection" + str(variance) + str(lowerThreshold) + str(upperThreshold)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        reader = itk.ImageFileReader[InputImageType].New()
        reader.SetFileName(str(inputImage))

        cannyFilter = itk.CannyEdgeDetectionImageFilter[
            InputImageType,
            InputImageType].New()
        cannyFilter.SetInput(reader.GetOutput())
        cannyFilter.SetVariance(variance)
        cannyFilter.SetLowerThreshold(lowerThreshold)
        cannyFilter.SetUpperThreshold(upperThreshold)


        rescaler = itk.RescaleIntensityImageFilter[
            InputImageType,
            OutputImageType].New()
        rescaler.SetInput(cannyFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[OutputImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def SobelEdgeDetection (request, *args, **kwargs):
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':    
    
        ### Sobel Edge Detection Image Filter ###
        #Apply SobelEdgeDetectionImageFilter to an image

        photo_name_processed = photo_name_clicked + "_SobelEdgeDetection"
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path  

        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        reader = itk.ImageFileReader[InputImageType].New()
        reader.SetFileName(str(inputImage))

        SobelFilter = itk.SobelEdgeDetectionImageFilter[
            InputImageType,
            InputImageType].New()
        SobelFilter.SetInput(reader.GetOutput())

        rescaler = itk.RescaleIntensityImageFilter[
            InputImageType,
            OutputImageType].New()
        rescaler.SetInput(SobelFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[OutputImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def LaplacianRecursive (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':

        ### Laplacian Recursive Gaussian Image Filter ###
        #Compute the Laplacian of an image.

        photo_name_processed = photo_name_clicked + "_LaplacianRecursive"
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        reader = itk.ImageFileReader[InputImageType].New()
        reader.SetFileName(str(inputImage))

        LaplacianRecursiveFilter = itk.LaplacianRecursiveGaussianImageFilter[
            InputImageType,
            InputImageType].New()
        LaplacianRecursiveFilter.SetInput(reader.GetOutput())

        rescaler = itk.RescaleIntensityImageFilter[
            InputImageType,
            OutputImageType].New()
        rescaler.SetInput(LaplacianRecursiveFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[OutputImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

def GradientMagnitude (request, *args, **kwargs):

    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':    
    
        ### Compute Gradient Magnitude Of Grayscale Image ###
        #This example demonstrates how to compute the magnitude of the gradient of an image.
      
        photo_name_processed = photo_name_clicked + "_GradientMagnitude"
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path  

        InputPixelType = itk.F
        OutputPixelType = itk.UC
        Dimension = 2

        InputImageType = itk.Image[InputPixelType, Dimension]
        OutputImageType = itk.Image[OutputPixelType, Dimension]

        reader = itk.ImageFileReader[InputImageType].New()
        reader.SetFileName(str(inputImage))

        GradientMagnitudeFilter = itk.GradientMagnitudeImageFilter[
            InputImageType,
            InputImageType].New()
        GradientMagnitudeFilter.SetInput(reader.GetOutput())

        rescaler = itk.RescaleIntensityImageFilter[
            InputImageType,
            OutputImageType].New()
        rescaler.SetInput(GradientMagnitudeFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[OutputImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

##Image Intensity Transformations
def Sigmoid (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
            
        ### Compute Sigmoid ###
        #Computes the sigmoid function pixel-wise.

        outputMinimum = request.POST.get("outputMinimum_Sigmoid","")
        outputMinimum = int(outputMinimum)
        outputMaximum = request.POST.get("outputMaximum_Sigmoid","")
        outputMaximum = int(outputMaximum)
        alpha = request.POST.get("alpha_Sigmoid","")
        alpha = float(alpha)
        beta = request.POST.get("beta_Sigmoid","")
        beta = float(beta)

        photo_name_processed = photo_name_clicked + "_Sigmoid" + str(outputMinimum) + str(outputMaximum) + str(alpha) + str(beta)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)
        
        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path

        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        sigmoidFilter = itk.SigmoidImageFilter[ImageType, ImageType].New()
        sigmoidFilter.SetInput(reader.GetOutput())
        sigmoidFilter.SetOutputMinimum(outputMinimum)
        sigmoidFilter.SetOutputMaximum(outputMaximum)
        sigmoidFilter.SetAlpha(alpha)
        sigmoidFilter.SetBeta(beta)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(sigmoidFilter.GetOutput())

        writer.Update()

        return HttpResponse(photo_dcm_processed_path)

##Segmentation

##Thresholding
def BinaryThreshold (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
                
        ### Threshold An Image Using Binary Thresholding ###
        #Binarize an input image by thresholding.
        
        lowerThreshold = request.POST.get("lowerThreshold_BinaryThreshold","")
        lowerThreshold = int(lowerThreshold)
        upperThreshold = request.POST.get("upperThreshold_BinaryThreshold","")     
        upperThreshold = int(upperThreshold)
        outsideValue = request.POST.get("outsideValue_BinaryThreshold","")     
        outsideValue = int(outsideValue)
        insideValue = request.POST.get("insideValue_BinaryThreshold","")     
        insideValue = int(insideValue)

        photo_name_processed = photo_name_clicked + "_BinaryThreshold" + str(lowerThreshold) + str(upperThreshold) + str(outsideValue) + str(insideValue)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        thresholdFilter = itk.BinaryThresholdImageFilter[ImageType, ImageType].New()
        thresholdFilter.SetInput(reader.GetOutput())

        thresholdFilter.SetLowerThreshold(lowerThreshold)
        thresholdFilter.SetUpperThreshold(upperThreshold)
        thresholdFilter.SetOutsideValue(outsideValue)
        thresholdFilter.SetInsideValue(insideValue)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(thresholdFilter.GetOutput())

        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)
    
def OtsuThreshold (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Threshold An Image Using Otsu ###
        #Threshold an Image using Otsu method.

        #Default Values: Bins:128 - Thresholds:1 - LabelOffset:0
        numberOfHistogramBins = request.POST.get("numberOfHistogramBins_OtsuThreshold","")
        numberOfHistogramBins = int(numberOfHistogramBins)
        numberOfThresholds = request.POST.get("numberOfThresholds_OtsuThreshold","")
        numberOfThresholds = int(numberOfThresholds)
        labelOffset = request.POST.get("labelOffset_OtsuThreshold","")
        labelOffset = int(labelOffset)

        photo_name_processed = photo_name_clicked + "_OtsuThreshold" + str(numberOfHistogramBins) + str(numberOfThresholds) + str(labelOffset)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        thresholdFilter = itk.OtsuMultipleThresholdsImageFilter[
                ImageType,
                ImageType].New()
        thresholdFilter.SetInput(reader.GetOutput())

        thresholdFilter.SetNumberOfHistogramBins(numberOfHistogramBins)
        thresholdFilter.SetNumberOfThresholds(numberOfThresholds)
        thresholdFilter.SetLabelOffset(labelOffset)

        rescaler = itk.RescaleIntensityImageFilter[ImageType, ImageType].New()
        rescaler.SetInput(thresholdFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)

def Threshold (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Threshold An Image ###
        #Threshold an image using itk::ThresholdImageFilter
        
        lowerThreshold = request.POST.get("lowerThreshold_Threshold","")
        lowerThreshold = int(lowerThreshold)
        upperThreshold = request.POST.get("upperThreshold_Threshold","")
        upperThreshold = int(upperThreshold)

        photo_name_processed = photo_name_clicked + "_Threshold" + str(lowerThreshold) + str(upperThreshold)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        thresholdFilter = itk.ThresholdImageFilter[ImageType].New()

        thresholdFilter.SetInput(reader.GetOutput())
        thresholdFilter.ThresholdOutside(lowerThreshold, upperThreshold)
        thresholdFilter.SetOutsideValue(0)

        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(thresholdFilter.GetOutput())

        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)

##Region Growing
def ConfidenceConnected (request, *args, **kwargs):
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
                
        ### Region Growing 1 ###
        #Confidence Connected Threshold Region Growing Segmentation
        
        PstX = request.POST.get("PstX_ConfidenceConnected","")
        PstY = request.POST.get("PstY_ConfidenceConnected","")
        array_Seed = [int(PstX),int(PstY)]
        iterations = request.POST.get("iterations_ConfidenceConnected","")
        iterations = int(iterations)

        photo_name_processed = photo_name_clicked + "_ConfidenceConnected" + str(PstX) + str(PstY) + str(iterations)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        PixelType = itk.UC
        Dimension = 2

        ImageType = itk.Image[PixelType, Dimension]

        reader = itk.ImageFileReader[ImageType].New()
        reader.SetFileName(str(inputImage))

        RegionGrowingFilter = itk.ConfidenceConnectedImageFilter[
                ImageType,
                ImageType].New()
        RegionGrowingFilter.SetInput(reader.GetOutput())

        RegionGrowingFilter.AddSeed(array_Seed)
        RegionGrowingFilter.SetMultiplier( 2.5 )
        RegionGrowingFilter.SetNumberOfIterations(iterations)
        RegionGrowingFilter.SetReplaceValue( 255 )
        RegionGrowingFilter.SetInitialNeighborhoodRadius( 2 )

        rescaler = itk.RescaleIntensityImageFilter[ImageType, ImageType].New()
        rescaler.SetInput(RegionGrowingFilter.GetOutput())
        rescaler.SetOutputMinimum(0)
        rescaler.SetOutputMaximum(255)
            
        writer = itk.ImageFileWriter[ImageType].New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(rescaler.GetOutput())

        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)

##Watershed
def Watershed (request, *args, **kwargs):                
    
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
    
    photo_name_clicked = kwargs.get('name', None)
    photo_dcm_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_clicked)

    if request.method == 'POST':
        
        ### Watershed Image Filter ###
        #This example illustrates how to segment an image using the watershed method.

        #A rule of thumb is to set the Threshold to be about 1/100 of the Level.
        #Good Values: threshold:0.002 - level:0.2
        threshold = request.POST.get("threshold_Watershed","")
        threshold = float(threshold)
        level = request.POST.get("level_Watershed","")
        level = float(level)

        photo_name_processed = photo_name_clicked + "_Watershed" + str(threshold) + str(level)
        photo_dcm_processed_path = 'media/dicom/%s/%s.dcm' % (patient_id, photo_name_processed)

        inputImage = photo_dcm_path
        outputImage = photo_dcm_processed_path       
        
        Dimension = 2

        FloatPixelType = itk.ctype('float')
        FloatImageType = itk.Image[FloatPixelType, Dimension]

        reader = itk.ImageFileReader[FloatImageType].New()
        reader.SetFileName(str(inputImage))

        gradientMagnitude = \
            itk.GradientMagnitudeImageFilter.New(Input=reader.GetOutput())

        watershed = \
            itk.WatershedImageFilter.New(Input=gradientMagnitude.GetOutput())

        watershed.SetThreshold(threshold)
        watershed.SetLevel(level)

        LabeledImageType = type(watershed.GetOutput())

        PixelType = itk.ctype('unsigned char')
        RGBPixelType = itk.RGBPixel[PixelType]
        RGBImageType = itk.Image[RGBPixelType, Dimension]

        ScalarToRGBColormapFilterType = \
            itk.ScalarToRGBColormapImageFilter[LabeledImageType, RGBImageType]
        colormapImageFilter = ScalarToRGBColormapFilterType.New()
        colormapImageFilter.SetColormap(ScalarToRGBColormapFilterType.Jet)
        colormapImageFilter.SetInput(watershed.GetOutput())
        colormapImageFilter.Update()

        WriterType = itk.ImageFileWriter[RGBImageType]
        writer = WriterType.New()
        writer.SetFileName(str(outputImage))
        writer.SetInput(colormapImageFilter.GetOutput())
        writer.Update()
        
        return HttpResponse(photo_dcm_processed_path)       

##### SliceDrop #####

def SliceDrop (request, *args, **kwargs):
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
 
    template_name = 'web_med/index.html'
    return render(request, template_name, {
        'pi': patient_id,
        'ps': patient_slug
    })

##### AMI Volume Rendering #####

def l15process(request, *args, **kwargs):
    template_name = 'web_med/l15.html'
    return render(request, template_name)

##### Volume Segmentation #####

def VolumeSegmentation (request, *args, **kwargs):
    global stl_name
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
 
    if request.method == 'POST':
              
        LowerThreshold = request.POST.get("LowerThreshold","")
	UpperThreshold = request.POST.get("UpperThreshold","")
        Name = request.POST.get("Name","")
	stl_name = Name    	
	PathDicom = 'media/dicom/%s/' % (patient_id)    
    
    	reader = vtk.vtkDICOMImageReader()
    	reader.SetDirectoryName(PathDicom)
    	reader.Update()

    	#Load dimensions using `GetDataExtent`
    	_extent = reader.GetDataExtent()
    	ConstPixelDims = [_extent[1]-_extent[0]+1, _extent[3]-_extent[2]+1, _extent[5]-_extent[4]+1]
    	ConstPixelSpacing = reader.GetPixelSpacing()

    	#Thresholding the data: mask out all non-bone tissue from the image, and create a bone-mask
    	threshold = vtk.vtkImageThreshold ()
    	threshold.SetInputConnection(reader.GetOutputPort())
    	#threshold.ThresholdByLower(400)  # remove all soft tissue
    	threshold.ThresholdBetween(-600,-400);

        threshold.ReplaceInOn()
        threshold.SetInValue(0)  # set all values below 400 to 0
        threshold.ReplaceOutOn()
        threshold.SetOutValue(1)  # set all values above 400 to 1
        threshold.Update()

	#Surface Extraction: Marching Cubes
	dmc = vtk.vtkDiscreteMarchingCubes()
	dmc.SetInputConnection(threshold.GetOutputPort())
	dmc.GenerateValues(1, 1, 1)
	dmc.Update()

	#Exporting the surface as an stl
	writer = vtk.vtkSTLWriter()
	writer.SetInputConnection(dmc.GetOutputPort())
	writer.SetFileTypeToBinary()
	vtk_patient_path = ('media/stl/%s/') % (patient_id)
	if not os.path.exists(vtk_patient_path):
           os.makedirs(vtk_patient_path)
	vtk_path = ('media/stl/%s/%s.stl') % (patient_id,Name)
	writer.SetFileName(vtk_path)
	writer.Write()

    return HttpResponse() 


def vtksegview (request, *args, **kwargs):
   
    patient_id = kwargs.get('pk', None)
    patient_slug = kwargs.get('slug', None)
      
    vtk_path = 'media/stl/%s/%s.stl' % (patient_id, stl_name)
   
    template_name = 'web_med/vtk.html'  
    return render(request, template_name, {
        'vtk_path':vtk_path
    }) 



