from collections import defaultdict

from .models import Member


def member_name_key(first_name, family_name):
    return tuple(" ".join(name.casefold().split()) for name in (first_name, family_name))


def existing_members_by_name(names):
    matches = defaultdict(dict)
    existing = Member.objects.order_by("pk").only("first_name", "family_name", "birth_date")
    for member in existing.iterator():
        name = member_name_key(member.first_name, member.family_name)
        if name in names:
            matches[name].setdefault(member.birth_date, member.member_id)
    return matches


def match_birth_date(matches, birth_date):
    if birth_date is None:
        return next(iter(matches.values()), None)
    return matches.get(birth_date) or matches.get(None)


def find_duplicate_member(first_name, family_name, birth_date):
    name = member_name_key(first_name, family_name)
    return match_birth_date(existing_members_by_name({name})[name], birth_date)


def duplicate_member_rows(rows):
    upload_names = {member_name_key(member.first_name, member.family_name) for _, member in rows}
    existing_by_name = existing_members_by_name(upload_names)
    upload_by_name = defaultdict(dict)
    errors = []
    for row_number, member in rows:
        name = member_name_key(member.first_name, member.family_name)
        birth_date = member.birth_date
        existing_id = match_birth_date(existing_by_name[name], birth_date)
        previous_row = match_birth_date(upload_by_name[name], birth_date)
        if existing_id:
            match = f"existing member {existing_id}"
        elif previous_row:
            match = f"row {previous_row} in this workbook"
        else:
            match = None
        if match:
            errors.append(f"Row {row_number}: Possible duplicate of {match}. Review the member before importing.")
        upload_by_name[name].setdefault(birth_date, row_number)
        if len(errors) == 30:
            errors.append("Review these possible duplicates and try again to check the remaining rows.")
            break
    return errors
