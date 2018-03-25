
from django.db import models
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
import os
import os.path

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name= 'user', primary_key=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    
    def __str__(self):
        return self.user.username

    def __str__(self):
        return self.first_name
    
    def __str__(self):
        return self.last_name
        

def create_profile(sender, **kwargs):
    user = kwargs["instance"]
    if kwargs["created"]:
        user_profile = UserProfile(user=user)
        user_profile.save()
        #user_profile = UserProfile.objects.create(user=kwargs['instance'])

post_save.connect(create_profile, sender=User)


class Patient(models.Model):
    doctor = models.IntegerField(default=1)
    firstName = models.CharField(max_length=200)
    lastName = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.firstName + ' ' + self.lastName + ' - ' + self.description

    def slug(self):
        return slugify(self.lastName)

### Upload to function
def get_upload_to(instance, filename):
    return os.path.join('dicom', str(instance.patient.id), filename)

def get_upload_to_nii(instance, filename):
    return os.path.join('nii', str(instance.patient.id), filename)

def get_upload_to_vtk(instance, filename):
    return os.path.join('vtk', str(instance.patient.id), filename)

class Photo(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_photos')
    #title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=get_upload_to)
    #uploaded_at = models.DateTimeField(auto_now_add=True)

    def get_file_name(self):
        path = self.file.name
        return os.path.basename(path)

    def get_file_name_withoutExtension(self):
        path = self.file.name
        base = os.path.basename(path)
        return os.path.splitext(base)[0]


class Photopng(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_photos_png')
    image = models.ImageField()

class Nii(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_niis')
    file = models.FileField(upload_to=get_upload_to_nii)

    def get_file_name(self):
        path = self.file.name
        return os.path.basename(path)

    def get_file_name_withoutExtension(self):
        path = self.file.name
        base = os.path.basename(path)
        return os.path.splitext(base)[0]


class VTK(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_vtks')
    file = models.FileField(upload_to=get_upload_to_vtk)

    def get_file_name(self):
        path = self.file.name
        return os.path.basename(path)

    def get_file_name_withoutExtension(self):
        path = self.file.name
        base = os.path.basename(path)
        return os.path.splitext(base)[0]



