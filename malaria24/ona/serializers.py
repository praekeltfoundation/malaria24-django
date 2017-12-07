from django.db.models.base import ObjectDoesNotExist
from rest_framework import serializers
from .models import SMS, InboundSMS, SMSEvent


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


class SMSEventSerializer(serializers.ModelSerializer):
    message_id = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = SMSEvent
        exclude = ('sms',)

    def validate_message_id(self, value):
        """ Replace 'message_id' with the matching SMS object '"""
        try:
            sms = SMS.objects.filter(message_id=value).latest('created_at')
        except ObjectDoesNotExist:
            raise serializers.ValidationError("Unknown message_id: %s" % value)
        return sms

    def create(self, validated_data):
        sms = validated_data.pop('message_id')
        validated_data['sms'] = sms
        return SMSEvent.objects.create(**validated_data)
