from malaria24.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'malaria24',
    }
}

ONAPIE_ACCESS_TOKEN = 'foo'
ONA_API_URL = 'https://odk.ona.io'
VUMI_GO_ACCOUNT_KEY = 'VUMI_GO_ACCOUNT_KEY'
VUMI_GO_API_TOKEN = 'VUMI_GO_API_TOKEN'
VUMI_GO_CONVERSATION_KEY = 'VUMI_GO_CONVERSATION_KEY'
