from django.contrib import admin
from .models import Skill, Certification, University, Profile, Offer, Application, ScoreHistory

admin.site.register(Skill)
admin.site.register(Certification)
admin.site.register(University)
admin.site.register(Profile)
admin.site.register(Offer)
admin.site.register(Application)
admin.site.register(ScoreHistory)