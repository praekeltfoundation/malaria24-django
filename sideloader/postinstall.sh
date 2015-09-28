cd "${INSTALLDIR}/${NAME}/malaria24/"
manage="${VENV}/bin/python ${INSTALLDIR}/${NAME}/manage.py"

pip install -e git+git://github.com/onaio/onapie.git#egg=onapie

$manage migrate --settings=malaria24.settings.production

# process static files
$manage compress --settings=malaria24.settings.production
$manage collectstatic --noinput --settings=malaria24.settings.production

# compile i18n strings
$manage compilemessages --settings=malaria24.settings.production
