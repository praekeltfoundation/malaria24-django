FROM praekeltfoundation/django-bootstrap:py3.7
RUN apt-get-install.sh wkhtmltopdf xvfb xauth

COPY . /app

RUN python -m pip install --upgrade pip

RUN pip install git+https://github.com/onaio/onapie.git#egg=onapie &&\
    pip install -e . &&\
    pip install -r requirements.txt

ENV DJANGO_SETTINGS_MODULE="malaria24.settings.docker"

RUN python manage.py collectstatic --noinput 

RUN printf '#!/bin/bash\nxvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf -q $*' > /usr/local/bin/wkhtmltopdf.sh \
  && chmod +x /usr/local/bin/wkhtmltopdf.sh \
  && ln -s /usr/local/bin/wkhtmltopdf.sh /usr/local/bin/wkhtmltopdf

CMD ["malaria24.wsgi:application"]
