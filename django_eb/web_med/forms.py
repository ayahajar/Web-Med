from django.contrib.auth import authenticate, get_user_model
from django import forms
from django.contrib.auth.models import User
from .models import Patient, Photo, UserProfile, Nii, VTK
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class PatientForm(forms.ModelForm):
    firstName  = forms.CharField(widget=forms.TextInput(
        attrs={
            'class' : 'form-control',
        }
    ))

    lastName  = forms.CharField(widget=forms.TextInput(
        attrs={
            'class' : 'form-control',
        }
    ))

    description  = forms.CharField(widget=forms.Textarea(
        attrs={
            'class' : 'form-control',
        }
    ))

    class Meta:
        model = Patient
        fields = ('firstName', 'lastName', 'description')

class PhotoForm(forms.ModelForm):

    class Meta:
        model = Photo
        fields = ('file', )

class NiiForm(forms.ModelForm):
    
    class Meta:
        model = Nii
        fields = ('file', )

class VTKForm(forms.ModelForm):
    
    class Meta:
        model = VTK
        fields = ('file', )

class UsersLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput,)

    def __init__(self, *args, **kwargs):
        super(UsersLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            "name":"username"})
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            "name":"password"})

    def clean(self, *args, **keyargs):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("This user does not exists")
            if not user.check_password(password):
                raise forms.ValidationError("Incorrect Password")
            if not user.is_active:
                raise forms.ValidationError("User is no longer active")

        return super(UsersLoginForm, self).clean(*args, **keyargs)


User = get_user_model()

class UsersRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "confirm_email", 
            "password"
        ]
    username = forms.CharField()
    first_name = forms.CharField()
    last_name = forms.CharField()
    email = forms.EmailField(label="Email")
    confirm_email = forms.EmailField(label="Confirm Email")
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super(UsersRegisterForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            "name":"username"})
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            "name":"first_name"})
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            "name":"last_name"})
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            "name":"email"})
        self.fields['confirm_email'].widget.attrs.update({
            'class': 'form-control',
            "name":"confirm_email"})
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            "name":"password"})

    def clean(self, *args, **keyargs):
        email = self.cleaned_data.get("email")
        confirm_email = self.cleaned_data.get("confirm_email")
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        first_name = self.cleaned_data.get("first_name")
        last_name = self.cleaned_data.get("last_name")

        if email != confirm_email:
            raise forms.ValidationError("Email must match")
        
        email_qs = User.objects.filter(email=email)
        if email_qs.exists():
            raise forms.ValidationError("Email is already registered")

        username_qs = User.objects.filter(username=username)
        if username_qs.exists():
            raise forms.ValidationError("User with this username already registered")

        if len(password) < 6:	#you can add more validations for password
            raise forms.ValidationError("Password must be greater than 6 characters")

        return super(UsersRegisterForm, self).clean(*args, **keyargs)

class EditProfileForm(UserChangeForm):
    template_name='/something/else'

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'password', 
        )