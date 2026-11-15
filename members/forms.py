from django import forms
from django.forms import inlineformset_factory
from django.forms.utils import pretty_name

from .duplicates import find_duplicate_member
from .models import Gender, Member, MemberChild, MembershipCheck, tagc_today


MINISTRY_INTERESTS = (
    "Administrative", "Children", "Choir", "Church Beautification", "Dancing / Acting",
    "Discipleship", "Evangelism", "Family Life", "Hospitality", "Jail Ministry",
    "Maintenance/Landscaping", "Missions", "Music/Art", "Outreach", "Web/Technology",
    "Writing Composition", "Youth", "Others",
)

FORM_SECTIONS = (
    ("Personal details", (
        "family_name", "first_name", "middle_name", "suffix", "gender", "birth_date", "birth_place",
        "citizenship", "civil_status", "wedding_anniversary", "photo",
    )),
    ("Address, contact, education and work", (
        "street_address", "city", "province", "housing_status", "contact_numbers", "email",
        "education", "occupation", "employer", "work_address",
    )),
    ("Family", (
        "father_name", "mother_name", "spouse_family_name", "spouse_first_name",
        "spouse_middle_name", "spouse_birth_date",
    )),
    ("Church involvement", (
        "spiritual_birthday", "baptized", "baptism_date", "baptism_place", "care_group",
        "current_ministry", "auxiliary", "spiritual_gift", "department", "primary_ministry",
        "secondary_ministry", "first_visit_date", "discovery_sources", "discovery_details",
    )),
    ("Ministry interests", ("ministry_interests", "music_art_details", "other_ministry_interest")),
    ("Application and remarks", (
        "application_type", "application_date",
        "signed_form_received", "parents_not_members", "hcdc_beneficiary", "notes",
    )),
)


PROFILE_SECTIONS = (
    ("Personal background", (
        "birth_date", "birth_place", "citizenship", "gender", "civil_status", "wedding_anniversary",
    )),
    ("Contact and home address", (
        "contact_numbers", "email", "street_address", "city", "province", "housing_status",
    )),
    ("Education and work", ("education", "occupation", "employer", "work_address")),
    ("Church involvement", (
        "first_visit_date", "discovery_sources", "discovery_details", "spiritual_birthday", "baptized",
        "baptism_date", "baptism_place", "care_group", "current_ministry", "auxiliary",
        "spiritual_gift", "department", "primary_ministry", "secondary_ministry",
    )),
    ("Ministry interests", ("ministry_interests", "music_art_details", "other_ministry_interest")),
)


class DateInput(forms.DateInput):
    input_type = "date"


