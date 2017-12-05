from rest_framework import serializers
from .models import InboundSMS


class InboundSMSSerializer(serializers.ModelSerializer):

    class Meta:
        model = InboundSMS
        exclude = ('created_at',)
