from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models


def tagc_today():
    return datetime.now(ZoneInfo("Asia/Manila")).date()


class Gender(models.TextChoices):
    FEMALE = "female", "Female"
    MALE = "male", "Male"


class Member(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DECEASED = "deceased", "Deceased"
        OTHER = "other", "Other"

    class ApplicationType(models.TextChoices):
        NEW = "new", "New"
        CHANGE = "change", "Change of Details"

    class Housing(models.TextChoices):
        OWNED = "owned", "Owned / mortgaged"
        RENTED = "rented", "Rented"
        OTHER = "other", "Other"

    class CivilStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        WIDOWED = "widowed", "Widowed"
        SEPARATED = "separated", "Separated"
        OTHER = "other", "Other"

    family_name = models.CharField(max_length=100)
    status = models.CharField(max_length=8, choices=Status, default=Status.ACTIVE, blank=True)
    status_details = models.CharField(max_length=200, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    suffix = models.CharField(max_length=30, blank=True)
    gender = models.CharField(max_length=6, choices=Gender, blank=True)
    birth_date = models.DateField("date of birth", null=True, blank=True)
    birth_place = models.CharField("place of birth (city / municipality, province)", max_length=200, blank=True)
    citizenship = models.CharField(max_length=100, blank=True)
    civil_status = models.CharField(max_length=10, choices=CivilStatus, blank=True)
    wedding_anniversary = models.DateField(null=True, blank=True)
    street_address = models.CharField("House No /Street /Barangay", max_length=255, blank=True)
    city = models.CharField("city / municipality", max_length=120, blank=True)
    province = models.CharField(max_length=120, blank=True)
    housing_status = models.CharField(max_length=6, choices=Housing, blank=True)
    contact_numbers = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    education = models.CharField("educational attainment / course", max_length=200, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    employer = models.CharField("company / business name", max_length=200, blank=True)
    work_address = models.CharField("work address (city / municipality, province)", max_length=200, blank=True)
    father_name = models.CharField("father’s name", max_length=200, blank=True)
    mother_name = models.CharField("mother’s name", max_length=200, blank=True)
    spouse_family_name = models.CharField(max_length=100, blank=True)
    spouse_first_name = models.CharField(max_length=100, blank=True)
    spouse_middle_name = models.CharField(max_length=100, blank=True)
    spouse_birth_date = models.DateField("spouse’s date of birth", null=True, blank=True)
    spiritual_birthday = models.DateField(null=True, blank=True)
    baptized = models.BooleanField(null=True, blank=True)
    baptism_date = models.DateField(null=True, blank=True)
    baptism_place = models.CharField("place of baptism", max_length=200, blank=True)
    care_group = models.CharField(max_length=150, blank=True)
    current_ministry = models.CharField("current ministry involvement", max_length=200, blank=True)
    auxiliary = models.CharField(max_length=150, blank=True)
    spiritual_gift = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=150, blank=True)
    primary_ministry = models.CharField(max_length=200, blank=True)
    secondary_ministry = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    excel_profile_values = models.JSONField(default=dict, blank=True)
    first_visit_date = models.DateField("Date First Visited/Joined TAGC Services", null=True, blank=True)
    discovery_sources = models.JSONField(default=list, blank=True)
    discovery_details = models.TextField("how the member came to know TAGC", blank=True)
    ministry_interests = models.JSONField(default=list, blank=True)
    music_art_details = models.CharField("music / art details", max_length=200, blank=True)
    other_ministry_interest = models.CharField(max_length=200, blank=True)
    parents_not_members = models.BooleanField("Parents not a member of TAGC", default=False)
    hcdc_beneficiary = models.BooleanField("HCDC Beneficiary", default=False)
    application_date = models.DateField("date of application", null=True, blank=True)
    application_type = models.CharField(max_length=6, choices=ApplicationType, default=ApplicationType.NEW)
    received_by = models.CharField(max_length=150, blank=True)
    received_date = models.DateField("date received", null=True, blank=True)
    signed_form_received = models.BooleanField(default=False)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="membership_record",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["family_name", "first_name", "pk"]

    def __str__(self):
        given_names = " ".join(filter(None, (self.first_name, self.middle_name)))
        return f"{self.family_name}, {given_names}"

    @property
    def member_id(self):
        return f"MBR-{self.pk:04d}" if self.pk is not None else None

    @property
    def profile_completeness(self):
        address_parts = (
            self.street_address, self.city, self.province,
            self.excel_profile_values.get("ADDRESS"),
        )
        fields = {
            "First name": self.first_name,
            "Last name": self.family_name,
            "Gender": self.gender,
            "Date of birth": self.birth_date,
            "Place of birth": self.birth_place,
            "Citizenship": self.citizenship,
            "Civil status": self.civil_status,
            "Address": next((part for part in address_parts if part and part.strip()), None),
            "Housing status": self.housing_status,
            "Email address": self.email,
            "Contact number": self.contact_numbers,
            "Educational attainment": self.education,
            "Occupation": self.occupation,
            "Baptized": self.baptized,
            "Spiritual birthday": self.spiritual_birthday,
            "Joined TAGC": self.first_visit_date,
            "Care group": self.care_group,
            "Current ministry": self.current_ministry,
            "Auxiliary": self.auxiliary,
            "Spiritual gift": self.spiritual_gift,
            "Department": self.department,
            "Primary ministry": self.primary_ministry,
            "Secondary ministry": self.secondary_ministry,
            "Ministry interests": self.ministry_interests or None,
            "How they heard about TAGC": self.discovery_sources or None,
        }
        civil_status = self.civil_status or self.excel_profile_values.get("CIVIL STATUS", "")
        if civil_status.strip().casefold() == self.CivilStatus.MARRIED:
            spouse_name_parts = (
                self.spouse_first_name, self.spouse_family_name, self.spouse_middle_name,
                self.excel_profile_values.get("SPOUSE NAME"),
            )
            fields["Spouse name"] = next((part for part in spouse_name_parts if part and part.strip()), None)
            fields["Wedding date"] = self.wedding_anniversary
        if self.baptized is True:
            fields["Baptism date"] = self.baptism_date
            fields["Place of baptism"] = self.baptism_place

        missing = [
            label for label, value in fields.items()
            if value is None or isinstance(value, str) and not value.strip()
        ]
        total = len(fields)
        return {
            "percent": round(100 * (total - len(missing)) / total),
            "filled": total - len(missing),
            "total": total,
            "missing": missing,
        }

    @property
    def age(self):
        return self._age_on(self.birth_date, tagc_today())

    @property
    def spouse_age(self):
        return self._age_on(self.spouse_birth_date, tagc_today())

    @staticmethod
    def _age_on(birth_date, today):
        if birth_date is None:
            return None
        birthday_pending = (today.month, today.day) < (birth_date.month, birth_date.day)
        return today.year - birth_date.year - int(birthday_pending)


class MemberImportBatch(models.Model):
    checksum = models.CharField(max_length=64, unique=True)


class MemberChild(models.Model):
    member = models.ForeignKey(Member, related_name="children", on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    birth_date = models.DateField("date of birth", null=True, blank=True)
    gender = models.CharField(max_length=6, choices=Gender, blank=True)
    attends_tagc = models.BooleanField("attends TAGC", null=True, blank=True)
    other_church = models.CharField("church attended if outside TAGC", max_length=200, blank=True)

    class Meta:
        ordering = ["pk"]


class MembershipCheck(models.Model):
    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    suggested_member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=320)
    contact_number = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    cleared_for_application = models.BooleanField(
        default=False, help_text="Enable only after checking that no existing membership record matches."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [("review_membershipcheck", "Can review membership requests")]


class StaffNotification(models.Model):
    class Kind(models.TextChoices):
        REGISTRATION = "registration", "New account registered"
        APPLICATION = "application", "New membership application submitted"
        UPDATE = "update", "Membership details updated"
        CHECK = "check", "Membership check requested"

    kind = models.CharField(max_length=12, choices=Kind)
    subject = models.CharField(max_length=320)
    changed_fields = models.JSONField(default=list, blank=True)
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True)
    membership_check = models.ForeignKey(MembershipCheck, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    dismissed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at", "-pk"]


class MemberPhoto(models.Model):
    member = models.OneToOneField(Member, related_name="photo", on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20)
    content = models.BinaryField()
