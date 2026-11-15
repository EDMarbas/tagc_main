from calendar import monthrange
from collections import Counter
from hashlib import sha256
from io import BytesIO
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_safe, require_http_methods
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .duplicates import duplicate_member_rows
from .forms import PROFILE_SECTIONS, ChildrenFormSet, DirectoryFilterForm, MemberForm, MembershipCheckForm, MemberStatusForm, SelfServiceMemberForm
from .imports import (
    MAX_IMPORT_BYTES, MEMBER_IMPORT_DATE_HEADERS, MEMBER_IMPORT_HEADERS,
    MEMBER_IMPORT_TEXT_HEADERS, read_member_workbook,
)
from .models import Member, MemberImportBatch, MemberPhoto, MembershipCheck, StaffNotification, tagc_today


@require_safe
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def directory(request):
    members = Member.objects.all()
    query = request.GET.get("q", "").strip()[:320]
    today = tagc_today()

    def birthday_cutoff(years_ago):
        year = today.year - years_ago
        day = min(today.day, monthrange(year, today.month)[1])
        return today.replace(year=year, day=day)

    for word in query.replace(",", " ").split():
        matches = (
            Q(first_name__icontains=word) | Q(middle_name__icontains=word) | Q(family_name__icontains=word)
            | Q(contact_numbers__icontains=word) | Q(email__icontains=word)
            | Q(city__icontains=word) | Q(province__icontains=word)
            | Q(care_group__icontains=word) | Q(current_ministry__icontains=word)
        )
        if re.fullmatch(r"MBR-[0-9]{4,18}", word.upper()):
            matches |= Q(pk=int(word[4:]))
        elif re.fullmatch(r"[0-9]{1,3}", word):
            age = int(word)
            matches |= Q(birth_date__gt=birthday_cutoff(age + 1), birth_date__lte=birthday_cutoff(age))
        members = members.filter(matches)

    filters = DirectoryFilterForm(request.GET)
    parameters = request.GET.copy()
    parameters.pop("page", None)
    active_filters = []
    if filters.is_valid():
        for name, field in filters.fields.items():
            value = filters.cleaned_data[name]
            if not value:
                continue
            match = value
            if name == "baptized":
                match = {"yes": True, "no": False, "unknown": None}[value]
            elif name == "spiritual_birthday" and value == "none":
                match = None
            elif name == "status" and value == "not_set":
                match = ""
            members = members.filter(**{name: match})
            remaining = parameters.copy()
            remaining.pop(name, None)
            label = dict(field.choices)[value]
            active_filters.append((f"{field.label}: {label}", remaining.urlencode()))

    page = Paginator(members, 25).get_page(request.GET.get("page"))
    return render(request, "members/directory.html", {
        "page": page, "query": query, "parameters": parameters.urlencode(),
        "filters": filters, "active_filters": active_filters,
        "status_choices": Member.Status.choices,
        "can_edit_status": request.user.is_staff and request.user.has_perm("members.change_member"),
        "return_parameters": request.GET.urlencode(),
    })


