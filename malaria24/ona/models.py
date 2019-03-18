import logging
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_save
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import datetime

import pytz
import re


class Digest(models.Model):
    """
    A Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        new_cases = (ReportedCase.objects.filter(digest__isnull=True)
                     .order_by("create_date_time"))
        if not new_cases.exists():
            return

        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        new_cases.update(digest=digest)
        return digest

    def send_digest_email(self):
        date = datetime.today()
        week = 'Week ' + str(
            date.strftime("%U")) + ' ' + str(date.year)

        if self.reportedcase_set.all():
            start_date = self.reportedcase_set.all() \
                .first().create_date_time.strftime(
                    "%d %B %Y"
            )
            end_date = self.reportedcase_set.all() \
                .last().create_date_time.strftime(
                    "%d %B %Y"
            )
            week = "{0} to {1}".format(start_date, end_date)

        context = {
            'digest': self,
            'week': week,
        }
        text_content = render_to_string('ona/text_digest.txt', context)
        html_content = render_to_string('ona/html_digest.html', context)
        return send_mail(
            subject='Digest of reported Malaria cases %s' % (
                timezone.now().strftime('%x'),),
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=set([actor.email_address
                                for actor
                                in self.recipients.all()]),
            html_message=html_content)


class CalculationsMixin(object):

    def calculate_over_under_5(self, qs):
        over5 = len([x for x in qs if x.age >= 5])
        under5 = qs.count() - over5
        return (over5, under5)

    def calculate_male_female(self, qs):
        females = qs.filter(gender__icontains='f').count()
        males = qs.exclude(gender__icontains='f').count()
        return (females, males)

    def calculate_travelhistory(self, qs):
        somalia = qs.filter(abroad__icontains='Somalia').count()
        ethiopia = qs.filter(abroad__icontains='Ethiopia').count()
        mozambique = qs.filter(abroad__icontains='Mozambique').count()
        zambia = qs.filter(abroad__icontains='Zambia').count()
        zimbabwe = qs.filter(abroad__icontains='Zimbabwe').count()
        c_list = [
            'Zimbabwe', 'Somalia', 'Ethiopia', 'Mozambique',
            'Zambia'
        ]
        other = qs.exclude(abroad__in=c_list).count()
        return (somalia, ethiopia, mozambique, zambia, zimbabwe, other)

    def noInternationalTravel(self, qs):
        noInternTravel = qs.filter(abroad__icontains='No').count()
        return noInternTravel


class NationalDigest(models.Model, CalculationsMixin):
    """
    A National Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MANAGER_NATIONAL, MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self):
        utc = pytz.UTC
        date = datetime.today()
        week = 'Week ' + str(date.strftime("%U")) + ' ' + str(date.year)
        provinces = []
        total_cases = total_females = total_males = 0
        total_under5 = total_over5 = 0
        total_somalia = total_ethiopia = total_no_international_travel = \
            total_mozambique = total_zambia = total_zimbabwe = 0
        total_other = 0

        all_case_ids = []

        for p, p_name in PROVINCES:
            districts = (Facility.objects.filter(province=p).values_list(
                'district', flat=True).distinct().order_by("district"))
            for district in districts:
                min_date = datetime.max.replace(tzinfo=utc)
                max_date = datetime(1991, 1, 1, 0, 0,
                                    0, 0, pytz.timezone('US/Pacific'))
                district_fac_codes = Facility.objects.filter(
                    district=district).values_list(
                    'facility_code',
                    flat=True).distinct().order_by("district")
                province_cases = ReportedCase.objects.filter(
                    facility_code__in=district_fac_codes, digest__isnull=True)

                total_cases += province_cases.count()
                all_case_ids += province_cases.values_list('pk', flat=True)

                female, male = self.calculate_male_female(province_cases)
                total_females += female
                total_males += male

                over5, under5 = self.calculate_over_under_5(province_cases)
                somalia, ethiopia, mozambique, zambia, zimbabwe, other = \
                    self.calculate_travelhistory(province_cases)
                no_international_travel = \
                    self.noInternationalTravel(province_cases)

                total_over5 += over5
                total_under5 += under5

                total_somalia += somalia
                total_ethiopia += ethiopia
                total_mozambique += mozambique
                total_zambia += zambia
                total_zimbabwe += zimbabwe
                total_other += other
                total_no_international_travel += no_international_travel

                if province_cases:
                    start_date = province_cases \
                        .first().create_date_time
                    if start_date < min_date:
                            min_date = start_date

                    end_date = province_cases \
                        .last().create_date_time
                    if end_date > max_date:
                            max_date = end_date
                    week = "{0} to {1}".format(min_date.strftime(
                        "%d %B %Y"
                    ), max_date.strftime(
                        "%d %B %Y"
                    ))

                provinces.append({
                    'province': p_name,
                    'district': district,
                    'cases': province_cases.count(),
                    'females': female, 'males': male,
                    'under5': under5,
                    'over5': over5,
                    'no_international_travel': no_international_travel,
                    'week': week,
                    'somalia': somalia,
                    'ethiopia': ethiopia,
                    'mozambique': mozambique,
                    'zambia': zambia,
                    'zimbabwe': zimbabwe,
                    'other': other
                })
        all_cases = ReportedCase.objects.filter(
            pk__in=all_case_ids).order_by('create_date_time')
        if all_cases.exists():
            min_week = all_cases.first().create_date_time
            max_week = all_cases.last().create_date_time

            week = "{0} to {1}".format(min_week.strftime(
                "%d %B %Y"
            ), max_week.strftime(
                "%d %B %Y"
            ))
        else:
            date = datetime.today()
            week = 'Week ' + str(
                date.strftime("%U")) + ' ' + str(date.year)

        totals = {}
        totals['total_cases'] = total_cases
        totals['total_females'] = total_females
        totals['total_males'] = total_males
        totals['total_under5'] = total_under5
        totals['total_over5'] = total_over5

        totals['total_no_international_travel'] = \
            total_no_international_travel
        totals['total_somalia'] = total_somalia
        totals['total_ethiopia'] = total_ethiopia
        totals['total_mozambique'] = total_mozambique
        totals['total_zambia'] = total_zambia
        totals['total_zimbabwe'] = total_zimbabwe
        totals['total_other'] = total_other

        return {
            'digest': self,
            'provinces': provinces,
            'week': week,
            'totals': totals
        }

    def send_digest_email(self):
        context = self.get_digest_email_data()
        text_content = render_to_string(
            'ona/text_national_digest.txt', context)
        html_content = render_to_string('ona/html_national_digest.html',
                                        context)
        return send_mail(
            subject='Digest of reported Malaria cases %s' % (
                timezone.now().strftime('%x'),),
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[actor.email_address
                            for actor
                            in self.recipients.all()],
            html_message=html_content)


