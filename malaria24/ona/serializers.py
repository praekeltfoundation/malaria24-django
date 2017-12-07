from django.db.models.base import ObjectDoesNotExist
from rest_framework import serializers
from .models import SMS, InboundSMS


class InboundSMSSerializer(serializers.ModelSerializer):
    reply_to = serializers.CharField(max_length=255, required=False,
                                     allow_null=True, default=None)

    class Meta:
        model = InboundSMS
        exclude = ('created_at',)

    def validate_reply_to(self, value):
        """ Replace 'reply_to' with the matching SMS object """
        try:
            sms = SMS.objects.filter(message_id=value).latest('created_at')
        except ObjectDoesNotExist:
            return None
        return sms
