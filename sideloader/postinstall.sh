cd "${INSTALLDIR}/${NAME}/malaria24/"
manage="${VENV}/bin/python ${INSTALLDIR}/${NAME}/manage.py"

pip install git+git://github.com/onaio/onapie.git#egg=onapie

$manage migrate --noinput --settings=malaria24.settings.production

# process static files
$manage compress --settings=malaria24.settings.production
$manage collectstatic --noinput --settings=malaria24.settings.production

# compile i18n strings
$manage compilemessages --settings=malaria24.settings.production

# setup wkhtmltopdf
# reference here: https://github.com/JazzCore/python-pdfkit/wiki/Using-wkhtmltopdf-without-X-server
echo -e '#!/bin/bash\nxvfb-run -a --server-args="-screen 0, 1024x768x24" /usr/bin/wkhtmltopdf $*' > /usr/bin/wkhtmltopdf.sh
chmod a+x /usr/bin/wkhtmltopdf.sh
ln -s /usr/bin/wkhtmltopdf.sh /usr/local/bin/wkhtmltopdf