class ProvincialDigest(models.Model, CalculationsMixin):
    """
    A Provincial Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self, province, facility_code):
        utc = pytz.UTC
        date2 = datetime.today()
        week = 'Week ' + str(date2.strftime("%U")) + ' ' + str(date2.year)
        district_list = []
        all_case_ids = []
        if not province:
            try:
                province = Facility.objects.get(
                    facility_code=facility_code).province
            except Facility.DoesNotExist:
                return {}
        districts = (Facility.objects.filter(province=province).values_list(
            'district', flat=True).distinct()
            .order_by("district"))
        total_cases = total_females = total_males = 0
        total_under5 = total_over5 = 0
        total_somalia = total_ethiopia = total_no_international_travel = \
            total_mozambique = total_zambia = total_zimbabwe = 0
        total_other = 0

        for district in districts:
            min_date = datetime.max.replace(tzinfo=utc)
            max_date = datetime(1991, 1, 1, 0, 0,
                                0, 0, pytz.timezone('US/Pacific'))
            district_fac_codes = Facility.objects.filter(
                district=district).values_list(
                    'facility_code',
                    flat=True).distinct().order_by("district")
            district_cases = ReportedCase.objects.filter(
                facility_code__in=district_fac_codes, digest__isnull=True)

            total_cases += district_cases.count()
            all_case_ids += district_cases.values_list('pk', flat=True)

            female, male = self.calculate_male_female(district_cases)
            total_females += female
            total_males += male

            over5, under5 = self.calculate_over_under_5(district_cases)
            somalia, ethiopia, mozambique, zambia, zimbabwe, other = \
                self.calculate_travelhistory(district_cases)
            no_international_travel = \
                self.noInternationalTravel(district_cases)

            total_over5 += over5
            total_under5 += under5

            total_somalia += somalia
            total_ethiopia += ethiopia
            total_mozambique += mozambique
            total_zambia += zambia
            total_zimbabwe += zimbabwe
            total_other += other
            total_no_international_travel += no_international_travel

            if district_cases:
                start_date = district_cases \
                    .first().create_date_time
                if start_date < min_date:
                        min_date = start_date

                end_date = district_cases \
                    .last().create_date_time
                if end_date > max_date:
                        max_date = end_date
                week = "{0} to {1}".format(min_date.strftime(
                    "%d %B %Y"
                ), max_date.strftime(
                    "%d %B %Y"
                ))

            district_list.append({
                'district': district,
                'cases': district_cases.count(),
                'females': female, 'males': male,
                'under5': under5,
                'over5': over5,
                'week': week,
                'no_international_travel': no_international_travel,
                'somalia': somalia,
                'ethiopia': ethiopia,
                'mozambique': mozambique,
                'zambia': zambia,
                'zimbabwe': zimbabwe,
                'other': other
            })

        all_cases = ReportedCase.objects.filter(
            pk__in=all_case_ids).order_by('create_date_time')
        if all_cases.exists():
            min_week = all_cases.first().create_date_time
            max_week = all_cases.last().create_date_time

            week = "{0} to {1}".format(min_week.strftime(
                "%d %B %Y"
            ), max_week.strftime(
                "%d %B %Y"
            ))
        else:
            date = datetime.today()
            week = 'Week ' + str(
                date.strftime("%U")) + ' ' + str(date.year)

        totals = {}
        totals['total_cases'] = total_cases
        totals['total_females'] = total_females
        totals['total_males'] = total_males
        totals['total_under5'] = total_under5
        totals['total_over5'] = total_over5

        totals['total_no_international_travel'] = \
            total_no_international_travel
        totals['total_somalia'] = total_somalia
        totals['total_ethiopia'] = total_ethiopia
        totals['total_mozambique'] = total_mozambique
        totals['total_zambia'] = total_zambia
        totals['total_zimbabwe'] = total_zimbabwe
        totals['total_other'] = total_other

        return {
            'digest': self,
            'districts': district_list,
            'week': week,
            'totals': totals,
        }

    def send_digest_email(self):
        for manager in Actor.objects.provincial():
            context = self.get_digest_email_data(
                manager.province, manager.facility_code)
            if not context:
                logging.warning(
                    'No province or facility_code for %s.' % manager.name)
                continue
            text_content = render_to_string(
                'ona/text_provincial_digest.txt', context)
            html_content = render_to_string(
                'ona/html_provincial_digest.html', context)
            mailing_list = set([
                manager.email_address
            ] + [actor.email_address for actor in self.recipients.all()])
            send_mail(
                subject='Digest of reported Malaria cases %s' % (
                    timezone.now().strftime('%x'),),
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=mailing_list,
                html_message=html_content)


class DistrictDigest(models.Model, CalculationsMixin):
    """
    A District Digest of reported cases.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    recipients = models.ManyToManyField('Actor')

    @classmethod
    def compile_digest(cls):
        recipients = Actor.objects.filter(
            role__in=[MIS],
            email_address__isnull=False)
        digest = cls.objects.create()
        digest.recipients = recipients
        digest.save()
        return digest

    def get_digest_email_data(self, district, facility_code):
        utc = pytz.UTC
        date3 = datetime.today()
        week = 'Week ' + str(date3.strftime("%U")) + ' ' + str(date3.year)
        if not district:
            try:
                district = Facility.objects.get(
                    facility_code=facility_code).district
            except Facility.DoesNotExist:
                return {}

        district_fac_codes = Facility.objects.filter(
            district=district).values_list(
                'facility_code',
                flat=True).distinct().order_by("district")

        district_cases = ReportedCase.objects.filter(
            facility_code__in=district_fac_codes, digest__isnull=True)

        facilities = Facility.objects.filter(district=district)
        fac_list = []
        all_case_ids = []
        total_cases = total_females = total_males = 0
        total_under5 = total_over5 = 0

        total_somalia = total_ethiopia = total_no_international_travel = \
            total_mozambique = total_zambia = total_zimbabwe = 0
        total_other = 0

        if district_cases:
            start_date = district_cases.first().create_date_time.strftime(
                "%d %B %Y"
            )
            end_date = district_cases.last().create_date_time.strftime(
                "%d %B %Y"
            )

            week = "{0} to {1}".format(start_date, end_date)

        for fac in facilities:
            min_date = datetime.max.replace(tzinfo=utc)
            max_date = datetime(1991, 1, 1, 0, 0,
                                0, 0, pytz.timezone('US/Pacific'))
            facility_name = 'Unknown (district: %s)' % (district,)
            if fac:
                facility_name = fac.facility_name

            district_name = 'Unknown district'
            if fac.district:
                district_name = fac.district

            fac_cases = district_cases.filter(facility_code=fac.facility_code)
            total_cases += fac_cases.count()
            all_case_ids += district_cases.values_list('pk', flat=True)

            female, male = self.calculate_male_female(fac_cases)
            total_females += female
            total_males += male

            over5, under5 = self.calculate_over_under_5(fac_cases)

            somalia, ethiopia, mozambique, zambia, zimbabwe, other = \
                self.calculate_travelhistory(fac_cases)
            no_international_travel = \
                self.noInternationalTravel(fac_cases)

            total_over5 += over5
            total_under5 += under5

            total_somalia += somalia
            total_ethiopia += ethiopia
            total_mozambique += mozambique
            total_zambia += zambia
            total_zimbabwe += zimbabwe
            total_other += other
            total_no_international_travel += no_international_travel

            if fac_cases:
                start_date = fac_cases \
                    .first().create_date_time
                if start_date < min_date:
                        min_date = start_date

                end_date = fac_cases \
                    .last().create_date_time
                if end_date > max_date:
                        max_date = end_date
                week = "{0} to {1}".format(min_date.strftime(
                    "%d %B %Y"
                ), max_date.strftime(
                    "%d %B %Y"
                ))

            fac_list.append({
                'facility': facility_name,
                'district': district_name,
                'cases': fac_cases.count(),
                'females': female, 'males': male,
                'under5': under5,
                'over5': over5,
                'week': week,
                'no_international_travel': no_international_travel,
                'somalia': somalia,
                'ethiopia': ethiopia,
                'mozambique': mozambique,
                'zambia': zambia,
                'zimbabwe': zimbabwe,
                'other': other
            })
        all_cases = ReportedCase.objects.filter(
            pk__in=all_case_ids).order_by('create_date_time')
        if all_cases.exists():
            min_week = all_cases.first().create_date_time
            max_week = all_cases.last().create_date_time

            week = "{0} to {1}".format(min_week.strftime(
                "%d %B %Y"
            ), max_week.strftime(
                "%d %B %Y"
            ))
        else:
            date = datetime.today()
            week = 'Week ' + str(
                date.strftime("%U")) + ' ' + str(date.year)

        totals = {}
        totals['total_cases'] = total_cases
        totals['total_females'] = total_females
        totals['total_males'] = total_males
        totals['total_under5'] = total_under5
        totals['total_over5'] = total_over5

        totals['total_no_international_travel'] = \
            total_no_international_travel
        totals['total_somalia'] = total_somalia
        totals['total_ethiopia'] = total_ethiopia
        totals['total_mozambique'] = total_mozambique
        totals['total_zambia'] = total_zambia
        totals['total_zimbabwe'] = total_zimbabwe
        totals['total_other'] = total_other

        return {
            'digest': self,
            'facility': fac_list,
            'week': week,
            'totals': totals
        }

    def send_digest_email(self):
        for manager in Actor.objects.district():
            context = self.get_digest_email_data(
                manager.district, manager.facility_code)
            if not context:
                logging.warning(
                    'No district or facility_code for %s.' % manager.name)
                continue
            text_content = render_to_string(
                'ona/text_district_digest.txt', context)
            html_content = render_to_string(
                'ona/html_district_digest.html', context)
            mailing_list = set([
                manager.email_address
            ] + [actor.email_address for actor in self.recipients.all()])
            send_mail(
                subject='Digest of reported Malaria cases %s' % (
                    timezone.now().strftime('%x'),),
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=mailing_list,
                html_message=html_content)


