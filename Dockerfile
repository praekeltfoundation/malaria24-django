FROM praekeltfoundation/django-bootstrap:py2.7
RUN apt-get-install.sh wkhtmltopdf xvfb xauth

COPY . /app

RUN pip install https://github.com/onaio/onapie/archive/develop.zip#egg=onapie &&\
    pip install -e .

ENV DJANGO_SETTINGS_MODULE="malaria24.settings.docker" \
    CELERY_APP=malaria24 \
    CELERY_WORKER=1 \
    CELERY_BEAT=1

RUN python manage.py collectstatic --noinput &&\
	python manage.py compress

RUN printf '#!/bin/bash\nxvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf -q $*' > /usr/local/bin/wkhtmltopdf.sh \
  && chmod +x /usr/local/bin/wkhtmltopdf.sh &&\
  ln -s /usr/local/bin/wkhtmltopdf.sh /usr/local/bin/wkhtmltopdf

CMD ["malaria24.wsgi:application"]
