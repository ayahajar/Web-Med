# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib import admin
from .models import Photo, Patient, UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name')

    '''def user_info(self, obj):
        return obj.description

    def get_queryset(self, request):
        queryset = super(UserProfileAdmin, self).get_queryset(request)
        queryset = queryset.order_by('-phone', 'user')
        return queryset

    user_info.short_description = 'Info'''

   



# Register your models here.
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Patient)
admin.site.register(Photo)