class OnaForm(models.Model):
    uuid = models.CharField(max_length=255)
    form_id = models.CharField(max_length=255, null=True)
    id_string = models.CharField(max_length=255, null=True)
    title = models.CharField(max_length=255, null=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title


class ReportedCase(models.Model):
    """
    This is a ReportedCase as captured in Ona.io and synced
    from their API to our database for easy querying.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    locality = models.CharField(max_length=255)
    date_of_birth = models.CharField(max_length=255)
    create_date_time = models.DateTimeField()
    sa_id_number = models.CharField(max_length=255, null=True)
    msisdn = models.CharField(max_length=255)
    id_type = models.CharField(max_length=255)
    abroad = models.CharField(max_length=255)
    reported_by = models.CharField(max_length=255)
    gender = models.CharField(max_length=255)
    facility_code = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, null=True)
    landmark_description = models.CharField(
        max_length=255, null=True, blank=True)
    case_number = models.CharField(
        max_length=255, null=True, blank=True)
    _id = models.CharField(max_length=255)
    _uuid = models.CharField(max_length=255)
    _xform_id_string = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    digest = models.ForeignKey('Digest', null=True, blank=True)
    ehps = models.ManyToManyField('Actor', blank=True)
    form = models.ForeignKey('OnaForm', null=True, blank=True)

    def normalize_msisdn(self, mobile_number):
        try:
            int(mobile_number)  # check if integer
            if re.match('^[+27]*([0-9]{9})$', mobile_number):
                return mobile_number
            else:
                return '+27' + mobile_number[1:]
        except ValueError:
            return mobile_number.lower()  # convert to lower case

    def get_data(self):
            '''JSON Formats need create_date_time & date_of_birth
            to be overridden

            need to validate msisdn and reported_by fields are in
            correct format
            if sa_id_number is None, needs to return empty string'''

            try:
                birth_date = datetime.strptime(self.date_of_birth, '%Y-%m-%d')
            except ValueError:
                # NOTE: This is an unfortunate side-effect of changing how
                #       date of birth is stored mid-way the data.
                #       There is historical data in Ona that has this
                #       old format.
                birth_date = datetime.strptime(self.date_of_birth, '%y%m%d')

            reported_by = self.normalize_msisdn(self.reported_by)
            msisdn = self.normalize_msisdn(self.msisdn)

            try:
                int(self.sa_id_number)  # check if integer
                sa_id_number = self.sa_id_number
            except ValueError:
                sa_id_number = ""

            return {"first_name": self.first_name,
                    "last_name": self.last_name,
                    "gender": self.gender,
                    "msisdn": msisdn,
                    "landmark_description": self.landmark_description,
                    "id_type": self.id_type,
                    "case_number": self.case_number,
                    "abroad": self.abroad,
                    "locality": self.locality,
                    "reported_by": reported_by,
                    "date_of_birth": birth_date.strftime("%Y-%m-%d"),
                    "sa_id_number": sa_id_number,
                    "create_date_time": self.create_date_time.strftime(
                        "%Y%m%d%H%M%S"),
                    "landmark": self.landmark,
                    "facility_code": self.facility_code}

    def get_today(self):
        return datetime.today()

    def get_facilities(self):
        return Facility.objects.filter(facility_code=self.facility_code)

    def get_facility_attributes(self, attname):
        return ', '.join([
            getattr(f, attname)
            for f in self.get_facilities() if getattr(f, attname)
        ]) or "Unknown"

    @property
    def facility_names(self):
        return self.get_facility_attributes('facility_name')

    @property
    def provinces(self):
        return self.get_facility_attributes('province')

    @property
    def subdistricts(self):
        return self.get_facility_attributes('subdistrict')

    @property
    def districts(self):
        return self.get_facility_attributes('district')

    @property
    def age(self):
        "Returns the age of the patient"
        today = self.get_today()
        try:
            dob = datetime.strptime(self.date_of_birth, '%Y-%m-%d')
        except ValueError:
            # NOTE: This is an unfortunate side-effect of changing how
            #       date of birth is stored mid-way the data.
            #       There is historical data in Ona that has this
            #       old format.
            dob = datetime.strptime(self.date_of_birth, '%y%m%d')
        return int((today - dob).days / 365)

    def get_ehps(self):
        return Actor.objects.ehps().filter(facility_code=self.facility_code)

    def get_email_context(self):
        return {
            'case': self,
            'ehps': self.get_ehps(),
            'site': Site.objects.get_current(),
        }

    def get_text_email_content(self):
        return render_to_string(
            'ona/text_email.txt', self.get_email_context())

    def get_html_email_content(self):
        return render_to_string(
            'ona/html_email.html', self.get_email_context())

    def get_pdf_email_content(self):
        # use attachment file
        return render_to_string(
            'ona/email_attachment.html', self.get_email_context())


EHP = 'EHP'
CASE_INVESTIGATOR = 'CASE_INVESTIGATOR'
MANAGER_DISTRICT = 'MANAGER_DISTRICT'
MANAGER_PROVINCIAL = 'MANAGER_PROVINCIAL'
MANAGER_NATIONAL = 'MANAGER_NATIONAL'
MIS = 'MIS'

PROVINCES = [
    ('The Eastern Cape', 'The Eastern Cape'),
    ('The Free State', 'The Free State'),
    ('Gauteng', 'Gauteng'),
    ('KwaZulu-Natal', 'KwaZulu-Natal'),
    ('Limpopo', 'Limpopo'),
    ('Mpumalanga', 'Mpumalanga'),
    ('The Northern Cape', 'The Northern Cape'),
    ('North West', 'North West'),
    ('The Western Cape', 'The Western Cape'),
]


class ActorManager(models.Manager):

    def ehps(self):
        return super(ActorManager, self).get_queryset().filter(role=EHP)

    def case_investigators(self):
        return super(ActorManager, self).get_queryset().filter(
            role=CASE_INVESTIGATOR)

    def mis(self):
        return super(ActorManager, self).get_queryset().filter(
            role=MIS)

    def managers(self):
        return super(ActorManager, self).get_queryset().exclude(role=EHP)

    def district(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_DISTRICT)

    def provincial(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_PROVINCIAL)

    def national(self):
        return super(
            ActorManager, self).get_queryset().filter(role=MANAGER_NATIONAL)


class SMS(models.Model):
    """
    An SMS sent from the system, for audit trail purposes.
    """
    to = models.CharField(max_length=255)
    content = models.CharField(max_length=255)
    message_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Email(models.Model):
    """
    An Email sent from the system, for audit trail purposes.
    """
    to = models.CharField(max_length=255)
    html_content = models.TextField()
    pdf_content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Facility(models.Model):
    facility_code = models.CharField(max_length=255)
    facility_name = models.CharField(max_length=255, null=True, blank=True)
    province = models.CharField(
        max_length=255, null=True, blank=True, choices=PROVINCES)
    district = models.CharField(max_length=255, null=True, blank=True)
    subdistrict = models.CharField(max_length=255, null=True, blank=True)
    phase = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Facility'
        verbose_name_plural = 'Facilities'

    def __unicode__(self):
        return u'%s - %s' % (self.facility_code, self.facility_name)

    def to_dict(self):
        return {
            'facility_code': self.facility_code,
            'facility_name': self.facility_name,
            'province': self.province,
            'district': self.district,
            'subdistrict': self.subdistrict,
            'phase': self.phase,
        }


class Actor(models.Model):
    """
    An Actor within the system with a defined role.
    """
    name = models.CharField(max_length=255)
    email_address = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=255, null=True, blank=True)
    facility_code = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(choices=[
        (EHP, 'EHP'),
        (CASE_INVESTIGATOR, 'Case Investigator'),
        (MANAGER_DISTRICT, 'District Manager'),
        (MANAGER_PROVINCIAL, 'Provincial Manager'),
        (MANAGER_NATIONAL, 'National Manager'),
        (MIS, 'MIS'),
    ], null=True, max_length=255)
    province = models.CharField(
        max_length=255, null=True, blank=True, choices=PROVINCES)
    district = models.CharField(
        max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActorManager()

    def __unicode__(self):
        return u'%s (%s)' % (self.name, self.role)


class InboundSMS(models.Model):
    """
    An SMS sent to the system.
    """
    message_id = models.UUIDField(primary_key=True)
    sender = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField("sent at")
    created_at = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('SMS', null=True)


class SMSEvent(models.Model):
    """
    An event for a message sent from the system.
    """
    event_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    sms = models.ForeignKey('SMS')


def new_case_alert_jembi(sender, instance, created, **kwargs):
    if not created:
        return

    alert_jembi(instance)


def new_case_alert_ehps(sender, instance, created, **kwargs):
    if not created:
        return

    alert_ehps(instance)


def new_case_alert_case_investigators(sender, instance, created, **kwargs):
    if not created:
        return

    alert_case_investigators(instance)


def new_case_alert_mis(sender, instance, created, **kwargs):
    if not created:
        return

    alert_case_mis(instance)


def alert_jembi(reported_case):
    from malaria24.ona.tasks import compile_and_send_jembi

    compile_and_send_jembi.delay(reported_case.pk)


def alert_ehps(reported_case):
    from malaria24.ona.tasks import send_sms, send_case_email
    ehps = Actor.objects.ehps().filter(
        facility_code=reported_case.facility_code)
    if not ehps.exists():
        logging.warning('No EHPs found for facility code %s.' % (
            reported_case.facility_code,))

    sms_copy = ('New Case: %(case_number)s '
                '%(facility_name)s, %(first_name)s '
                '%(last_name)s, %(locality)s, '
                '%(landmark)s, %(landmark_description)s, age %(age)d, '
                '%(gender)s, phone: %(msisdn)s') % {
        'case_number': reported_case.case_number,
        'facility_name': reported_case.facility_names,
        'first_name': reported_case.first_name,
        'last_name': reported_case.last_name,
        'locality': reported_case.locality,
        'landmark': reported_case.landmark,
        'landmark_description': reported_case.landmark_description,
        'age': reported_case.age,
        'gender': reported_case.gender,
        'msisdn': reported_case.msisdn}

    for ehp in ehps:
        reported_case.ehps.add(ehp)
        if ehp.phone_number and ehp.email_address:
            send_sms.delay(to=ehp.phone_number, content=sms_copy)
            send_case_email.delay(reported_case.pk, [ehp.email_address])
        elif ehp.phone_number:
            send_sms.delay(to=ehp.phone_number, content=sms_copy)
            logging.warning(
                ('Unable to Email report for case %s to %s. '
                 'Missing email_address.') % (
                    reported_case.case_number,
                    ehp))

        elif ehp.email_address:
            send_case_email.delay(reported_case.pk, [ehp.email_address])
            logging.warning(
                ('Unable to SMS report for case %s to %s. '
                 'Missing phone_number.') % (
                    reported_case.case_number,
                    ehp))

    if reported_case.reported_by:
        send_sms.delay(to=reported_case.reported_by,
                       content=('Your reported case for %s %s has been '
                                'assigned case number %s.' % (
                                    reported_case.first_name,
                                    reported_case.last_name,
                                    reported_case.case_number,)))
    else:
        logging.warning(
            ('Unable to SMS case number for case %s. '
             'Missing reported_by.') % (reported_case.case_number,))


def alert_case_investigators(reported_case):
    from malaria24.ona.tasks import send_sms
    case_investigators = Actor.objects.case_investigators().filter(
        facility_code=reported_case.facility_code)

    if not case_investigators.exists():
        logging.warning(
            'No Case Investigators found for facility code %s.' % (
                reported_case.facility_code,))

    for case_investigator in case_investigators:
        if case_investigator.phone_number:
            send_sms.delay(
                to=case_investigator.phone_number,
                content=(
                    'New Case: %(case_number)s '
                    '%(facility_name)s, %(first_name)s '
                    '%(last_name)s, %(locality)s, '
                    '%(landmark)s, %(landmark_description)s, age %(age)d, '
                    '%(gender)s, phone: %(msisdn)s')
                % {
                    'case_number': reported_case.case_number,
                    'facility_name': reported_case.facility_names,
                    'first_name': reported_case.first_name,
                    'last_name': reported_case.last_name,
                    'locality': reported_case.locality,
                    'landmark': reported_case.landmark,
                    'landmark_description': reported_case.landmark_description,
                    'age': reported_case.age,
                    'gender': reported_case.gender,
                    'msisdn': reported_case.msisdn,
                })
        else:
            logging.warning(
                ('Unable to SMS report for case %s to %s. '
                 'Missing phone_number.') % (
                    reported_case.case_number,
                    case_investigator))


def alert_case_mis(reported_case):
    from malaria24.ona.tasks import send_case_email
    facilities = reported_case.get_facilities()
    provinces = set([facility.province for facility in facilities])
    mis_set = Actor.objects.mis().filter(
        province__in=provinces).values_list(
            'name', 'role', 'email_address').distinct()

    if not mis_set:
        logging.warning(
            'No MIS found for facility code %s.' % (
                reported_case.facility_code,))

    for name, role, email in mis_set:
        if email:
            send_case_email.delay(
                reported_case.pk, [email])

        else:
            logging.warning(
                ('Unable to Email report for case %s to %s (%s). '
                 'Missing email_address.') % (
                    reported_case.case_number,
                    name, role))


post_save.connect(new_case_alert_ehps, sender=ReportedCase)
post_save.connect(new_case_alert_case_investigators, sender=ReportedCase)
post_save.connect(new_case_alert_mis, sender=ReportedCase)
post_save.connect(new_case_alert_jembi, sender=ReportedCase)