@require_POST
@never_cache
@login_required
@permission_required(("members.view_member", "members.change_member"), raise_exception=True)
def update_member_status(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    member = get_object_or_404(Member, pk=pk)
    form = MemberStatusForm(request.POST)
    if form.is_valid():
        Member.objects.filter(pk=member.pk).update(
            **form.cleaned_data, updated_by=request.user, updated_at=timezone.now(),
        )
        messages.success(request, f"Status updated for {member.member_id}.")
    else:
        messages.error(request, " ".join(error for errors in form.errors.values() for error in errors))
    return redirect(reverse("members:directory", query=request.GET))


@require_safe
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return render(request, "members/detail.html", {
        "member": member,
        "sections": MemberForm(instance=member).record_sections(labels={"birth_place": "Place of Birth"}),
        "has_photo": MemberPhoto.objects.filter(member=member).exists(),
    })


@require_safe
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def photo(request, pk):
    return member_photo_response(get_object_or_404(MemberPhoto, member_id=pk))


@require_safe
@never_cache
@login_required
def my_membership_photo(request):
    image = get_object_or_404(MemberPhoto, member__account=request.user)
    return member_photo_response(image)


def member_photo_response(image):
    response = HttpResponse(image.content, content_type=image.content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_safe
@never_cache
@login_required
@permission_required(("members.view_member", "members.add_member"), raise_exception=True)
def download_member_import_template(request):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Members"
    sheet.append(MEMBER_IMPORT_HEADERS)
    sheet.freeze_panes = "C2"
    sheet.row_dimensions[1].height = 24
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="14245C")
    header_alignment = Alignment(vertical="center")

    for column, header in enumerate(MEMBER_IMPORT_HEADERS, start=1):
        heading = sheet.cell(row=1, column=column)
        heading.font = header_font
        heading.fill = header_fill
        heading.alignment = header_alignment
        sheet.column_dimensions[get_column_letter(column)].width = (
            36 if header in {"ADDRESS", "NOTES"} else max(18, len(header) + 4)
        )

        number_format = "General"
        if header in MEMBER_IMPORT_TEXT_HEADERS:
            number_format = "@"
        elif header in MEMBER_IMPORT_DATE_HEADERS:
            number_format = "mm/dd/yyyy"

        for row in range(2, 502):
            sheet.cell(row=row, column=column).number_format = number_format

    with BytesIO() as output:
        workbook.save(output)
        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    response["Content-Disposition"] = 'attachment; filename="TAGC_Member_Upload_Template.xlsx"'
    return response


@require_POST
@never_cache
@login_required
@permission_required(("members.view_member", "members.add_member"), raise_exception=True)
def bulk_import_members(request):
    upload = request.FILES.get("workbook")
    try:
        if upload is None or not upload.name.lower().endswith(".xlsx"):
            raise ValidationError("Choose an .xlsx workbook.")
        if upload.size > MAX_IMPORT_BYTES:
            raise ValidationError("Choose a workbook of 5 MB or less.")

        checksum = sha256()
        for chunk in upload.chunks():
            checksum.update(chunk)
        upload.seek(0)
        rows, errors = read_member_workbook(upload)
        if errors:
            raise ValidationError(errors)

        with transaction.atomic():
            _, created = MemberImportBatch.objects.get_or_create(checksum=checksum.hexdigest())
            if not created:
                raise ValidationError("This exact workbook was already imported.")
            duplicates = duplicate_member_rows(rows)
            if duplicates:
                raise ValidationError(duplicates)
            members = [member for _, member in rows]
            for member in members:
                member.created_by = request.user
                member.updated_by = request.user
            Member.objects.bulk_create(members, batch_size=200)
    except ValidationError as error:
        return render(request, "members/import_errors.html", {"errors": error.messages}, status=400)

    messages.success(request, f"Imported {len(members):,} member(s).")
    return redirect("members:directory")


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
@permission_required(("members.view_member", "members.add_member"), raise_exception=True)
def add(request):
    return member_form(request, Member())


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
@permission_required(("members.view_member", "members.change_member"), raise_exception=True)
def edit(request, pk):
    return member_form(request, get_object_or_404(Member, pk=pk))


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
def my_membership(request):
    member = Member.objects.filter(account=request.user).first()
    membership_check = MembershipCheck.objects.filter(account=request.user).first() if not member else None
    form = MembershipCheckForm(request.POST if request.method == "POST" else None)
    candidate_token = request.POST.get("candidate", "")
    if request.method == "POST":
        if member or membership_check:
            return redirect("members:my_membership")
        if form.is_valid():
            candidate = None
            if candidate_token:
                try:
                    account_id, candidate_id = signing.loads(candidate_token, salt="membership-check", max_age=3600)
                except signing.BadSignature:
                    account_id, candidate_id = None, None
                if account_id == request.user.pk:
                    candidate = Member.objects.filter(pk=candidate_id, account__isnull=True).first()
                if candidate is None:
                    form.add_error(None, "That selection is no longer available. Search again or send a request without selecting a record.")
                    candidate_token = ""
        if form.is_valid():
            with transaction.atomic():
                membership_check, created = MembershipCheck.objects.get_or_create(
                    account=request.user, defaults={**form.cleaned_data, "suggested_member": candidate},
                )
                if created:
                    StaffNotification.objects.create(
                        kind=StaffNotification.Kind.CHECK, subject=membership_check.full_name,
                        membership_check=membership_check,
                    )
            return redirect("members:my_membership")
    query = request.GET.get("name", "").strip()[:320]
    candidates = []
    page = None
    can_start_application = False
    if query and not member and not membership_check:
        matches = Member.objects.filter(account__isnull=True).only("first_name", "middle_name", "family_name")
        for word in query.replace(",", " ").split():
            matches = matches.filter(
                Q(first_name__icontains=word) | Q(middle_name__icontains=word) | Q(family_name__icontains=word)
            )
        if query.replace(",", " ").split():
            page = Paginator(matches, 25).get_page(request.GET.get("page"))
            candidates = [
                (str(match), signing.dumps((request.user.pk, match.pk), salt="membership-check"))
                for match in page
            ]
            can_start_application = page.paginator.count == 0
            if can_start_application:
                request.session["membership_no_match_account"] = request.user.pk
            else:
                request.session.pop("membership_no_match_account", None)
    return render(request, "members/my_membership.html", {
        "member": member, "membership_check": membership_check, "check_form": form,
        "has_photo": bool(member and MemberPhoto.objects.filter(member=member).exists()),
        "profile_sections": (
            SelfServiceMemberForm(instance=member).record_sections(PROFILE_SECTIONS, labels={"birth_place": "Place of birth"})
            if member else []
        ),
        "query": query, "candidates": candidates, "search_page": page, "candidate_token": candidate_token,
        "can_start_application": can_start_application,
    })


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
def my_membership_apply(request):
    if Member.objects.filter(account=request.user).exists():
        return redirect("members:my_membership")
    check = MembershipCheck.objects.filter(account=request.user).first()
    can_apply = (
        check.cleared_for_application if check
        else request.session.get("membership_no_match_account") == request.user.pk
    )
    if not can_apply:
        return redirect("members:my_membership")
    try:
        return member_form(request, Member(account=request.user), self_service=True)
    except IntegrityError:
        if Member.objects.filter(account=request.user).exists():
            return redirect("members:my_membership")
        raise


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
def my_membership_edit(request):
    member = get_object_or_404(Member, account=request.user)
    return member_form(request, member, self_service=True)


@require_safe
@never_cache
@login_required
@permission_required("members.review_membershipcheck", raise_exception=True)
def verification_queue(request):
    checks = MembershipCheck.objects.select_related("account__membership_record")
    show_all = request.GET.get("status") == "all"
    if not show_all:
        checks = checks.filter(cleared_for_application=False, account__membership_record__isnull=True)
    page = Paginator(checks.order_by("-created_at", "-pk"), 25).get_page(request.GET.get("page"))
    return render(request, "members/verification_queue.html", {"page": page, "show_all": show_all})


@require_http_methods(["GET", "POST", "HEAD"])
@never_cache
@login_required
@permission_required("members.review_membershipcheck", raise_exception=True)
def review_membership_check(request, pk):
    check = get_object_or_404(MembershipCheck.objects.select_related("account", "suggested_member"), pk=pk)
    linked_member = Member.objects.filter(account=check.account).first()
    source = request.POST if request.method == "POST" else request.GET
    member_id = source.get("member_id", "").strip().upper()
    candidate = check.suggested_member if not member_id else None
    if re.fullmatch(r"MBR-[0-9]{4,18}", member_id):
        candidate = Member.objects.filter(pk=int(member_id[4:])).first()
    error = "No member was found for that ID." if member_id and not candidate else ""
    if request.method == "POST":
        action = request.POST.get("action")
        if action not in {"link", "clear"}:
            return HttpResponse(status=400)
        if request.POST.get("confirmed") != "yes":
            error = "Confirm that you completed the verification before saving."
        elif not check.account.is_active:
            error = "This account is inactive."
        elif linked_member:
            error = "This account already has a linked membership."
        elif action == "link" and (not candidate or not member_id):
            error = "Select a member record before linking."
        else:
            try:
                with transaction.atomic():
                    check = MembershipCheck.objects.select_for_update().get(pk=pk)
                    if Member.objects.filter(account_id=check.account_id).exists():
                        error = "This account already has a linked membership."
                    elif action == "link":
                        updated = Member.objects.filter(pk=candidate.pk, account__isnull=True).update(
                            account_id=check.account_id, updated_by=request.user, updated_at=timezone.now(),
                        )
                        if updated:
                            check.cleared_for_application = False
                            check.save(update_fields=["cleared_for_application"])
                        else:
                            error = "That record is already linked or is no longer available."
                    else:
                        check.cleared_for_application = True
                        check.save(update_fields=["cleared_for_application"])
            except IntegrityError:
                error = "The account could not be linked because another link already exists. Refresh and check the record."
            if not error:
                messages.success(request, "Membership linked." if action == "link" else "Account cleared to start a new application.")
                return redirect("members:review_membership_check", pk=pk)
    search = request.GET.get("member_search", "").strip()[:150]
    matches = []
    if search and not linked_member and check.account.is_active:
        available = Member.objects.filter(account__isnull=True)
        if re.fullmatch(r"MBR-[0-9]{4,18}", search.upper()):
            available = available.filter(pk=int(search[4:]))
        else:
            for word in search.replace(",", " ").split():
                available = available.filter(
                    Q(first_name__icontains=word) | Q(middle_name__icontains=word)
                    | Q(family_name__icontains=word)
                )
        if search.replace(",", " ").split():
            matches = list(available.only("first_name", "middle_name", "family_name")[:21])
    return render(request, "members/verification_review.html", {
        "check": check, "candidate": candidate, "linked_member": linked_member,
        "search": search, "matches": matches[:20], "more_matches": len(matches) > 20,
        "error": error,
    })


@require_safe
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def notifications(request):
    read = StaffNotification.objects.filter(pk=OuterRef("pk"), read_by=request.user)
    items = StaffNotification.objects.select_related(
        "member", "membership_check__account", "membership_check__suggested_member",
    ).exclude(dismissed_by=request.user).annotate(is_read=Exists(read))
    page = Paginator(items, 25).get_page(request.GET.get("page"))
    return render(request, "members/notifications.html", {"page": page})


@require_POST
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def mark_notification_read(request, pk):
    notification = get_object_or_404(StaffNotification, pk=pk)
    notification.read_by.add(request.user)
    return redirect("members:notifications")


@require_POST
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def dismiss_notification(request, pk):
    notification = get_object_or_404(StaffNotification, pk=pk)
    notification.dismissed_by.add(request.user)
    return redirect("members:notifications")


def member_form(request, member, *, self_service=False):
    form_class = SelfServiceMemberForm if self_service else MemberForm
    is_new = member.pk is None
    application_type = Member.ApplicationType.NEW if is_new else Member.ApplicationType.CHANGE
    if request.method == "POST":
        previous_discovery_sources = member.discovery_sources
        form = form_class(request.POST, request.FILES, instance=member)
        children = ChildrenFormSet(request.POST, instance=member)
        form_valid = form.is_valid()
        children_valid = children.is_valid()
        if form_valid and children_valid:
            with transaction.atomic():
                member = form.save(commit=False)
                member.application_type = application_type
                if is_new:
                    member.created_by = request.user
                member.updated_by = request.user
                if is_new:
                    member.save(force_insert=True)
                else:
                    records = Member.objects.select_for_update()
                    if self_service:
                        records = records.filter(account=request.user)
                    get_object_or_404(records.only("pk"), pk=member.pk)
                    fields = set(form.changed_data) - {"photo"}
                    if member.discovery_sources != previous_discovery_sources:
                        fields.update({"discovery_sources", "discovery_details"})
                    member.save(update_fields=fields | {"application_type", "updated_by", "updated_at"})
                    records.filter(pk=member.pk, status="").update(status=Member.Status.ACTIVE)
                children.instance = member
                children.save()

                image = form.cleaned_data["photo"]
                if image:
                    image.seek(0)
                    MemberPhoto.objects.update_or_create(
                        member=member,
                        defaults={
                            "content": image.read(),
                            "content_type": "image/jpeg" if image.image.format == "JPEG" else "image/png",
                        },
                    )
                if self_service and is_new:
                    StaffNotification.objects.create(
                        kind=StaffNotification.Kind.APPLICATION, subject=str(member), member=member,
                    )
                elif self_service and (
                    form.has_changed() or children.changed_objects
                    or children.new_objects
                ):
                    changed_fields = [str(form[name].label) for name in form.changed_data]
                    changed_child_fields = {
                        name for _, names in children.changed_objects for name in names
                    }
                    for name, field in children.empty_form.fields.items():
                        if name in changed_child_fields and not field.widget.is_hidden:
                            changed_fields.append(f"Child details: {field.label}")
                    if children.new_objects:
                        changed_fields.append("Child added" if len(children.new_objects) == 1 else "Children added")
                    StaffNotification.objects.create(
                        kind=StaffNotification.Kind.UPDATE, subject=str(member), member=member,
                        changed_fields=changed_fields,
                    )
            if self_service:
                return redirect("members:my_membership")
            return redirect("members:detail", pk=member.pk)
    else:
        form = form_class(instance=member)
        children = ChildrenFormSet(instance=member)

    return render(request, "members/form.html", {
        "form": form, "children": children, "member": member,
        "has_photo": bool(member.pk and MemberPhoto.objects.filter(member=member).exists()),
        "application_type": application_type.label, "self_service": self_service,
    })


@require_safe
@never_cache
@login_required
@permission_required("members.view_member", raise_exception=True)
def summary(request):
    age_groups = dict.fromkeys(("Under 18", "18–29", "30–44", "45–59", "60 and over", "Unknown"), 0)
    care_groups = Counter()
    interests = Counter()
    total = 0
    today = tagc_today()
    for member in Member.objects.only("birth_date", "care_group", "ministry_interests").iterator():
        total += 1
        age = Member._age_on(member.birth_date, today)
        if age is None:
            band = "Unknown"
        elif age < 18:
            band = "Under 18"
        elif age < 30:
            band = "18–29"
        elif age < 45:
            band = "30–44"
        elif age < 60:
            band = "45–59"
        else:
            band = "60 and over"
        age_groups[band] += 1
        care_groups[member.care_group.strip() or "Unspecified"] += 1
        interests.update(set(member.ministry_interests))

    charts = (
        ("Age groups", age_groups.items()),
        ("Care groups", care_groups.most_common()),
        ("Ministry interests", interests.most_common()),
    )
    return render(request, "members/summary.html", {"total": total, "charts": charts})
