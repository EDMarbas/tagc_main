from io import BytesIO
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .forms import ChildrenFormSet
from .models import Member, MembershipCheck


class MemberEntryTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.staff = users.objects.create_superuser("staff", "staff@example.test")
        self.member = users.objects.create_user("member")
        self.client.force_login(self.staff)

    def test_other_discovery_answer_is_required_saved_and_cleared(self):
        member = Member.objects.create(
            first_name="First", family_name="Last", discovery_sources=["Invited", "Referred"],
        )
        edit_url = reverse("members:edit", args=[member.pk])
        prefix = ChildrenFormSet.get_default_prefix()
        data = {
            "first_name": member.first_name, "family_name": member.family_name,
            f"{prefix}-TOTAL_FORMS": "0", f"{prefix}-INITIAL_FORMS": "0",
            "discovery_sources": ["Invited", "Other"],
        }
        self.assertContains(self.client.post(edit_url, data), "Enter how you heard about TAGC.")
        data["discovery_details"] = "Community event"
        detail_url = reverse("members:detail", args=[member.pk])
        self.assertRedirects(self.client.post(edit_url, data), detail_url)
        member.refresh_from_db()
        self.assertEqual(member.discovery_sources, ["Other"])
        self.assertEqual(member.discovery_details, "Community event")
        edit = self.client.get(edit_url)
        self.assertContains(edit, "Community event")
        self.assertContains(edit, 'type="radio" name="discovery_sources"')
        self.assertContains(edit, 'aria-label="Close popup"')
        self.assertNotContains(edit, "Edit other answer")
        data["discovery_sources"] = ["Invited"]
        self.assertRedirects(self.client.post(edit_url, data), detail_url)
        member.refresh_from_db()
        self.assertEqual(member.discovery_details, "")

    def workbook(self, rows):
        workbook = Workbook()
        for row in rows:
            workbook.active.append(row)
        with BytesIO() as output:
            workbook.save(output)
            return output.getvalue()

    def upload(self, workbook):
        return self.client.post(
            reverse("members:bulk_import"),
            {"workbook": SimpleUploadedFile("members.xlsx", workbook)},
        )

    def test_bulk_import_accepts_month_first_and_existing_date_formats(self):
        workbook = self.workbook([
            ["LAST NAME", "FIRST NAME", "DATE OF BIRTH", "WEDDING DATE",
             "DATE BAPTIZED", "SPIRITUAL BIRTHDAY"],
            ["Record", "Excel", "03/11/1991", "06-17-2017", "2010-08-09", date(2010, 7, 4)],
        ])
        self.assertRedirects(self.upload(workbook), reverse("members:directory"))
        member = Member.objects.get()
        self.assertEqual(member.birth_date, date(1991, 3, 11))
        self.assertEqual(member.wedding_anniversary, date(2017, 6, 17))
        self.assertEqual(member.baptism_date, date(2010, 8, 9))
        self.assertEqual(member.spiritual_birthday, date(2010, 7, 4))

    def test_bulk_import_flags_existing_members_and_allows_different_birth_dates(self):
        member = Member.objects.create(first_name="Maria  Luz", family_name="Reyes", birth_date=date(1991, 3, 11))
        headers = ["LAST NAME", "FIRST NAME", "DATE OF BIRTH"]
        matching = self.workbook([headers, ["REYES", "maria luz", "03/11/1991"]])
        self.assertContains(self.upload(matching), f"Possible duplicate of existing member {member.member_id}", status_code=400)
        names_only = self.workbook([headers, ["Reyes", "Maria Luz"]])
        self.assertContains(self.upload(names_only), "Possible duplicate", status_code=400)
        distinct = self.workbook([headers, ["Reyes", "Maria Luz", "03/12/1991"]])
        self.assertRedirects(self.upload(distinct), reverse("members:directory"))
        self.assertEqual(Member.objects.count(), 2)

    def test_bulk_import_flags_duplicates_within_workbook(self):
        workbook = self.workbook([
            ["LAST NAME", "FIRST NAME", "DATE OF BIRTH"],
            ["Reyes", "Maria", "03/11/1991"],
            [None, None, None],
            ["Reyes", "Maria"],
        ])
        self.assertContains(self.upload(workbook), "Row 4: Possible duplicate of row 2", status_code=400)
        self.assertFalse(Member.objects.exists())

    def test_staff_and_admin_add_forms_flag_existing_members(self):
        member = Member.objects.create(first_name="Maria Luz", family_name="Reyes", birth_date=date(1991, 3, 11))
        prefix = ChildrenFormSet.get_default_prefix()
        data = {
            "first_name": "maria  luz", "family_name": "REYES",
            f"{prefix}-TOTAL_FORMS": "0", f"{prefix}-INITIAL_FORMS": "0",
        }
        for url in (reverse("members:add"), reverse("admin:members_member_add")):
            with self.subTest(url=url):
                response = self.client.post(url, data)
                self.assertContains(response, f"Possible duplicate of existing member {member.member_id}")
                self.assertEqual(Member.objects.count(), 1)
        distinct = {**data, "birth_date": "1991-03-12"}
        self.assertEqual(self.client.post(reverse("members:add"), distinct).status_code, 302)
        self.assertEqual(Member.objects.count(), 2)

    def test_admin_delete_does_not_reuse_member_id(self):
        member = Member.objects.create(first_name="First", family_name="Record")
        deleted_pk = member.pk
        url = reverse("admin:members_member_delete", args=[deleted_pk])
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 302)
        self.assertFalse(Member.objects.filter(pk=deleted_pk).exists())
        replacement = Member.objects.create(first_name="Second", family_name="Record")
        self.assertGreater(replacement.pk, deleted_pk)

    def test_entry_routes_use_the_same_member_table(self):
        prefix = ChildrenFormSet.get_default_prefix()
        management = {f"{prefix}-TOTAL_FORMS": "0", f"{prefix}-INITIAL_FORMS": "0"}
        admin_url = reverse("admin:members_member_add")
        self.assertEqual(
            self.client.post(admin_url, {"first_name": "Admin", "family_name": "Record"}).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(reverse("members:add"), {
                "first_name": "Staff", "family_name": "Record", **management,
            }).status_code,
            302,
        )

        MembershipCheck.objects.create(
            account=self.member, full_name="User Record", cleared_for_application=True,
        )
        self.client.force_login(self.member)
        self.assertEqual(
            self.client.post(reverse("members:my_membership_apply"), {
                "first_name": "User", "family_name": "Record", **management,
            }).status_code,
            302,
        )
        workbook = self.workbook([["LAST NAME", "FIRST NAME"], ["Record", "Excel"]])
        self.assertEqual(self.upload(workbook).status_code, 403)

        self.client.force_login(self.staff)
        self.assertRedirects(self.upload(workbook), reverse("members:directory"))
        members = list(Member.objects.order_by("pk"))
        self.assertEqual([member.first_name for member in members], ["Admin", "Staff", "User", "Excel"])
        self.assertEqual(len({member.member_id for member in members}), 4)
        self.assertIsNone(members[-1].birth_date)
        self.assertEqual(members[-1].contact_numbers, "")
        self.assertContains(self.upload(workbook), "already imported", status_code=400)
        self.assertEqual(Member.objects.count(), 4)

    def test_invalid_row_prevents_batch_save(self):
        workbook = self.workbook([
            ["LAST NAME", "FIRST NAME"], ["Record", "Valid"], ["Missing first name"],
        ])
        self.assertContains(self.upload(workbook), "Row 3, FIRST NAME", status_code=400)
        self.assertFalse(Member.objects.exists())

    def test_excel_profile_text_and_new_fields_are_saved(self):
        workbook = self.workbook([
            ["LAST NAME", "FIRST NAME", "ADDRESS", "STATUS", "JOINED TAGC", "SUFFIX"],
            ["Record", "Excel", "Purok 4, Tagum", "OFW", "Since Birth", "Jr."],
        ])
        self.assertRedirects(self.upload(workbook), reverse("members:directory"))
        member = Member.objects.get()
        self.assertEqual(member.suffix, "Jr.")
        self.assertEqual(member.excel_profile_values, {
            "ADDRESS": "Purok 4, Tagum", "STATUS": "OFW", "JOINED TAGC": "Since Birth",
        })
        self.assertContains(self.client.get(reverse("members:detail", args=[member.pk])), "Since Birth")

    def test_profile_completeness_counts_address_once_and_excludes_other_excel_only_text(self):
        member = Member.objects.create(
            first_name="Excel",
            family_name="Record",
            baptized=False,
            status="",
            excel_profile_values={
                "ADDRESS": "Purok 4, Tagum",
                "CIVIL STATUS": "Married",
                "SPOUSE NAME": "Spouse Record",
                "JOINED TAGC": "Since Birth",
                "STATUS": "OFW",
            },
        )
        completion = member.profile_completeness
        self.assertEqual((completion["filled"], completion["total"], completion["percent"]), (5, 27, 19))
        self.assertIn("Ministry interests", completion["missing"])
        self.assertNotIn("Address", completion["missing"])
        self.assertIn("Civil status", completion["missing"])
        self.assertIn("Auxiliary", completion["missing"])
        self.assertIn("Spiritual gift", completion["missing"])
        self.assertIn("Wedding date", completion["missing"])
        self.assertNotIn("Spouse name", completion["missing"])
        self.assertNotIn("Baptism date", completion["missing"])
        self.assertContains(self.client.get(reverse("members:directory")), "19%")

        member.excel_profile_values = {}
        member.city = "Tagum"
        member.civil_status = Member.CivilStatus.MARRIED
        member.auxiliary = "MEN"
        member.save(update_fields=["excel_profile_values", "city", "civil_status", "auxiliary"])
        detail = self.client.get(reverse("members:detail", args=[member.pk]))
        self.assertContains(detail, "22%")
        self.assertContains(detail, "Wedding date")
        self.assertIn("Spouse name", member.profile_completeness["missing"])

        member.spouse_middle_name = "Cruz"
        member.save(update_fields=["spouse_middle_name"])
        self.assertNotIn("Spouse name", member.profile_completeness["missing"])
        edit = self.client.get(reverse("members:edit", args=[member.pk]))
        self.assertContains(edit, "data-highlight-blank")
        self.assertNotContains(self.client.get(reverse("members:add")), "data-highlight-blank")

    def test_ministry_interests_count_as_one_item(self):
        member = Member()
        empty = member.profile_completeness
        member.ministry_interests = ["Missions"]
        single = member.profile_completeness
        member.ministry_interests.append("Web/Technology")
        self.assertEqual(single["filled"], empty["filled"] + 1)
        self.assertEqual(single["total"], empty["total"])
        self.assertEqual(member.profile_completeness, single)

    def test_discovery_source_starts_unselected_and_counts_once(self):
        response = self.client.get(reverse("members:add"))
        sources = list(response.context["form"]["discovery_sources"])
        self.assertEqual(len(sources), 4)
        self.assertFalse(any(source.data["selected"] for source in sources))

        member = Member()
        empty = member.profile_completeness
        self.assertIn("How they heard about TAGC", empty["missing"])
        member.discovery_sources = ["Invited"]
        single = member.profile_completeness
        member.discovery_sources.append("Referred")
        self.assertEqual(single["filled"], empty["filled"] + 1)
        self.assertEqual(member.profile_completeness, single)

    def test_member_sees_shared_completeness_score_for_their_linked_record(self):
        self.client.force_login(self.member)
        url = reverse("members:my_membership")
        self.assertNotContains(self.client.get(url), "Profile completeness")
        member = Member.objects.create(account=self.member, first_name="First", family_name="Last")
        response = self.client.get(url)
        self.assertContains(response, f'{member.profile_completeness["percent"]}% complete')
        self.assertContains(response, "Missing fields")
        self.assertContains(response, reverse("members:my_membership_edit"))
