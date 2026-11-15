from datetime import date, datetime
import re
from zipfile import BadZipFile, ZipFile
from xml.etree.ElementTree import ParseError

from django.core.exceptions import ValidationError
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import Member, tagc_today


MEMBER_IMPORT_COLUMNS = {
    "LAST NAME": "family_name",
    "FIRST NAME": "first_name",
    "MIDDLE NAME": "middle_name",
    "SUFFIX": "suffix",
    "GENDER": "gender",
    "DATE OF BIRTH": "birth_date",
    "PLACE OF BIRTH": "birth_place",
    "CIVIL STATUS": None,
    "SPOUSE NAME": None,
    "WEDDING DATE": "wedding_anniversary",
    "CONTACT NO.": "contact_numbers",
    "EMAIL": "email",
    "ADDRESS": None,
    "AUXILIARY": "auxiliary",
    "CARE GROUP": "care_group",
    "BAPTIZED": "baptized",
    "DATE BAPTIZED": "baptism_date",
    "SPIRITUAL BIRTHDAY": "spiritual_birthday",
    "JOINED TAGC": None,
    "OCCUPATION": "occupation",
    "EDUCATION": "education",
    "SPIRITUAL GIFT": "spiritual_gift",
    "DEPARTMENT": "department",
    "PRIMARY MINISTRY": "primary_ministry",
    "SECONDARY MINISTRY": "secondary_ministry",
    "STATUS": None,
    "NOTES": "notes",
}
MEMBER_IMPORT_HEADERS = tuple(MEMBER_IMPORT_COLUMNS)
FIELD_IMPORT_HEADERS = {
    field: header for header, field in MEMBER_IMPORT_COLUMNS.items() if field is not None
}
NON_IMPORT_FIELDS = {
    field.name for field in Member._meta.fields if field.name not in FIELD_IMPORT_HEADERS
}
MEMBER_IMPORT_TEXT_HEADERS = {
    header for header, field in MEMBER_IMPORT_COLUMNS.items() if field is None
} | {"CONTACT NO."}
MEMBER_IMPORT_DATE_HEADERS = {
    "DATE OF BIRTH", "WEDDING DATE", "DATE BAPTIZED", "SPIRITUAL BIRTHDAY",
}
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 5000
LEGACY_HEADERS = {"MEMBER ID", "AGE", "AGE GROUP"}


def import_member_row(headers, cells):
    member = Member()
    for header, cell in zip(headers, cells):
        if header not in MEMBER_IMPORT_COLUMNS:
            continue
        value = cell.value
        if value is None or isinstance(value, str) and not value.strip():
            continue
        if cell.data_type in {"f", "e"}:
            raise ValidationError(f"{header}: Enter a value instead of a formula or Excel error.")
        field = MEMBER_IMPORT_COLUMNS[header]
        if field is None:
            if isinstance(value, datetime) and value.time() == datetime.min.time():
                value = value.date()
            member.excel_profile_values[header] = str(value)
            continue
        if header in MEMBER_IMPORT_DATE_HEADERS:
            if isinstance(value, datetime):
                value = value.date()
            if not isinstance(value, date):
                text = str(value).strip()
                month_first = re.fullmatch(r"([0-9]{1,2})([/-])([0-9]{1,2})\2([0-9]{4})", text)
                try:
                    if month_first:
                        month, _, day, year = month_first.groups()
                        value = date(int(year), int(month), int(day))
                    else:
                        value = date.fromisoformat(text)
                except ValueError:
                    raise ValidationError(f"{header}: Enter a valid date, such as 03/11/1991.") from None
            if field == "birth_date" and value > tagc_today():
                raise ValidationError(f"{header}: Enter a date on or before today.")
        elif field == "baptized":
            baptism_values = {"yes": True, "no": False, "true": True, "false": False}
            value = baptism_values.get(str(value).strip().lower())
            if value is None:
                raise ValidationError(f"{header}: Enter Yes or No.")
        else:
            value = str(value).strip()
            if field == "gender":
                value = value.lower()
        setattr(member, field, value)

    # Excel status is display data. Staff set the operational status separately.
    member.status = ""
    member.clean_fields(exclude=NON_IMPORT_FIELDS)
    return member


def read_member_workbook(upload):
    try:
        with ZipFile(upload) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 32 * 1024 * 1024:
                raise ValidationError("The expanded workbook is too large.")
        upload.seek(0)
        workbook = load_workbook(upload, read_only=True, keep_links=False)
        try:
            if len(workbook.worksheets) != 1:
                raise ValidationError("Use an Excel workbook with one worksheet.")
            sheet = workbook.worksheets[0]
            sheet.reset_dimensions()
            rows = sheet.iter_rows(max_col=len(MEMBER_IMPORT_HEADERS) + len(LEGACY_HEADERS) + 1)
            headers = [str(cell.value or "").strip().upper() for cell in next(rows, ())]
            used_headers = [header for header in headers if header]
            if (
                not {"LAST NAME", "FIRST NAME"} <= set(used_headers)
                or len(used_headers) != len(set(used_headers))
                or set(used_headers) - (MEMBER_IMPORT_COLUMNS.keys() | LEGACY_HEADERS)
            ):
                raise ValidationError("Use the template headers and include LAST NAME and FIRST NAME.")

            members, errors = [], []
            for row_number, cells in enumerate(rows, start=2):
                if row_number > MAX_IMPORT_ROWS + 1:
                    raise ValidationError(f"Use up to {MAX_IMPORT_ROWS:,} rows per workbook.")
                if not any(cell.value is not None and str(cell.value).strip() for cell in cells):
                    continue
                try:
                    members.append((row_number, import_member_row(headers, cells)))
                except ValidationError as error:
                    if hasattr(error, "message_dict"):
                        for field, messages in error.message_dict.items():
                            header = FIELD_IMPORT_HEADERS[field]
                            errors.extend(f"Row {row_number}, {header}: {message}" for message in messages)
                    else:
                        errors.extend(f"Row {row_number}: {message}" for message in error.messages)
                    if len(errors) >= 30:
                        break
            if not members and not errors:
                raise ValidationError("Enter at least one member below the headers.")
            return members, errors
        finally:
            workbook.close()
    except (BadZipFile, InvalidFileException, KeyError, OSError, ParseError, ValueError) as error:
        raise ValidationError("The workbook could not be read. Save it as an .xlsx file and try again.") from error
