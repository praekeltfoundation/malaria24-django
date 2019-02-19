# This is a development Dockerfile. For versioned Dockerfiles see:
# https://github.com/praekeltfoundation/docker-seed
FROM praekeltfoundation/django-bootstrap:py2.7-jessie

 COPY . /app
RUN pip install -e git+git://github.com/onaio/onapie.git#egg=onapie &&\
    pip install -e .

 ENV DJANGO_SETTINGS_MODULE "malaria24.settings"
RUN python manage.py collectstatic --noinput
CMD ["malaria24.wsgi:application"]