def profile_title(text):
    lowercase_words = {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
    return " ".join(
        word if index and word in lowercase_words else word[:1].upper() + word[1:]
        for index, word in enumerate(text.split())
    )

    def __init__(self):
        super().__init__(format="%Y-%m-%d")


class DirectoryFilterForm(forms.Form):
    saved_value_fields = {
        "city": "City / municipality",
        "province": "Province",
        "care_group": "Care group",
        "current_ministry": "Current ministry",
    }
    spiritual_birthday = forms.ChoiceField(label="Spiritual Birthday", required=False)
    baptized = forms.ChoiceField(
        label="Baptized",
        required=False,
        choices=(("", "Any status"), ("yes", "Yes"), ("no", "No"), ("unknown", "Not recorded")),
    )
    gender = forms.ChoiceField(required=False, choices=(("", "Any gender"), *Gender.choices))
    civil_status = forms.ChoiceField(required=False, choices=(("", "Any status"), *Member.CivilStatus.choices))
    status = forms.ChoiceField(
        label="Status", required=False, choices=(("", "Any status"), ("not_set", "Not set"), *Member.Status.choices),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dates = Member.objects.exclude(spiritual_birthday__isnull=True).order_by(
            "-spiritual_birthday"
        ).values_list("spiritual_birthday", flat=True).distinct()
        self.fields["spiritual_birthday"].choices = [
            ("", "Any date"), ("none", "None"),
            *((day.isoformat(), f"{day:%b %d, %Y}") for day in dates),
        ]
        for name, label in self.saved_value_fields.items():
            values = Member.objects.exclude(**{name: ""}).order_by(name).values_list(name, flat=True).distinct()
            self.fields[name] = forms.ChoiceField(
                label=label, required=False, choices=[("", "Any"), *((value, value) for value in values)],
            )

class MemberStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Member.Status.choices)
    status_details = forms.CharField(required=False, max_length=200)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Member.Status.OTHER:
            if not cleaned.get("status_details") and "status_details" not in self.errors:
                self.add_error("status_details", "Enter an explanation for Other.")
        else:
            cleaned["status_details"] = ""
        return cleaned


class MemberDuplicateCheckForm(forms.ModelForm):
    check_duplicates = True

    def clean(self):
        cleaned = super().clean()
        first_name = cleaned.get("first_name")
        family_name = cleaned.get("family_name")
        if self.check_duplicates and self.instance._state.adding and first_name and family_name and "birth_date" in cleaned:
            existing_id = find_duplicate_member(first_name, family_name, cleaned["birth_date"])
            if existing_id:
                self.add_error(None, f"Possible duplicate of existing member {existing_id}. Review that record before adding a new member.")
        return cleaned


class MemberForm(MemberDuplicateCheckForm):
    photo = forms.ImageField(
        label="Member photo",
        required=False,
        help_text="Upload a JPEG or PNG up to 2 MiB. Leave blank to keep the current photo.",
    )
    ministry_interests = forms.MultipleChoiceField(
        choices=[(name, name) for name in MINISTRY_INTERESTS],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    discovery_sources = forms.ChoiceField(
        label="How they heard about TAGC",
        choices=[(name, name) for name in ("Invited", "Social Media", "Referred", "Other")],
        required=False,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Member
        fields = [
            name for _, names in FORM_SECTIONS for name in names
            if name not in {"application_type", "signed_form_received"}
        ]
        labels = {"discovery_details": "How did you hear about TAGC?"}
        widgets = {
            name: DateInput() for name in (
                "birth_date", "wedding_anniversary", "spouse_birth_date", "spiritual_birthday",
                "baptism_date", "first_visit_date", "application_date",
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_address"].label = "Work address"
        self.fields["work_address"].widget.attrs["placeholder"] = "City / municipality, province"
        self.fields["contact_numbers"].label = "Contact number"
        sources = self.initial.get("discovery_sources") or []
        self.initial["discovery_sources"] = (
            "Other" if self.initial.get("discovery_details") else next(iter(sources), "")
        )

    def clean_discovery_sources(self):
        source = self.cleaned_data["discovery_sources"]
        return [source] if source else []

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo is None:
            return None
        if photo.size > 2 * 1024 * 1024 or photo.image.width * photo.image.height > 20_000_000:
            raise forms.ValidationError("Use an image up to 2 MiB and 20 megapixels.")
        if photo.image.format not in {"JPEG", "PNG"}:
            raise forms.ValidationError("Upload a JPEG or PNG image.")
        return photo

    def clean(self):
        cleaned = super().clean()
        sources = cleaned.get("discovery_sources")
        if sources is not None:
            if "Other" not in sources:
                cleaned["discovery_details"] = ""
            elif not cleaned.get("discovery_details"):
                self.add_error("discovery_details", "Enter how you heard about TAGC.")
        today = tagc_today()
        for field in ("birth_date", "spouse_birth_date"):
            value = cleaned.get(field)
            if value and value > today:
                self.add_error(field, "Enter a date of birth on or before today.")
        return cleaned

    def sections(self):
        return [(title, [self[name] for name in names if name in self.fields]) for title, names in FORM_SECTIONS]

    def record_sections(self, groups=FORM_SECTIONS, *, labels=None):
        imported_fields = {
            "street_address": ("ADDRESS", "Address"),
            "spouse_family_name": ("SPOUSE NAME", "Spouse name"),
            "first_visit_date": ("JOINED TAGC", "Joined TAGC"),
            "civil_status": ("CIVIL STATUS", "Civil status"),
        }
        sections = []
        for title, names in groups:
            rows = []
            for name in names:
                if name == "photo":
                    continue
                value = getattr(self.instance, name)
                display = getattr(self.instance, f"get_{name}_display", None)
                if display:
                    value = display()
                elif isinstance(value, list):
                    value = ", ".join(value)
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                if not value and name in imported_fields:
                    column, label = imported_fields[name]
                    imported = self.instance.excel_profile_values.get(column)
                    if imported:
                        rows.append((label, imported))
                if value:
                    field = self.fields.get(name)
                    label = field.label if field else self.instance._meta.get_field(name).verbose_name.capitalize()
                    rows.append((profile_title((labels or {}).get(name, label or pretty_name(name))), value))
                if name in ("birth_date", "spouse_birth_date") and value:
                    age = self.instance.age if name == "birth_date" else self.instance.spouse_age
                    rows.append(("Age" if name == "birth_date" else "Spouse’s age", age))
            sections.append((profile_title(title), rows))
        return sections


class SelfServiceMemberForm(MemberForm):
    check_duplicates = False

    class Meta(MemberForm.Meta):
        fields = [
            name for name in MemberForm.Meta.fields
            if name != "notes"
        ]


class MembershipCheckForm(forms.ModelForm):
    class Meta:
        model = MembershipCheck
        fields = ("full_name", "contact_number", "email")
        labels = {"email": "Email address (optional)"}
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "contact_number": forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }


class ChildForm(forms.ModelForm):
    class Meta:
        model = MemberChild
        fields = ("name", "birth_date", "gender", "attends_tagc", "other_church")
        labels = {"other_church": "Other church attended"}
        widgets = {"birth_date": DateInput()}

    def clean_birth_date(self):
        value = self.cleaned_data["birth_date"]
        if value and value > tagc_today():
            raise forms.ValidationError("Enter a date of birth on or before today.")
        return value


ChildrenFormSet = inlineformset_factory(
    Member, MemberChild, form=ChildForm, extra=0, max_num=50, validate_max=True, can_delete=False,
)
