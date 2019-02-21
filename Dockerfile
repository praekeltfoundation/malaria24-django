# This is a development Dockerfile. For versioned Dockerfiles see:
# https://github.com/praekeltfoundation/docker-seed
FROM praekeltfoundation/django-bootstrap:py2.7-jessie

COPY . /app

RUN pip install https://github.com/onaio/onapie/archive/develop.zip#egg=onapie &&\
    pip install -e .

ENV DJANGO_SETTINGS_MODULE "malaria24.settings.docker"
RUN python manage.py collectstatic --noinput

RUN apt-get-install.sh wkhtmltopdf xvfb
RUN printf '#!/bin/bash\nxvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf -q $*' > /usr/local/bin/wkhtmltopdf.sh \
  && chmod +x /usr/local/bin/wkhtmltopdf.sh

CMD ["malaria24.wsgi:application"]
