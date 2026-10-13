import hashlib
import io
import os
import tempfile
from datetime import datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import requests
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase

from server.apps.remotech.models import (
    Assignment,
    Badge,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
    ContentViewed,
    Leaderboard,
    LeaderboardDetail,
    ModuleContent,
    Question,
    QuestionOption,
    SetPasswordToken,
    Submission,
    UserAnswer,
    UserBadge,
    UserProgress,
)
from server.apps.remotech.services.auth import (
    MENTOR_GROUP,
    PARTICIPANT_GROUP,
    register_user,
)
from server.apps.remotech.services.grading import (
    compute_auto_score,
    penalized_score,
    split_points,
)
from server.apps.remotech.services.richtext import (
    extract_media_urls,
    sanitize_richtext,
)
from server.apps.remotech.views import ACTIVITY_TIME_ZONE
from server.pagination import StandardPagination

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="remotech-test-media-")


class StandardPaginationUnitTests(SimpleTestCase):
    def make_request(self, **params):
        return Request(APIRequestFactory().get("/", params))

    def test_default_page_size(self):
        assert StandardPagination().get_page_size(self.make_request()) == 10

    def test_client_can_set_page_size(self):
        request = self.make_request(page_size=5)
        assert StandardPagination().get_page_size(request) == 5

    def test_page_size_is_capped_at_max(self):
        request = self.make_request(page_size=999)
        assert StandardPagination().get_page_size(request) == 100


class PaginationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="secret123")
        self.courses = [
            Course.objects.create(user=self.user, title=f"Course {i:02d}")
            for i in range(12)
        ]

    def test_course_list_returns_paginated_envelope(self):
        response = self.client.get("/course/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(set(data.keys()), {"count", "next", "previous", "results"})
        self.assertEqual(data["count"], 12)
        self.assertEqual(len(data["results"]), 10)
        self.assertIsNotNone(data["next"])
        self.assertIsNone(data["previous"])

    def test_second_page_contains_remainder_without_overlap(self):
        page1 = self.client.get("/course/").json()
        response = self.client.get("/course/?page=2")
        page2 = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(page2["results"]), 2)
        self.assertIsNotNone(page2["previous"])

        ids1 = {item["id"] for item in page1["results"]}
        ids2 = {item["id"] for item in page2["results"]}
        self.assertEqual(ids1 & ids2, set())
        self.assertEqual(len(ids1 | ids2), 12)

    def test_page_size_query_param(self):
        data = self.client.get("/course/?page_size=5").json()

        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["count"], 12)

    def test_out_of_range_page_returns_404(self):
        response = self.client.get("/course/?page=999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("errors", response.json())

    def test_invalid_page_returns_404(self):
        response = self.client.get("/course/?page=abc")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_list_endpoint_is_paginated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/leaderboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(set(data.keys()), {"count", "next", "previous", "results"})

    def test_non_list_endpoint_still_works(self):
        response = self.client.post(
            "/token/", {"username": "nobody", "password": "wrong"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RichTextSanitizerUnitTests(SimpleTestCase):
    def test_strips_script_event_handlers_and_javascript_urls(self):
        html = (
            '<p onmouseover="evil()">hi</p>'
            "<script>alert(1)</script>"
            '<a href="javascript:alert(1)">bad</a>'
        )

        result = sanitize_richtext(html)

        self.assertNotIn("<script", result)
        self.assertNotIn("alert", result)
        self.assertNotIn("onmouseover", result)
        self.assertNotIn("javascript:", result)
        self.assertIn("<p>hi</p>", result)

    def test_strips_embedded_external_frames(self):
        html = (
            '<iframe src="https://evil.com"></iframe>'
            '<object data="https://evil.com/x.swf"></object>'
            "<style>body{display:none}</style>"
        )

        result = sanitize_richtext(html)

        self.assertNotIn("iframe", result)
        self.assertNotIn("object", result)
        self.assertNotIn("<style", result)

    def test_keeps_media_images_and_document_links(self):
        html = (
            '<img src="/media/course-content/images/a.webp" alt="gambar">'
            '<a href="/media/course-content/documents/b.pdf" download>b</a>'
        )

        result = sanitize_richtext(html)

        self.assertIn('src="/media/course-content/images/a.webp"', result)
        self.assertIn('href="/media/course-content/documents/b.pdf"', result)
        self.assertIn("download", result)

    def test_keeps_text_alignment_style(self):
        result = sanitize_richtext('<p style="text-align: center; color: red">x</p>')

        self.assertIn('style="text-align:center"', result)
        self.assertNotIn("color", result)

    def test_extract_media_urls(self):
        html = (
            '<img src="/media/course-content/images/a.webp">'
            '<a href="/media/course-content/documents/b.pdf">b</a>'
            '<a href="https://example.com">ext</a>'
            '<img src="/static/logo.png">'
        )

        self.assertEqual(
            extract_media_urls(html),
            {
                "/media/course-content/images/a.webp",
                "/media/course-content/documents/b.pdf",
            },
        )

    def test_extract_media_urls_on_empty_input(self):
        self.assertEqual(extract_media_urls(""), set())
        self.assertEqual(extract_media_urls(None), set())


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class UploadAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="uploader", password="secret123")
        self.client.force_authenticate(user=self.user)

    @staticmethod
    def make_image(name="photo.png", content_type="image/png"):
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)

    @staticmethod
    def storage_name(url):
        path = url.removeprefix(settings.BASE_URL.rstrip("/"))
        return path.removeprefix("/").removeprefix("media/")

    def test_image_upload_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post("/upload/image/", {"image": self.make_image()})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_image_upload_returns_webp_media_url(self):
        response = self.client.post("/upload/image/", {"image": self.make_image()})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        url = response.json()["url"]
        self.assertTrue(
            url.startswith(f"{settings.BASE_URL}/media/course-content/images/")
        )
        self.assertTrue(url.endswith(".webp"))
        self.assertTrue(default_storage.exists(self.storage_name(url)))

    def test_image_upload_rejects_non_image(self):
        file = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")

        response = self.client.post("/upload/image/", {"image": file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "image")

    def test_image_upload_rejects_oversized_image(self):
        width, height = 3500, 1000
        pixels = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
        buffer = io.BytesIO()
        pixels.save(buffer, format="PNG")
        self.assertGreater(buffer.tell(), 10 * 1024 * 1024)
        file = SimpleUploadedFile("big.png", buffer.getvalue(), "image/png")

        response = self.client.post("/upload/image/", {"image": file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "image")

    def test_document_upload_requires_authentication(self):
        self.client.force_authenticate(user=None)
        file = SimpleUploadedFile("materi.pdf", b"%PDF-1.7", "application/pdf")

        response = self.client.post("/upload/document/", {"file": file})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_document_upload_returns_media_url(self):
        file = SimpleUploadedFile("materi.pdf", b"%PDF-1.7", "application/pdf")

        response = self.client.post("/upload/document/", {"file": file})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        url = response.json()["url"]
        self.assertTrue(
            url.startswith(f"{settings.BASE_URL}/media/course-content/documents/")
        )
        self.assertTrue(url.endswith(".pdf"))
        self.assertTrue(default_storage.exists(self.storage_name(url)))

    def test_document_upload_rejects_disallowed_extension(self):
        file = SimpleUploadedFile("malware.exe", b"MZ", "application/octet-stream")

        response = self.client.post("/upload/document/", {"file": file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "file")

    def test_document_upload_rejects_oversized_document(self):
        file = SimpleUploadedFile(
            "big.pdf", b"a" * (20 * 1024 * 1024 + 1), "application/pdf"
        )

        response = self.client.post("/upload/document/", {"file": file})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ModuleRouteTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.user, title="Course Route")

    def test_module_route_is_registered(self):
        response = self.client.get("/module/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_module_list_is_public(self):
        CourseModule.objects.create(course=self.course, title="Module 1")

        response = self.client.get("/module/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_non_owner_cannot_create_module(self):
        other = User.objects.create_user(username="intruder", password="secret123")
        self.client.force_authenticate(user=other)

        response = self.client.post(
            "/module/", {"course": self.course.id, "title": "Hacked"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ModuleContentAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course A")
        self.text_module = CourseModule.objects.create(
            course=self.course, title="M1", module_category=CourseModule.Category.TEXT
        )
        self.video_module = CourseModule.objects.create(
            course=self.course, title="M2", module_category=CourseModule.Category.VIDEO
        )
        self.content = ModuleContent.objects.create(
            module=self.text_module, content_text="<p>old</p>"
        )

    @staticmethod
    def storage_name(url):
        path = url.removeprefix(settings.BASE_URL.rstrip("/"))
        return path.removeprefix("/").removeprefix("media/")

    def test_list_and_retrieve_are_public(self):
        list_response = self.client.get("/module-content/")
        detail_response = self.client.get(f"/module-content/{self.content.id}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.json()["count"], 1)

    def test_filter_by_module(self):
        other_module = CourseModule.objects.create(
            course=self.course, title="M3", module_category=CourseModule.Category.TEXT
        )
        ModuleContent.objects.create(module=other_module, content_text="<p>two</p>")

        response = self.client.get(f"/module-content/?module={self.text_module.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["module"], self.text_module.id)

    def test_create_requires_authentication(self):
        response = self.client.post(
            "/module-content/",
            {"module": self.text_module.id, "content_text": "<p>hi</p>"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_text_content_is_sanitized_on_create(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": (
                    '<p onmouseover="evil()">hi<script>alert(1)</script></p>'
                ),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stored = response.json()["content_text"]
        self.assertIn("<p>hi</p>", stored)
        self.assertNotIn("script", stored)
        self.assertNotIn("onmouseover", stored)
        self.assertEqual(
            ModuleContent.objects.get(pk=response.json()["id"]).content_text, stored
        )

    def test_text_content_is_sanitized_on_update(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/module-content/{self.content.id}/",
            {"content_text": '<img src="/media/x.webp" onerror="evil()">'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned = response.json()["content_text"]
        self.assertNotIn("onerror", returned)
        self.assertIn(f'src="{settings.BASE_URL}/media/x.webp"', returned)
        self.content.refresh_from_db()
        self.assertIn('src="/media/x.webp"', self.content.content_text)
        self.assertNotIn(settings.BASE_URL, self.content.content_text)

    def test_text_content_requires_content(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/", {"module": self.text_module.id, "content_text": "   "}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "content_text")

    def test_video_content_requires_url(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/", {"module": self.video_module.id}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "content_url")

    def test_non_owner_cannot_create_content(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            "/module-content/",
            {"module": self.text_module.id, "content_text": "<p>hi</p>"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_owner_cannot_update_content(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            f"/module-content/{self.content.id}/", {"content_text": "<p>hijack</p>"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.content.refresh_from_db()
        self.assertEqual(self.content.content_text, "<p>old</p>")

    def test_non_owner_cannot_delete_content(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.delete(f"/module-content/{self.content.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ModuleContent.objects.filter(pk=self.content.id).exists())

    def test_owner_can_update_and_delete_content(self):
        self.client.force_authenticate(user=self.owner)

        update_response = self.client.patch(
            f"/module-content/{self.content.id}/", {"content_text": "<p>new</p>"}
        )
        delete_response = self.client.delete(f"/module-content/{self.content.id}/")

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ModuleContent.objects.filter(pk=self.content.id).exists())

    def test_orphaned_media_removed_when_reference_dropped(self):
        self.client.force_authenticate(user=self.owner)
        url = self.client.post("/upload/image/", {"image": self._make_image()}).json()[
            "url"
        ]
        create_response = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": f'<p><img src="{url}"></p>',
            },
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        storage_name = self.storage_name(url)
        self.assertTrue(default_storage.exists(storage_name))

        update_response = self.client.patch(
            f"/module-content/{create_response.json()['id']}/",
            {"content_text": "<p>no image</p>"},
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertFalse(default_storage.exists(storage_name))

    def test_media_still_referenced_is_kept(self):
        self.client.force_authenticate(user=self.owner)
        url = self.client.post("/upload/image/", {"image": self._make_image()}).json()[
            "url"
        ]
        first = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": f'<p><img src="{url}"></p>',
            },
        ).json()
        second = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": f'<p><img src="{url}"></p>',
            },
        ).json()
        storage_name = self.storage_name(url)

        self.client.delete(f"/module-content/{first['id']}/")

        self.assertTrue(default_storage.exists(storage_name))

        self.client.patch(
            f"/module-content/{second['id']}/", {"content_text": "<p>x</p>"}
        )

        self.assertFalse(default_storage.exists(storage_name))

    def test_write_normalizes_own_absolute_media_url(self):
        self.client.force_authenticate(user=self.owner)
        absolute = f"{settings.BASE_URL}/media/course-content/images/z.webp"

        response = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": f'<p><img src="{absolute}"></p>',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = ModuleContent.objects.get(pk=response.json()["id"])
        stored = content.content_text
        self.assertIn('src="/media/course-content/images/z.webp"', stored)
        self.assertNotIn(settings.BASE_URL, stored)
        self.assertIn(
            f'src="{settings.BASE_URL}/media/course-content/images/z.webp"',
            response.json()["content_text"],
        )

    def test_write_keeps_external_media_url(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": '<img src="https://other.example.com/pic.png">',
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(
            'src="https://other.example.com/pic.png"',
            response.json()["content_text"],
        )

    def test_read_returns_absolute_media_urls(self):
        content = ModuleContent.objects.create(
            module=self.text_module,
            content_text='<p><img src="/media/course-content/images/a.webp"></p>',
        )

        response = self.client.get(f"/module-content/{content.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            f'src="{settings.BASE_URL}/media/course-content/images/a.webp"',
            response.json()["content_text"],
        )

    def test_round_trip_keeps_db_relative(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            "/module-content/",
            {
                "module": self.text_module.id,
                "content_text": '<p><img src="/media/course-content/images/rt.webp"></p>',
            },
        ).json()
        fetched = self.client.get(f"/module-content/{created['id']}/").json()[
            "content_text"
        ]
        self.assertIn(settings.BASE_URL, fetched)

        response = self.client.patch(
            f"/module-content/{created['id']}/", {"content_text": fetched}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stored = ModuleContent.objects.get(pk=created["id"]).content_text
        self.assertNotIn(settings.BASE_URL, stored)
        self.assertIn('src="/media/course-content/images/rt.webp"', stored)

    @staticmethod
    def _make_image():
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
        return SimpleUploadedFile("photo.png", buffer.getvalue(), "image/png")


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CourseRepresentationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cthumb", password="secret123")

    @staticmethod
    def make_thumbnail():
        buffer = io.BytesIO()
        Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
        return SimpleUploadedFile("thumb.png", buffer.getvalue(), "image/png")

    def test_thumbnail_is_absolute(self):
        course = Course.objects.create(
            user=self.user, title="With Thumb", thumbnail=self.make_thumbnail()
        )

        response = self.client.get(f"/course/{course.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            response.json()["thumbnail"].startswith(
                f"{settings.BASE_URL}/media/courses/thumbnails/"
            )
        )

    def test_empty_thumbnail_stays_none(self):
        course = Course.objects.create(user=self.user, title="No Thumb")

        response = self.client.get(f"/course/{course.id}/")

        self.assertIsNone(response.json()["thumbnail"])


@override_settings(CORS_ALLOWED_ORIGINS=["https://remotech.web.id"])
class CorsAPITests(APITestCase):
    def test_allowed_origin_gets_cors_header(self):
        response = self.client.get("/course/", HTTP_ORIGIN="https://remotech.web.id")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "https://remotech.web.id"
        )

    def test_disallowed_origin_gets_no_cors_header(self):
        response = self.client.get("/course/", HTTP_ORIGIN="https://evil.example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.has_header("Access-Control-Allow-Origin"))

    def test_preflight_for_upload_endpoint(self):
        response = self.client.options(
            "/upload/image/",
            HTTP_ORIGIN="https://remotech.web.id",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response["Access-Control-Allow-Origin"], "https://remotech.web.id"
        )
        self.assertIn("POST", response["Access-Control-Allow-Methods"])


class RegisterUserGroupTests(TestCase):
    def test_new_user_is_added_to_participant_group(self):
        user = register_user("alice@example.com", "Alice Doe")

        self.assertTrue(Group.objects.filter(name=PARTICIPANT_GROUP).exists())
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)), [PARTICIPANT_GROUP]
        )

    def test_creates_participant_group_when_missing(self):
        self.assertFalse(Group.objects.filter(name=PARTICIPANT_GROUP).exists())

        user = register_user("bob@example.com", "Bob")

        self.assertEqual(user.groups.get().name, PARTICIPANT_GROUP)

    def test_existing_participant_group_is_reused(self):
        group = Group.objects.create(name=PARTICIPANT_GROUP)

        user = register_user("carol@example.com", "Carol Smith")

        self.assertEqual(Group.objects.filter(name=PARTICIPANT_GROUP).count(), 1)
        self.assertEqual(user.groups.get(), group)
        self.assertEqual(user.first_name, "Carol")
        self.assertEqual(user.last_name, "Smith")


class SetPasswordRouteTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dave@example.com", email="dave@example.com"
        )
        self.user.set_unusable_password()
        self.user.save()
        self.token = SetPasswordToken.objects.create(
            user=self.user, token="valid-token-value"
        )

    def test_get_renders_set_password_page(self):
        response = self.client.get("/set-password/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
        self.assertContains(response, f'href="{settings.FE_URL.rstrip("/")}/login"')
        self.assertContains(response, "Back to Login")

    def test_get_renders_reset_password_page_with_back_to_login_link(self):
        response = self.client.get("/reset-password/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response["Content-Type"])
        self.assertContains(response, f'href="{settings.FE_URL.rstrip("/")}/login"')
        self.assertContains(response, "Back to Login")

    def test_post_sets_password(self):
        response = self.client.post(
            "/set-password/",
            {
                "token": self.token.token,
                "password": "newsecret123",
                "password_confirm": "newsecret123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecret123"))

    def test_post_with_invalid_token_returns_validation_error(self):
        response = self.client.post(
            "/set-password/",
            {
                "token": "nope",
                "password": "newsecret123",
                "password_confirm": "newsecret123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "token")

    def test_forgot_password_reset_sets_password(self):
        response = self.client.post(
            "/forgot-password/reset/",
            {
                "token": self.token.token,
                "password": "resetsecret123",
                "password_confirm": "resetsecret123",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("resetsecret123"))


class ListFilterTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course_a = Course.objects.create(user=self.owner, title="Course A")
        self.course_b = Course.objects.create(user=self.owner, title="Course B")
        self.module_a = CourseModule.objects.create(course=self.course_a, title="MA")
        self.module_b = CourseModule.objects.create(course=self.course_b, title="MB")
        self.client.force_authenticate(user=self.owner)

    def test_module_filter_by_course(self):
        response = self.client.get(f"/module/?course={self.course_a.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], self.module_a.id)

    def test_enrollment_filter_by_user_and_course(self):
        CourseEnrollment.objects.create(course=self.course_a, user=self.owner)
        CourseEnrollment.objects.create(course=self.course_b, user=self.owner)

        by_user = self.client.get(f"/enroll/?user={self.owner.id}").json()
        by_course = self.client.get(f"/enroll/?course={self.course_a.id}").json()

        self.assertEqual(by_user["count"], 2)
        self.assertEqual(by_user["results"][0]["user"], self.owner.id)
        self.assertEqual(by_course["count"], 1)
        self.assertEqual(by_course["results"][0]["course"]["id"], self.course_a.id)

    def test_enrollment_search_by_course_title(self):
        CourseEnrollment.objects.create(course=self.course_a, user=self.owner)
        CourseEnrollment.objects.create(course=self.course_b, user=self.owner)

        response = self.client.get("/enroll/?search=Course A").json()

        self.assertEqual(response["count"], 1)
        self.assertEqual(response["results"][0]["course"]["id"], self.course_a.id)

    def test_enrollment_default_ordering_newest_first(self):
        older = CourseEnrollment.objects.create(course=self.course_b, user=self.owner)
        newer = CourseEnrollment.objects.create(course=self.course_a, user=self.owner)
        CourseEnrollment.objects.filter(id=older.id).update(
            enrolled_at=timezone.now() - timedelta(days=1)
        )

        default_order = self.client.get("/enroll/").json()
        ascending = self.client.get("/enroll/?ordering=enrolled_at").json()

        self.assertEqual(
            [item["id"] for item in default_order["results"]],
            [newer.id, older.id],
        )
        self.assertEqual(
            [item["id"] for item in ascending["results"]],
            [older.id, newer.id],
        )

    def test_order_filter_by_course_and_status(self):
        CourseOrder.objects.create(
            course=self.course_a,
            user=self.owner,
            order_no="ORD-1",
            gross_amount="100000.00",
            payment_type="gopay",
            midtrans_transaction_id="tx-1",
        )
        CourseOrder.objects.create(
            course=self.course_b,
            user=self.owner,
            order_no="ORD-2",
            gross_amount="200000.00",
            payment_type="qris",
            midtrans_transaction_id="tx-2",
            transaction_status="settlement",
        )

        by_course = self.client.get(f"/order/?course={self.course_b.id}").json()
        by_status = self.client.get("/order/?transaction_status=settlement").json()

        self.assertEqual(by_course["count"], 1)
        self.assertEqual(by_course["results"][0]["order_no"], "ORD-2")
        self.assertEqual(by_status["count"], 1)
        self.assertEqual(by_status["results"][0]["order_no"], "ORD-2")

    def test_order_list_includes_course_title(self):
        CourseOrder.objects.create(
            course=self.course_a,
            user=self.owner,
            order_no="ORD-1",
            gross_amount="100000.00",
            payment_type="gopay",
            midtrans_transaction_id="tx-1",
        )

        response = self.client.get("/order/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        first = response.json()["results"][0]
        self.assertEqual(first["course"], self.course_a.id)
        self.assertEqual(first["course_title"], "Course A")

    def test_assignment_filter_by_course_module(self):
        Assignment.objects.create(
            course_module=self.module_a, name="A1", description="do it"
        )
        Assignment.objects.create(
            course_module=self.module_b, name="A2", description="do it too"
        )

        response = self.client.get(f"/assignment/?course_module={self.module_a.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "A1")

    def test_leaderboard_filter_by_course_and_user(self):
        Leaderboard.objects.create(course=self.course_a, user=self.owner, total_points=10)
        Leaderboard.objects.create(course=self.course_b, user=self.other, total_points=20)

        by_course = self.client.get(f"/leaderboard/?course={self.course_a.id}").json()
        by_user = self.client.get(f"/leaderboard/?user={self.other.id}").json()

        self.assertEqual(by_course["count"], 1)
        self.assertEqual(by_course["results"][0]["user"], self.owner.id)
        self.assertEqual(by_user["count"], 1)
        self.assertEqual(by_user["results"][0]["total_points"], 20)


class SubmissionRouteTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course Sub")
        self.module = CourseModule.objects.create(
            course=self.course, title="M1", module_category="upload"
        )
        self.assignment_a = Assignment.objects.create(
            course_module=self.module, name="A1", description="desc"
        )
        self.assignment_b = Assignment.objects.create(
            course_module=self.module, name="A2", description="desc"
        )
        self.client.force_authenticate(user=self.owner)

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/submission/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_submission_route_is_registered(self):
        response = self.client.get("/submission/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_submission(self):
        response = self.client.post(
            "/submission/",
            {
                "user": self.owner.id,
                "assignment": self.assignment_a.id,
                "submission_url": "https://example.com/task.pdf",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["submission_url"], "https://example.com/task.pdf")
        self.assertEqual(data["score"], 0)
        self.assertEqual(data["user"], self.owner.id)

    def test_filter_by_assignment_and_user(self):
        Submission.objects.create(
            user=self.owner,
            assignment=self.assignment_a,
            submission_url="https://example.com/a.pdf",
        )
        Submission.objects.create(
            user=self.other,
            assignment=self.assignment_b,
            submission_url="https://example.com/b.pdf",
        )

        by_assignment = self.client.get(
            f"/submission/?assignment={self.assignment_a.id}"
        ).json()
        by_user = self.client.get(f"/submission/?user={self.other.id}").json()

        self.assertEqual(by_assignment["count"], 1)
        self.assertEqual(by_assignment["results"][0]["assignment"], self.assignment_a.id)
        self.assertEqual(by_user["count"], 1)
        self.assertEqual(by_user["results"][0]["user"], self.other.id)

    def test_create_ignores_body_user_and_uses_request_user(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            "/submission/",
            {
                "user": self.owner.id,
                "assignment": self.assignment_a.id,
                "submission_url": "https://example.com/x.pdf",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["user"], self.other.id)
        self.assertEqual(
            Submission.objects.get(assignment=self.assignment_a).user, self.other
        )

    def test_create_resets_score_and_reviewed_by(self):
        response = self.client.post(
            "/submission/",
            {
                "user": self.owner.id,
                "assignment": self.assignment_a.id,
                "submission_url": "https://example.com/x.pdf",
                "score": 100,
                "reviewed_by": "spoof",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["score"], 0)
        self.assertEqual(response.json()["reviewed_by"], "")

    def test_create_submission_marks_module_complete_when_enrolled(self):
        CourseEnrollment.objects.create(course=self.course, user=self.owner)

        response = self.client.post(
            "/submission/",
            {
                "user": self.owner.id,
                "assignment": self.assignment_a.id,
                "submission_url": "https://example.com/task.pdf",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        progress = UserProgress.objects.get(module=self.module, user=self.owner)
        self.assertEqual(progress.status, UserProgress.ProgressStatus.FINISH)
        self.assertIsNotNone(progress.complete_at)

    def test_create_submission_without_enrollment_does_not_mark(self):
        response = self.client.post(
            "/submission/",
            {
                "user": self.owner.id,
                "assignment": self.assignment_a.id,
                "submission_url": "https://example.com/task.pdf",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(
            UserProgress.objects.filter(module=self.module, user=self.owner).exists()
        )


MIDTRANS_TEST_KEY = "test-server-key"


def make_notification(order, transaction_status="settlement", **overrides):
    payload = {
        "order_id": order.order_no,
        "status_code": "200",
        "gross_amount": str(order.gross_amount),
        "transaction_status": transaction_status,
        "transaction_id": "tx-123",
        "payment_type": "qris",
    }
    payload.update(overrides)
    payload["signature_key"] = hashlib.sha512(
        f"{payload['order_id']}{payload['status_code']}"
        f"{payload['gross_amount']}{MIDTRANS_TEST_KEY}".encode()
    ).hexdigest()
    return payload


def configure_snap_response(mock_post, token="snap-token-1"):
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"token": token}


@override_settings(MIDTRANS_SERVER_KEY=MIDTRANS_TEST_KEY)
class EnrollCourseTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.buyer = User.objects.create_user(
            username="buyer", password="secret123", email="buyer@example.com"
        )
        self.free_course = Course.objects.create(
            user=self.owner, title="Free Course", price=0, is_publish=True
        )
        self.paid_course = Course.objects.create(
            user=self.owner, title="Paid Course", price=150000, is_publish=True
        )
        self.draft_course = Course.objects.create(
            user=self.owner, title="Draft Course", price=1000, is_publish=False
        )
        self.closed_course = Course.objects.create(
            user=self.owner, title="Closed Course", price=0, is_publish=True, is_open=False
        )
        self.client.force_authenticate(user=self.buyer)

    def test_free_course_enrolls_immediately(self):
        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            response = self.client.post(
                "/order/enroll/", {"course": self.free_course.id}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["enrolled"])
        self.assertEqual(data["order"]["transaction_status"], "settlement")
        self.assertEqual(data["order"]["gross_amount"], "0.00")
        self.assertEqual(data["order"]["payment_type"], "free")
        self.assertIsNotNone(data["order"]["paid_at"])
        mock_post.assert_not_called()
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.free_course
            ).exists()
        )

    def test_free_course_second_attempt_is_rejected(self):
        self.client.post("/order/enroll/", {"course": self.free_course.id})

        response = self.client.post("/order/enroll/", {"course": self.free_course.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.free_course
            ).count(),
            1,
        )

    def test_paid_course_creates_pending_order_with_snap_token(self):
        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            configure_snap_response(mock_post)
            response = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["enrolled"])
        self.assertEqual(data["order"]["transaction_status"], "pending")
        self.assertEqual(data["order"]["gross_amount"], "150000.00")
        self.assertEqual(data["snap_token"], "snap-token-1")
        mock_post.assert_called_once()
        auth = mock_post.call_args.kwargs["auth"]
        self.assertEqual(auth, (MIDTRANS_TEST_KEY, ""))
        self.assertFalse(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.paid_course
            ).exists()
        )

    def test_paid_course_reuses_pending_order_and_snap_token(self):
        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            configure_snap_response(mock_post)
            first = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            ).json()
            second = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            ).json()

        self.assertEqual(first["order"]["id"], second["order"]["id"])
        self.assertEqual(second["snap_token"], "snap-token-1")
        mock_post.assert_called_once()
        self.assertEqual(CourseOrder.objects.filter(user=self.buyer).count(), 1)

    def test_retry_after_failed_payment_creates_new_order(self):
        CourseOrder.objects.create(
            user=self.buyer,
            course=self.paid_course,
            order_no="ORD-FAILED",
            gross_amount="150000.00",
            transaction_status="deny",
        )

        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            configure_snap_response(mock_post)
            response = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertNotEqual(data["order"]["order_no"], "ORD-FAILED")
        self.assertEqual(data["order"]["transaction_status"], "pending")
        mock_post.assert_called_once()

    def test_settled_order_without_enrollment_is_rejected(self):
        CourseOrder.objects.create(
            user=self.buyer,
            course=self.paid_course,
            order_no="ORD-SETTLED",
            gross_amount="150000.00",
            transaction_status="settlement",
        )

        response = self.client.post("/order/enroll/", {"course": self.paid_course.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.paid_course
            ).exists()
        )

    def test_unpublished_course_is_rejected(self):
        response = self.client.post("/order/enroll/", {"course": self.draft_course.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CourseOrder.objects.filter(user=self.buyer).exists())

    def test_closed_course_is_rejected(self):
        response = self.client.post("/order/enroll/", {"course": self.closed_course.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            CourseOrder.objects.filter(user=self.buyer, course=self.closed_course).exists()
        )
        self.assertFalse(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.closed_course
            ).exists()
        )


    def test_gateway_failure_keeps_pending_order_for_retry(self):
        # 5xx responses re-raise in tests unless disabled.
        self.client.raise_request_exception = False
        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            mock_post.side_effect = requests.ConnectionError("boom")
            failed = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            )

        self.assertEqual(failed.status_code, status.HTTP_502_BAD_GATEWAY)
        order = CourseOrder.objects.get(user=self.buyer, course=self.paid_course)
        self.assertEqual(order.transaction_status, "pending")
        self.assertEqual(order.snap_token, "")

        with patch(
            "server.apps.remotech.services.payment.requests.post"
        ) as mock_post:
            configure_snap_response(mock_post)
            retried = self.client.post(
                "/order/enroll/", {"course": self.paid_course.id}
            )

        self.assertEqual(retried.status_code, status.HTTP_200_OK)
        self.assertEqual(retried.json()["order"]["id"], order.id)

    def test_enroll_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post("/order/enroll/", {"course": self.free_course.id})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(MIDTRANS_SERVER_KEY=MIDTRANS_TEST_KEY)
class PaymentWebhookTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.buyer = User.objects.create_user(username="buyer", password="secret123")
        self.course = Course.objects.create(
            user=self.owner, title="Paid Course", price=150000, is_publish=True
        )
        self.order = CourseOrder.objects.create(
            user=self.buyer,
            course=self.course,
            order_no="ORD-WEBHOOK",
            gross_amount="150000.00",
        )

    def post_notification(self, payload):
        return self.client.post("/payment/notification/", payload, format="json")

    def test_invalid_signature_returns_403(self):
        payload = make_notification(self.order)
        payload["signature_key"] = "invalid-signature"

        response = self.post_notification(payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "pending")
        self.assertFalse(CourseEnrollment.objects.filter(user=self.buyer).exists())

    def test_settlement_creates_enrollment(self):
        response = self.post_notification(make_notification(self.order))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "settlement")
        self.assertEqual(self.order.payment_type, "qris")
        self.assertEqual(self.order.midtrans_transaction_id, "tx-123")
        self.assertIsNotNone(self.order.paid_at)
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.course
            ).exists()
        )

    def test_settlement_notification_is_idempotent(self):
        self.post_notification(make_notification(self.order))
        response = self.post_notification(make_notification(self.order))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.course
            ).count(),
            1,
        )

    def test_status_downgrade_is_ignored(self):
        self.post_notification(make_notification(self.order))
        response = self.post_notification(
            make_notification(self.order, transaction_status="pending")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "settlement")
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.course
            ).exists()
        )

    def test_gross_amount_mismatch_returns_400(self):
        payload = make_notification(self.order, gross_amount="999999.00")

        response = self.post_notification(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "pending")

    def test_unknown_order_returns_400(self):
        payload = make_notification(self.order, order_id="ORD-UNKNOWN")

        response = self.post_notification(payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pending_notification_keeps_order_pending(self):
        response = self.post_notification(
            make_notification(self.order, transaction_status="pending")
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "pending")
        self.assertIsNone(self.order.paid_at)
        self.assertFalse(CourseEnrollment.objects.filter(user=self.buyer).exists())

    def test_unknown_capture_status_is_rejected(self):
        # QRIS never sends `capture`; unknown statuses must not touch the order.
        response = self.post_notification(
            make_notification(self.order, transaction_status="capture")
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.order.refresh_from_db()
        self.assertEqual(self.order.transaction_status, "pending")
        self.assertIsNone(self.order.paid_at)
        self.assertFalse(CourseEnrollment.objects.filter(user=self.buyer).exists())


@override_settings(MIDTRANS_SERVER_KEY=MIDTRANS_TEST_KEY)
class CheckPaymentTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.buyer = User.objects.create_user(username="buyer", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(
            user=self.owner, title="Paid Course", price=150000, is_publish=True
        )
        self.order = CourseOrder.objects.create(
            user=self.buyer,
            course=self.course,
            order_no="ORD-CHECK",
            gross_amount="150000.00",
        )
        self.client.force_authenticate(user=self.buyer)

    def test_settlement_from_gateway_creates_enrollment(self):
        with patch(
            "server.apps.remotech.services.payment.requests.get"
        ) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "order_id": self.order.order_no,
                "transaction_status": "settlement",
                "payment_type": "qris",
                "transaction_id": "tx-9",
            }
            response = self.client.post(f"/order/{self.order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["transaction_status"], "settlement")
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["auth"], (MIDTRANS_TEST_KEY, ""))
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.buyer, course=self.course
            ).exists()
        )

    def test_pending_from_gateway_does_not_enroll(self):
        with patch(
            "server.apps.remotech.services.payment.requests.get"
        ) as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "order_id": self.order.order_no,
                "transaction_status": "pending",
            }
            response = self.client.post(f"/order/{self.order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["transaction_status"], "pending")
        self.assertFalse(CourseEnrollment.objects.filter(user=self.buyer).exists())

    def test_settled_order_skips_gateway_call(self):
        self.order.transaction_status = "settlement"
        self.order.save(update_fields=["transaction_status"])

        with patch(
            "server.apps.remotech.services.payment.requests.get"
        ) as mock_get:
            response = self.client.post(f"/order/{self.order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_not_called()

    def test_free_order_skips_gateway_call(self):
        order = CourseOrder.objects.create(
            user=self.buyer,
            course=self.course,
            order_no="ORD-FREE",
            gross_amount="0.00",
        )

        with patch(
            "server.apps.remotech.services.payment.requests.get"
        ) as mock_get:
            response = self.client.post(f"/order/{order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get.assert_not_called()

    def test_other_user_order_returns_404(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(f"/order/{self.order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_gateway_error_returns_502(self):
        self.client.raise_request_exception = False
        with patch(
            "server.apps.remotech.services.payment.requests.get"
        ) as mock_get:
            mock_get.side_effect = requests.ConnectionError("boom")
            response = self.client.post(f"/order/{self.order.id}/check-payment/")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)


class OrderEnrollmentAccessTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.buyer = User.objects.create_user(username="buyer", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(
            user=self.owner, title="Paid Course", price=150000, is_publish=True
        )
        self.order = CourseOrder.objects.create(
            user=self.other,
            course=self.course,
            order_no="ORD-OTHER",
            gross_amount="150000.00",
            payment_type="gopay",
            midtrans_transaction_id="tx-1",
        )
        self.enrollment = CourseEnrollment.objects.create(
            user=self.other, course=self.course
        )
        self.client.force_authenticate(user=self.buyer)

    def test_order_create_is_not_allowed(self):
        response = self.client.post("/order/", {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_order_update_is_not_allowed(self):
        patch_response = self.client.patch(
            f"/order/{self.order.id}/", {"transaction_status": "settlement"}
        )
        delete_response = self.client.delete(f"/order/{self.order.id}/")

        self.assertEqual(
            patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_enrollment_write_is_not_allowed(self):
        create_response = self.client.post(
            "/enroll/", {"course": self.course.id, "user": self.buyer.id}
        )
        patch_response = self.client.patch(f"/enroll/{self.enrollment.id}/", {})
        delete_response = self.client.delete(f"/enroll/{self.enrollment.id}/")

        self.assertEqual(
            create_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_order_list_only_shows_own_orders(self):
        response = self.client.get("/order/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_other_user_order_detail_returns_404(self):
        response = self.client.get(f"/order/{self.order.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_enrollment_list_only_shows_own_enrollments(self):
        response = self.client.get("/enroll/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_order_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/order/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentUserAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi@example.com",
            email="budi@example.com",
            first_name="Budi",
            last_name="Santoso",
        )

    def test_me_returns_current_user_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/user/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": self.user.id,
                "email": "budi@example.com",
                "first_name": "Budi",
                "last_name": "Santoso",
                "full_name": "Budi Santoso",
                "is_mentor": False,
            },
        )

    def test_me_returns_true_is_mentor_for_mentor_group(self):
        mentor_group, _ = Group.objects.get_or_create(name=MENTOR_GROUP)
        self.user.groups.add(mentor_group)
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/user/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["is_mentor"])

    def test_me_falls_back_to_username_when_name_is_empty(self):
        self.user.first_name = ""
        self.user.last_name = ""
        self.user.save(update_fields=["first_name", "last_name"])
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/user/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["full_name"], "budi@example.com")

    def test_me_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/user/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi@example.com",
            email="budi@example.com",
            first_name="Budi",
            last_name="Santoso",
            password="secret123",
        )

    def test_patch_updates_name_and_email(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/user/me/",
            {
                "first_name": "Budi Ardian",
                "last_name": "Santoso",
                "email": "baru@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Budi Ardian")
        self.assertEqual(self.user.last_name, "Santoso")
        self.assertEqual(self.user.email, "baru@example.com")
        # username dipakai sebagai identitas login — ikut menyesuaikan email.
        self.assertEqual(self.user.username, "baru@example.com")
        self.assertEqual(response.json()["email"], "baru@example.com")

    def test_patch_keeps_username_when_not_equal_to_email(self):
        self.user.username = "budi"
        self.user.save(update_fields=["username"])
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/user/me/", {"email": "baru@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "budi")
        self.assertEqual(self.user.email, "baru@example.com")

    def test_patch_rejects_email_taken_by_another_user(self):
        User.objects.create_user(username="lain@example.com", email="lain@example.com")
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            "/user/me/", {"email": "lain@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "email")

    def test_patch_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.patch("/user/me/", {"first_name": "X"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserChangePasswordTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="budi@example.com",
            email="budi@example.com",
            first_name="Budi",
            last_name="Santoso",
            password="secret123",
        )

    def change_password(self, **overrides):
        payload = {
            "old_password": "secret123",
            "new_password": "newsecret456",
            "new_password_confirm": "newsecret456",
        }
        payload.update(overrides)
        return self.client.post("/user/change-password/", payload, format="json")

    def test_change_password_updates_password(self):
        self.client.force_authenticate(user=self.user)

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecret456"))
        self.assertFalse(self.user.check_password("secret123"))

    def test_wrong_old_password_returns_field_error(self):
        self.client.force_authenticate(user=self.user)

        response = self.change_password(old_password="salah12345")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "old_password")

    def test_mismatched_confirmation_returns_field_error(self):
        self.client.force_authenticate(user=self.user)

        response = self.change_password(new_password_confirm="lain456")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "new_password_confirm")

    def test_rejects_reused_password(self):
        self.client.force_authenticate(user=self.user)

        response = self.change_password(
            new_password="secret123", new_password_confirm="secret123"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "new_password")

    def test_rejects_numeric_password(self):
        self.client.force_authenticate(user=self.user)

        response = self.change_password(
            new_password="1234567890", new_password_confirm="1234567890"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["errors"][0]["attr"], "new_password")

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.change_password()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CourseIsOpenTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.open_course = Course.objects.create(
            user=self.owner, title="Open Course", price=0, is_publish=True, is_open=True
        )
        self.closed_course = Course.objects.create(
            user=self.owner, title="Closed Course", price=0, is_publish=True, is_open=False
        )

    def test_course_created_without_is_open_defaults_to_true(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post("/course/", {"title": "New Course"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(response.json()["is_open"], True)

    def test_course_created_with_is_open_false(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/course/", {"title": "Closed On Create", "is_open": False}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIs(response.json()["is_open"], False)

    def test_form_update_does_not_reset_booleans(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/course/{self.open_course.id}/", {"title": "Renamed Open Course"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.json()["is_publish"], True)
        self.assertIs(response.json()["is_open"], True)

    def test_course_detail_returns_is_open(self):
        response = self.client.get(f"/course/{self.closed_course.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(response.json()["is_open"], False)

    def test_filter_by_is_open_false(self):
        response = self.client.get("/course/", {"is_open": "false"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.closed_course.id])

    def test_filter_by_is_open_true(self):
        response = self.client.get("/course/", {"is_open": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.open_course.id])


class CourseCatalogTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="uploader", password="secret123", first_name="Budi", last_name="Santoso"
        )
        self.free = Course.objects.create(
            user=self.owner, title="Gratis Course", price=0, is_publish=True
        )
        self.cheap = Course.objects.create(
            user=self.owner, title="Murah Meriah", price=10000, is_publish=True
        )
        self.expensive = Course.objects.create(
            user=self.owner, title="Mahal Course", price=900000, is_publish=True
        )
        self.draft = Course.objects.create(
            user=self.owner, title="Draft Course", price=0, is_publish=False
        )

    def test_user_name_is_returned(self):
        response = self.client.get(f"/course/{self.cheap.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["user_name"], "Budi Santoso")

    def test_user_name_falls_back_to_username(self):
        anonymous = User.objects.create_user(username="solo@example.com")
        course = Course.objects.create(user=anonymous, title="Solo Course")

        response = self.client.get(f"/course/{course.id}/")

        self.assertEqual(response.json()["user_name"], "solo@example.com")

    def test_filter_by_is_publish(self):
        response = self.client.get("/course/", {"is_publish": "false"})

        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.draft.id])

    def test_search_by_title(self):
        response = self.client.get("/course/", {"search": "Mahal"})

        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.expensive.id])

    def test_search_by_description(self):
        Course.objects.create(
            user=self.owner, title="Lain Judul", description="kopinya mahal", is_publish=True
        )

        response = self.client.get("/course/", {"search": "kopinya"})

        self.assertEqual(len(response.json()["results"]), 1)

    def test_ordering_by_price_ascending(self):
        response = self.client.get(
            "/course/", {"is_publish": "true", "ordering": "price"}
        )

        results = response.json()["results"]
        self.assertEqual(
            [course["id"] for course in results],
            [self.free.id, self.cheap.id, self.expensive.id],
        )

    def test_default_ordering_is_newest_first(self):
        response = self.client.get("/course/", {"is_publish": "true"})

        results = response.json()["results"]
        self.assertEqual(
            [course["id"] for course in results],
            [self.expensive.id, self.cheap.id, self.free.id],
        )

    def test_price_free_filter(self):
        response = self.client.get(
            "/course/", {"is_publish": "true", "price__lte": "0", "ordering": "price"}
        )

        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.free.id])

    def test_price_paid_filter(self):
        response = self.client.get(
            "/course/", {"is_publish": "true", "price__gt": "0", "ordering": "price"}
        )

        results = response.json()["results"]
        self.assertEqual(
            [course["id"] for course in results], [self.cheap.id, self.expensive.id]
        )


class CourseMyTests(APITestCase):
    def setUp(self):
        self.mentor = User.objects.create_user(
            username="mentor", password="secret123", first_name="Mentor"
        )
        self.other = User.objects.create_user(
            username="other", password="secret123", first_name="Other"
        )
        self.own_draft = Course.objects.create(
            user=self.mentor, title="My Draft", is_publish=False
        )
        self.own_published = Course.objects.create(
            user=self.mentor, title="My Published", is_publish=True
        )
        self.foreign = Course.objects.create(
            user=self.other, title="Not Mine", is_publish=True
        )

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/course/my/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_only_own_courses_including_drafts(self):
        self.client.force_authenticate(user=self.mentor)

        response = self.client.get("/course/my/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertEqual(
            [course["id"] for course in results],
            [self.own_published.id, self.own_draft.id],
        )

    def test_other_users_courses_are_excluded(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get("/course/my/")

        results = response.json()["results"]
        self.assertEqual([course["id"] for course in results], [self.foreign.id])

    def test_supports_search_and_pagination_envelope(self):
        self.client.force_authenticate(user=self.mentor)

        response = self.client.get("/course/my/", {"search": "Draft"})

        data = response.json()
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual([course["id"] for course in data["results"]], [self.own_draft.id])


class CourseModuleDescriptionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(
            user=self.owner, title="Course", price=0, is_publish=True
        )

    def test_module_returns_description(self):
        module = CourseModule.objects.create(
            course=self.course,
            title="Modul Deskripsi",
            description="Isi deskripsi module.",
        )

        response = self.client.get("/module/", {"course": self.course.id})

        results = response.json()["results"]
        self.assertEqual(results[0]["id"], module.id)
        self.assertEqual(results[0]["description"], "Isi deskripsi module.")

    def test_module_description_defaults_to_empty(self):
        module = CourseModule.objects.create(course=self.course, title="Tanpa Deskripsi")

        response = self.client.get(f"/module/{module.id}/")

        self.assertEqual(response.json()["description"], "")

    def test_module_list_is_ordered_by_sequence(self):
        second = CourseModule.objects.create(
            course=self.course, title="Kedua", sequence=2
        )
        first = CourseModule.objects.create(course=self.course, title="Pertama", sequence=1)

        response = self.client.get("/module/", {"course": self.course.id})

        results = response.json()["results"]
        self.assertEqual(
            [module["id"] for module in results], [first.id, second.id]
        )


class CourseOwnershipTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Original", price=0)

    def test_non_owner_cannot_update_course(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            f"/course/{self.course.id}/", {"title": "Hacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Original")

    def test_non_owner_cannot_delete_course(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.delete(f"/course/{self.course.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_owner_can_update_course(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/course/{self.course.id}/", {"title": "Updated"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Updated")

    def test_owner_can_delete_course(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f"/course/{self.course.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())


class ModuleContentSequenceTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course")
        self.module = CourseModule.objects.create(
            course=self.course, title="M1", module_category=CourseModule.Category.TEXT
        )
        self.other_module = CourseModule.objects.create(
            course=self.course, title="M2", module_category=CourseModule.Category.TEXT
        )

    def test_sequence_auto_assigned_per_module(self):
        first = ModuleContent.objects.create(module=self.module, content_text="<p>1</p>")
        second = ModuleContent.objects.create(module=self.module, content_text="<p>2</p>")
        other = ModuleContent.objects.create(
            module=self.other_module, content_text="<p>other</p>"
        )

        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(other.sequence, 1)

    def test_list_is_ordered_by_sequence(self):
        late = ModuleContent.objects.create(
            module=self.module, content_text="<p>b</p>", sequence=2
        )
        early = ModuleContent.objects.create(
            module=self.module, content_text="<p>a</p>", sequence=1
        )
        last = ModuleContent.objects.create(
            module=self.module, content_text="<p>c</p>", sequence=3
        )

        response = self.client.get(f"/module-content/?module={self.module.id}")

        results = response.json()["results"]
        self.assertEqual(
            [item["id"] for item in results], [early.id, late.id, last.id]
        )

    def test_create_assigns_sequence(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/",
            {"module": self.module.id, "content_text": "<p>x</p>"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["sequence"], 1)

    def test_owner_can_reorder_content_by_patching_sequence(self):
        self.client.force_authenticate(user=self.owner)
        first = ModuleContent.objects.create(module=self.module, content_text="<p>1</p>")
        second = ModuleContent.objects.create(module=self.module, content_text="<p>2</p>")

        first_response = self.client.patch(
            f"/module-content/{first.id}/", {"sequence": 2}, format="json"
        )
        second_response = self.client.patch(
            f"/module-content/{second.id}/", {"sequence": 1}, format="json"
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.sequence, 2)
        self.assertEqual(second.sequence, 1)


class ProgressActivityTests(APITestCase):
    """GET /progress/activity/ — grafik 7 hari + streak belajar (zona WIB)."""

    def setUp(self):
        self.user = User.objects.create_user(username="student", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course A")
        self.module = CourseModule.objects.create(course=self.course, title="M1")
        self.content = ModuleContent.objects.create(
            module=self.module, content_text="<p>isi</p>"
        )
        self.assignment = Assignment.objects.create(
            course_module=self.module, name="A1", description="kerjakan"
        )
        CourseEnrollment.objects.create(course=self.course, user=self.user)
        self.today = timezone.localtime(
            timezone.now(), ACTIVITY_TIME_ZONE
        ).date()
        self.client.force_authenticate(user=self.user)

    @staticmethod
    def at(day):
        """Tengah hari WIB pada `day` — aman dari batas pergantian hari."""
        return datetime.combine(day, time(12, 0), tzinfo=ACTIVITY_TIME_ZONE)

    def activity(self):
        response = self.client.get("/progress/activity/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()

    def mark_views(self, *days):
        """Buat satu konten baru per hari (ContentViewed unik per konten)."""
        for day in days:
            content = ModuleContent.objects.create(
                module=self.module, content_text=f"<p>{day}</p>"
            )
            viewed = ContentViewed.objects.create(user=self.user, content=content)
            ContentViewed.objects.filter(pk=viewed.pk).update(
                viewed_at=self.at(day)
            )

    def test_activity_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/progress/activity/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_seven_days_ending_today_without_activity(self):
        data = self.activity()

        self.assertEqual(len(data["days"]), 7)
        self.assertEqual(data["days"][-1]["date"], self.today.isoformat())
        self.assertEqual(data["days"][-1]["weekday"], self.today.weekday())
        self.assertTrue(all(not entry["active"] for entry in data["days"]))
        self.assertEqual(data["week_active_count"], 0)
        self.assertEqual(data["current_streak"], 0)
        self.assertEqual(data["best_streak"], 0)

    def test_counts_content_view_progress_and_submission(self):
        self.mark_views(self.today)
        UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=self.at(self.today),
        )
        submission = Submission.objects.create(
            user=self.user,
            assignment=self.assignment,
            submission_url="https://example.com/a",
        )
        Submission.objects.filter(pk=submission.pk).update(
            submit_on=self.at(self.today - timedelta(days=1))
        )

        data = self.activity()

        self.assertEqual(data["days"][-1]["count"], 2)
        self.assertTrue(data["days"][-1]["active"])
        self.assertTrue(data["days"][-2]["active"])
        self.assertEqual(data["week_active_count"], 2)
        self.assertEqual(data["current_streak"], 2)

    def test_streak_breaks_on_gap(self):
        self.mark_views(self.today, self.today - timedelta(days=2))

        data = self.activity()

        self.assertEqual(data["current_streak"], 1)
        self.assertEqual(data["best_streak"], 1)

    def test_streak_continues_from_yesterday_when_today_inactive(self):
        self.mark_views(self.today - timedelta(days=1))

        data = self.activity()

        self.assertEqual(data["current_streak"], 1)
        self.assertFalse(data["days"][-1]["active"])

    def test_best_streak_uses_history_beyond_one_week(self):
        self.mark_views(
            self.today - timedelta(days=10),
            self.today - timedelta(days=9),
            self.today - timedelta(days=8),
        )

        data = self.activity()

        self.assertEqual(data["best_streak"], 3)
        self.assertEqual(data["current_streak"], 0)
        self.assertFalse(any(entry["active"] for entry in data["days"]))

    def test_ignores_activity_from_other_users(self):
        viewed = ContentViewed.objects.create(user=self.other, content=self.content)
        ContentViewed.objects.filter(pk=viewed.pk).update(
            viewed_at=self.at(self.today)
        )

        data = self.activity()

        self.assertFalse(data["days"][-1]["active"])
        self.assertEqual(data["current_streak"], 0)


class ProgressAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course P")
        self.module = CourseModule.objects.create(course=self.course, title="M1")
        self.module_2 = CourseModule.objects.create(course=self.course, title="M2")
        self.stranger_course = Course.objects.create(user=self.owner, title="Else")
        self.stranger_module = CourseModule.objects.create(
            course=self.stranger_course, title="SM"
        )
        CourseEnrollment.objects.create(course=self.course, user=self.user)

    def test_progress_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/progress/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_is_scoped_to_own_progress(self):
        self.client.force_authenticate(user=self.user)
        mine = UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )
        UserProgress.objects.create(
            module=self.module,
            user=self.other,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )

        response = self.client.get("/progress/").json()

        self.assertEqual(response["count"], 1)
        self.assertEqual(response["results"][0]["id"], mine.id)

    def test_list_filters_by_course(self):
        self.client.force_authenticate(user=self.user)
        UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )
        other_course = Course.objects.create(user=self.owner, title="Other")
        other_module = CourseModule.objects.create(course=other_course, title="OM")
        UserProgress.objects.create(
            module=other_module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )

        response = self.client.get(f"/progress/?course={self.course.id}").json()

        self.assertEqual(response["count"], 1)
        self.assertEqual(response["results"][0]["module"], self.module.id)

    def test_create_marks_finish_and_is_idempotent(self):
        self.client.force_authenticate(user=self.user)

        first = self.client.post("/progress/", {"module": self.module.id}, format="json")
        second = self.client.post(
            "/progress/", {"module": self.module.id}, format="json"
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            UserProgress.objects.filter(module=self.module, user=self.user).count(), 1
        )
        row = UserProgress.objects.get(module=self.module, user=self.user)
        self.assertEqual(row.status, UserProgress.ProgressStatus.FINISH)
        self.assertIsNotNone(row.complete_at)
        self.assertEqual(first.json()["status"], UserProgress.ProgressStatus.FINISH)

    def test_create_requires_enrollment_in_course(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/progress/", {"module": self.stranger_module.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            UserProgress.objects.filter(
                module=self.stranger_module, user=self.user
            ).count(),
            0,
        )

    def test_create_requires_module(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post("/progress/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy_unmarks_progress(self):
        self.client.force_authenticate(user=self.user)
        row = UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )

        response = self.client.delete(f"/progress/{row.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserProgress.objects.filter(id=row.id).exists())

    def test_destroy_cannot_remove_other_users_progress(self):
        row = UserProgress.objects.create(
            module=self.module,
            user=self.other,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(f"/progress/{row.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(UserProgress.objects.filter(id=row.id).exists())

    def test_update_methods_not_allowed(self):
        self.client.force_authenticate(user=self.user)
        row = UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )

        patch_response = self.client.patch(f"/progress/{row.id}/", {}, format="json")
        put_response = self.client.put(f"/progress/{row.id}/", {}, format="json")

        self.assertEqual(
            patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_summary_counts_percent_for_enrolled_courses(self):
        self.client.force_authenticate(user=self.user)
        UserProgress.objects.create(
            module=self.module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )
        UserProgress.objects.create(
            module=self.module_2,
            user=self.other,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )
        CourseEnrollment.objects.create(course=self.stranger_course, user=self.user)
        UserProgress.objects.create(
            module=self.stranger_module,
            user=self.user,
            status=UserProgress.ProgressStatus.FINISH,
            complete_at=timezone.now(),
        )

        response = self.client.get("/progress/summary/").json()

        by_course = {row["course"]: row for row in response}
        self.assertEqual(len(response), 2)
        self.assertEqual(by_course[self.course.id]["total"], 2)
        self.assertEqual(by_course[self.course.id]["completed"], 1)
        self.assertEqual(by_course[self.course.id]["percent"], 50)
        self.assertEqual(by_course[self.stranger_course.id]["total"], 1)
        self.assertEqual(by_course[self.stranger_course.id]["completed"], 1)
        self.assertEqual(by_course[self.stranger_course.id]["percent"], 100)


class LeaderboardDetailsTests(APITestCase):
    """GET /leaderboard/ (user_name) dan /leaderboard/{id}/details/ (rincian)."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.user = User.objects.create_user(
            username="budi@example.com",
            email="budi@example.com",
            first_name="Budi",
            last_name="Santoso",
            password="secret123",
        )
        self.course = Course.objects.create(user=self.owner, title="Course A")
        self.first = CourseModule.objects.create(course=self.course, title="M1")
        self.second = CourseModule.objects.create(course=self.course, title="M2")
        self.leaderboard = Leaderboard.objects.create(
            user=self.user, course=self.course, total_points=75
        )
        LeaderboardDetail.objects.create(
            leaderboard=self.leaderboard,
            module=self.first,
            description="M1",
            point=25,
        )
        LeaderboardDetail.objects.create(
            leaderboard=self.leaderboard,
            module=self.second,
            description="M2",
            point=50,
        )
        self.client.force_authenticate(user=self.user)

    def test_list_returns_user_name_and_course_title(self):
        response = self.client.get("/leaderboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(
            item
            for item in response.json()["results"]
            if item["id"] == self.leaderboard.id
        )
        self.assertEqual(row["user_name"], "Budi Santoso")
        self.assertEqual(row["course_title"], "Course A")

    def test_user_name_falls_back_to_username(self):
        other = User.objects.create_user(username="other", password="secret123")
        row_id = Leaderboard.objects.create(
            user=other, course=self.course, total_points=10
        ).id

        response = self.client.get("/leaderboard/").json()
        row = next(item for item in response["results"] if item["id"] == row_id)

        self.assertEqual(row["user_name"], "other")

    def test_details_returns_breakdown_ordered_by_module_sequence(self):
        response = self.client.get(f"/leaderboard/{self.leaderboard.id}/details/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            [(row["description"], row["point"]) for row in data],
            [("M1", 25), ("M2", 50)],
        )
        self.assertEqual(
            [row["module"] for row in data], [self.first.id, self.second.id]
        )

    def test_details_unknown_leaderboard_returns_404(self):
        response = self.client.get("/leaderboard/999999/details/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_details_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(f"/leaderboard/{self.leaderboard.id}/details/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyLeaderboardTests(APITestCase):
    """GET /leaderboard/me/ — ringkasan poin milik sendiri lintas course."""

    def setUp(self):
        self.user = User.objects.create_user(username="student", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course A")
        self.course_b = Course.objects.create(user=self.owner, title="Course B")
        CourseEnrollment.objects.create(course=self.course, user=self.user)
        CourseEnrollment.objects.create(course=self.course_b, user=self.user)
        self.client.force_authenticate(user=self.user)

    def mine_in(self, data, course_id):
        return next(row for row in data["courses"] if row["course"] == course_id)

    def test_me_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/leaderboard/me/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_lists_enrolled_courses_without_points(self):
        response = self.client.get("/leaderboard/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total_points"], 0)
        self.assertEqual(
            [(row["course"], row["course_title"]) for row in data["courses"]],
            [(self.course.id, "Course A"), (self.course_b.id, "Course B")],
        )
        self.assertTrue(all(row["total_points"] == 0 for row in data["courses"]))
        self.assertTrue(all(row["rank"] is None for row in data["courses"]))
        self.assertTrue(all(row["participants"] == 0 for row in data["courses"]))

    def test_me_reports_rank_and_participants(self):
        Leaderboard.objects.create(user=self.other, course=self.course, total_points=300)
        Leaderboard.objects.create(user=self.owner, course=self.course, total_points=100)
        Leaderboard.objects.create(user=self.user, course=self.course, total_points=200)

        mine = self.mine_in(self.client.get("/leaderboard/me/").json(), self.course.id)

        self.assertEqual(mine["course_title"], "Course A")
        self.assertEqual(mine["total_points"], 200)
        self.assertEqual(mine["rank"], 2)
        self.assertEqual(mine["participants"], 3)

    def test_me_ties_break_by_leaderboard_id(self):
        Leaderboard.objects.create(user=self.other, course=self.course, total_points=100)
        Leaderboard.objects.create(user=self.user, course=self.course, total_points=100)

        mine = self.mine_in(self.client.get("/leaderboard/me/").json(), self.course.id)

        self.assertEqual(mine["rank"], 2)

    def test_me_sums_points_across_courses_and_sorts_desc(self):
        Leaderboard.objects.create(user=self.user, course=self.course, total_points=50)
        Leaderboard.objects.create(user=self.user, course=self.course_b, total_points=250)

        data = self.client.get("/leaderboard/me/").json()

        self.assertEqual(data["total_points"], 300)
        self.assertEqual(
            [row["course"] for row in data["courses"]],
            [self.course_b.id, self.course.id],
        )

    def test_me_ignores_courses_not_enrolled(self):
        stranger_course = Course.objects.create(user=self.owner, title="Else")
        Leaderboard.objects.create(user=self.user, course=stranger_course, total_points=999)

        data = self.client.get("/leaderboard/me/").json()

        self.assertEqual(data["total_points"], 0)
        self.assertNotIn(
            stranger_course.id, [row["course"] for row in data["courses"]]
        )


class LeaderboardPointsTests(APITestCase):
    """Poin module diselesaikan → akumulasi ke tabel leaderboard (per course)."""

    def setUp(self):
        self.user = User.objects.create_user(username="student", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course L")
        self.module = CourseModule.objects.create(
            course=self.course, title="M1", point=150
        )
        self.module_2 = CourseModule.objects.create(
            course=self.course, title="M2", point=200
        )
        CourseEnrollment.objects.create(course=self.course, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_complete_module_awards_points_and_detail(self):
        response = self.client.post(
            "/progress/", {"module": self.module.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 150)
        detail = LeaderboardDetail.objects.get(leaderboard=leaderboard)
        self.assertEqual(detail.module, self.module)
        self.assertEqual(detail.description, "M1")
        self.assertEqual(detail.point, 150)

    def test_repeat_complete_does_not_double_points(self):
        self.client.post("/progress/", {"module": self.module.id}, format="json")
        self.client.post("/progress/", {"module": self.module.id}, format="json")

        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 150)
        self.assertEqual(
            LeaderboardDetail.objects.filter(leaderboard=leaderboard).count(), 1
        )

    def test_multiple_completed_modules_sum_points(self):
        self.client.post("/progress/", {"module": self.module.id}, format="json")
        self.client.post("/progress/", {"module": self.module_2.id}, format="json")

        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 350)
        self.assertEqual(
            LeaderboardDetail.objects.filter(leaderboard=leaderboard).count(), 2
        )

    def test_unmark_reduces_points_and_removes_detail(self):
        created = self.client.post(
            "/progress/", {"module": self.module.id}, format="json"
        ).json()

        response = self.client.delete(f"/progress/{created['id']}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 0)
        self.assertFalse(LeaderboardDetail.objects.filter(leaderboard=leaderboard))

    def test_unmark_then_remark_awards_once(self):
        created = self.client.post(
            "/progress/", {"module": self.module.id}, format="json"
        ).json()
        self.client.delete(f"/progress/{created['id']}/")
        self.client.post("/progress/", {"module": self.module.id}, format="json")

        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 150)
        self.assertEqual(
            LeaderboardDetail.objects.filter(leaderboard=leaderboard).count(), 1
        )

    def test_unenrolled_create_rejected_without_leaderboard_row(self):
        stranger = User.objects.create_user(username="stranger", password="secret123")
        self.client.force_authenticate(user=stranger)

        response = self.client.post(
            "/progress/", {"module": self.module.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Leaderboard.objects.filter(user=stranger, course=self.course).exists()
        )

    def test_submission_create_awards_points(self):
        """Module upload memberi poin leaderboard dari skor submission:
        0 sebelum dinilai, naik setelah mentor menilai."""
        upload_module = CourseModule.objects.create(
            course=self.course, title="Upload", module_category="upload", point=150
        )
        assignment = Assignment.objects.create(
            course_module=upload_module, name="A1", description="do it"
        )

        response = self.client.post(
            "/submission/",
            {
                "assignment": assignment.id,
                "submission_url": "https://example.com/task.pdf",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 0)

        submission_id = response.json()["id"]
        self.client.force_authenticate(user=self.owner)
        patch_response = self.client.patch(
            f"/submission/{submission_id}/", {"score": 150}, format="json"
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)

        leaderboard.refresh_from_db()
        self.assertEqual(leaderboard.total_points, 150)

    def test_leaderboard_write_methods_not_allowed(self):
        row = Leaderboard.objects.create(
            course=self.course, user=self.user, total_points=150
        )

        create_response = self.client.post(
            "/leaderboard/",
            {"course": self.course.id, "user": self.other.id, "total_points": 9999},
            format="json",
        )
        patch_response = self.client.patch(
            f"/leaderboard/{row.id}/", {"total_points": 9999}, format="json"
        )
        delete_response = self.client.delete(f"/leaderboard/{row.id}/")

        self.assertEqual(
            create_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            delete_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        row.refresh_from_db()
        self.assertEqual(row.total_points, 150)

    def test_leaderboard_list_ordered_by_points_desc(self):
        Leaderboard.objects.create(course=self.course, user=self.other, total_points=50)
        Leaderboard.objects.create(course=self.course, user=self.user, total_points=300)

        response = self.client.get(f"/leaderboard/?course={self.course.id}").json()

        self.assertEqual(response["count"], 2)
        self.assertEqual(response["results"][0]["user"], self.user.id)
        self.assertEqual(response["results"][0]["total_points"], 300)
        self.assertEqual(response["results"][1]["user"], self.other.id)


class ContentViewTests(APITestCase):
    """POST /content-view/ - auto-complete module text/video hanya setelah
    seluruh konten dibuka; poin leaderboard ikut tersinkron."""

    def setUp(self):
        self.user = User.objects.create_user(username="viewer", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course CV")
        self.text_module = CourseModule.objects.create(
            course=self.course, title="Text", module_category="text", point=150
        )
        self.content_a = ModuleContent.objects.create(
            module=self.text_module, content_text="<p>A</p>"
        )
        self.content_b = ModuleContent.objects.create(
            module=self.text_module, content_text="<p>B</p>"
        )
        self.video_module = CourseModule.objects.create(
            course=self.course, title="Video", module_category="video", point=50
        )
        self.video_content = ModuleContent.objects.create(
            module=self.video_module, content_url="https://youtu.be/x"
        )
        self.upload_module = CourseModule.objects.create(
            course=self.course, title="Tugas", module_category="upload", point=70
        )
        self.upload_content = ModuleContent.objects.create(
            module=self.upload_module, content_url="https://example.com/brief"
        )
        self.quiz_module = CourseModule.objects.create(
            course=self.course, title="Kuis", module_category="quiz", point=30
        )
        self.quiz_content = ModuleContent.objects.create(
            module=self.quiz_module, content_url="https://example.com/syarat"
        )
        CourseEnrollment.objects.create(course=self.course, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_mark_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(f"/content-view/{self.content_a.id}/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_first_content_does_not_finish_multi_content_module(self):
        response = self.client.post(f"/content-view/{self.content_a.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["module_completed"])
        self.assertTrue(
            ContentViewed.objects.filter(user=self.user, content=self.content_a).exists()
        )
        self.assertFalse(
            UserProgress.objects.filter(
                module=self.text_module, user=self.user
            ).exists()
        )

    def test_last_content_finishes_module_and_syncs_leaderboard(self):
        self.client.post(f"/content-view/{self.content_a.id}/")

        response = self.client.post(f"/content-view/{self.content_b.id}/")

        self.assertTrue(response.json()["module_completed"])
        row = UserProgress.objects.get(module=self.text_module, user=self.user)
        self.assertEqual(row.status, UserProgress.ProgressStatus.FINISH)
        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 150)

    def test_mark_is_idempotent(self):
        first = self.client.post(f"/content-view/{self.content_a.id}/")
        second = self.client.post(f"/content-view/{self.content_a.id}/")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.json()["module_completed"])
        self.assertEqual(
            ContentViewed.objects.filter(user=self.user, content=self.content_a).count(),
            1,
        )

    def test_single_content_video_module_completes_on_first_open(self):
        response = self.client.post(f"/content-view/{self.video_content.id}/")

        self.assertTrue(response.json()["module_completed"])
        row = UserProgress.objects.get(module=self.video_module, user=self.user)
        self.assertEqual(row.status, UserProgress.ProgressStatus.FINISH)
        leaderboard = Leaderboard.objects.get(user=self.user, course=self.course)
        self.assertEqual(leaderboard.total_points, 50)

    def test_upload_module_never_auto_completes(self):
        response = self.client.post(f"/content-view/{self.upload_content.id}/")

        self.assertFalse(response.json()["module_completed"])
        self.assertFalse(
            UserProgress.objects.filter(
                module=self.upload_module, user=self.user
            ).exists()
        )

    def test_quiz_module_never_auto_completes(self):
        response = self.client.post(f"/content-view/{self.quiz_content.id}/")

        self.assertFalse(response.json()["module_completed"])
        self.assertFalse(
            UserProgress.objects.filter(module=self.quiz_module, user=self.user).exists()
        )

    def test_unenrolled_user_records_viewed_without_progress(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(f"/content-view/{self.content_a.id}/")

        self.assertFalse(response.json()["module_completed"])
        self.assertTrue(
            ContentViewed.objects.filter(user=self.other, content=self.content_a).exists()
        )
        self.assertFalse(
            UserProgress.objects.filter(module=self.text_module, user=self.other).exists()
        )
        self.assertFalse(
            Leaderboard.objects.filter(user=self.other, course=self.course).exists()
        )

    def test_list_returns_own_viewed_ids_scoped_by_course(self):
        self.client.post(f"/content-view/{self.content_a.id}/")
        ContentViewed.objects.create(user=self.other, content=self.content_b)

        response = self.client.get(
            f"/content-view/?course={self.course.id}"
        ).json()

        self.assertEqual(response["content_ids"], [self.content_a.id])


def make_choice_question(module, text, correct_index=0, labels=("A", "B")):
    question = Question.objects.create(
        module=module, question_text=text, question_type="choices"
    )
    for index, label in enumerate(labels):
        QuestionOption.objects.create(
            question=question,
            option_text=label,
            is_correct=index == correct_index,
        )
    return question


def make_boolean_question(module, text, correct_is_true=True):
    question = Question.objects.create(
        module=module, question_text=text, question_type="boolean"
    )
    QuestionOption.objects.create(
        question=question, option_text="Benar", is_correct=correct_is_true
    )
    QuestionOption.objects.create(
        question=question, option_text="Salah", is_correct=not correct_is_true
    )
    return question


def make_essay_question(module, text):
    return Question.objects.create(
        module=module, question_text=text, question_type="essai"
    )


class QuizWeightsUnitTests(SimpleTestCase):
    """Pembagian `module.point` per soal — bagian essay ditahan mentor."""

    def test_weights_sum_to_module_point(self):
        module = CourseModule(course_id=None, point=100)
        questions = [
            SimpleNamespace(is_essay=False),
            SimpleNamespace(is_essay=False),
            SimpleNamespace(is_essay=False),
            SimpleNamespace(is_essay=True),
        ]

        weights = split_points(module, questions)

        self.assertEqual(weights.total, 4)
        self.assertEqual(weights.auto_count, 3)
        self.assertEqual(weights.essay_count, 1)
        self.assertEqual(weights.auto_max, 75)
        self.assertEqual(weights.essay_max, 25)
        self.assertEqual(weights.auto_max + weights.essay_max, module.point)

    def test_auto_only_module_scores_full_point(self):
        module = CourseModule(course_id=None, point=90)
        questions = [SimpleNamespace(is_essay=False) for _ in range(3)]

        weights = split_points(module, questions)

        self.assertEqual(weights.essay_max, 0)
        self.assertEqual(weights.auto_max, 90)
        self.assertEqual(compute_auto_score(weights, correct_count=2), 60)

    def test_essay_only_module_has_no_auto_part(self):
        module = CourseModule(course_id=None, point=50)
        questions = [SimpleNamespace(is_essay=True) for _ in range(2)]

        weights = split_points(module, questions)

        self.assertEqual(weights.auto_count, 0)
        self.assertEqual(weights.auto_max, 0)
        self.assertEqual(weights.essay_max, 50)
        self.assertEqual(compute_auto_score(weights, correct_count=0), 0)


class AssignmentOwnershipTests(APITestCase):
    """Assignment module upload dibuat/dikelola mentor (pemilik course)."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course AO")
        self.module = CourseModule.objects.create(
            course=self.course, title="Tugas", module_category="upload"
        )
        self.payload = {
            "course_module": self.module.id,
            "name": "Tugas 1",
            "description": "Kumpulkan tautan hasil kerja.",
        }

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/assignment/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_can_list_assignments(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(f"/assignment/?course_module={self.module.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_non_owner_cannot_create_assignment(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post("/assignment/", self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Assignment.objects.filter(course_module=self.module).exists())

    def test_owner_creates_assignment(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post("/assignment/", self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["name"], "Tugas 1")

    def test_non_owner_cannot_update_assignment(self):
        assignment = Assignment.objects.create(
            course_module=self.module, name="A1", description="d"
        )
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            f"/assignment/{assignment.id}/", {"name": "Hack"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assignment.refresh_from_db()
        self.assertEqual(assignment.name, "A1")

    def test_owner_updates_and_deletes_assignment(self):
        assignment = Assignment.objects.create(
            course_module=self.module, name="A1", description="d"
        )
        self.client.force_authenticate(user=self.owner)

        patch_response = self.client.patch(
            f"/assignment/{assignment.id}/", {"name": "A2"}, format="json"
        )
        delete_response = self.client.delete(f"/assignment/{assignment.id}/")

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Assignment.objects.filter(pk=assignment.id).exists())


class UploadSubmissionFlowTests(APITestCase):
    """Module upload = tempat mengumpulkan tautan tugas, dinilai mentor
    dengan skor maksimal poin module."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.student = User.objects.create_user(
            username="student", password="secret123"
        )
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course U")
        self.upload_module = CourseModule.objects.create(
            course=self.course, title="Tugas", module_category="upload", point=100
        )
        self.text_module = CourseModule.objects.create(
            course=self.course, title="Materi", module_category="text", point=100
        )
        self.quiz_module = CourseModule.objects.create(
            course=self.course, title="Kuis", module_category="quiz", point=100
        )
        self.assignment = Assignment.objects.create(
            course_module=self.upload_module, name="Tugas 1", description="d"
        )
        self.text_assignment = Assignment.objects.create(
            course_module=self.text_module, name="A-teks", description="d"
        )
        CourseEnrollment.objects.create(course=self.course, user=self.student)
        self.client.force_authenticate(user=self.student)

    def submit_payload(self, url="https://example.com/hasil.pdf", assignment=None):
        return {
            "assignment": (assignment or self.assignment).id,
            "submission_url": url,
        }

    def test_create_submission(self):
        response = self.client.post("/submission/", self.submit_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["score"], 0)
        self.assertFalse(data["is_graded"])
        self.assertFalse(data["is_quiz"])
        self.assertEqual(data["module"], self.upload_module.id)
        self.assertEqual(data["max_score"], 100)
        self.assertEqual(data["user_name"], "student")

    def test_resubmit_updates_single_row(self):
        first = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        )
        second = self.client.post(
            "/submission/", self.submit_payload(url="https://example.com/v2.pdf"),
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Submission.objects.filter(assignment=self.assignment).count(), 1
        )
        submission = Submission.objects.get(assignment=self.assignment)
        self.assertEqual(submission.submission_url, "https://example.com/v2.pdf")

    def test_resubmit_rejected_after_graded(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.owner)
        self.client.patch(f"/submission/{created['id']}/", {"score": 80}, format="json")

        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submission_url_required(self):
        response = self.client.post(
            "/submission/", {"assignment": self.assignment.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_upload_modules_accept_submissions(self):
        response = self.client.post(
            "/submission/", self.submit_payload(assignment=self.text_assignment),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Submission.objects.filter(assignment=self.text_assignment).exists()
        )

    def test_student_can_update_own_url_before_graded(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()

        response = self.client.patch(
            f"/submission/{created['id']}/",
            {"submission_url": "https://example.com/baru.pdf"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Submission.objects.get(pk=created["id"]).submission_url,
            "https://example.com/baru.pdf",
        )

    def test_student_cannot_grade_own_submission(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()

        response = self.client.patch(
            f"/submission/{created['id']}/", {"score": 100}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Submission.objects.get(pk=created["id"]).score, 0)

    def test_non_owner_cannot_grade(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            f"/submission/{created['id']}/", {"score": 100}, format="json"
        )

        # submission course lain tidak terlihat → tidak bocor ke-403/404
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_grades_with_score_limit_and_reviewer(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.owner)

        too_high = self.client.patch(
            f"/submission/{created['id']}/", {"score": 101}, format="json"
        )
        negative = self.client.patch(
            f"/submission/{created['id']}/", {"score": -1}, format="json"
        )
        valid = self.client.patch(
            f"/submission/{created['id']}/", {"score": 85}, format="json"
        )

        self.assertEqual(too_high.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(negative.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valid.status_code, status.HTTP_200_OK)
        submission = Submission.objects.get(pk=created["id"])
        self.assertEqual(submission.score, 85)
        self.assertEqual(submission.reviewed_by, "owner")
        self.assertTrue(valid.json()["is_graded"])

    def test_student_cannot_edit_after_graded(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.owner)
        self.client.patch(f"/submission/{created['id']}/", {"score": 50}, format="json")

        self.client.force_authenticate(user=self.student)
        response = self.client.patch(
            f"/submission/{created['id']}/",
            {"submission_url": "https://example.com/ganti.pdf"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_grade_via_extra_fields(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()

        response = self.client.patch(
            f"/submission/{created['id']}/",
            {"submission_url": "https://example.com/x.pdf", "score": 99},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submission_visibility_scoped_to_own_and_own_course(self):
        mine = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.other)
        stranger_view = self.client.get("/submission/").json()
        Submission.objects.create(
            user=self.other,
            assignment=self.assignment,
            submission_url="https://example.com/other.pdf",
        )

        self.client.force_authenticate(user=self.owner)
        owner_view = self.client.get("/submission/").json()
        self.client.force_authenticate(user=self.student)
        student_view = self.client.get("/submission/").json()

        self.assertEqual(stranger_view["count"], 0)
        self.assertEqual(owner_view["count"], 2)
        self.assertEqual(student_view["count"], 1)
        self.assertEqual(student_view["results"][0]["id"], mine["id"])

    def test_graded_filter(self):
        created = self.client.post(
            "/submission/", self.submit_payload(), format="json"
        ).json()
        self.client.force_authenticate(user=self.owner)
        self.client.patch(f"/submission/{created['id']}/", {"score": 10}, format="json")

        pending = self.client.get("/submission/?graded=false").json()
        graded = self.client.get("/submission/?graded=true").json()

        self.assertEqual(pending["count"], 0)
        self.assertEqual(graded["count"], 1)

    def test_manual_progress_blocked_for_upload_and_quiz(self):
        upload_progress = self.client.post(
            "/progress/", {"module": self.upload_module.id}, format="json"
        )
        quiz_progress = self.client.post(
            "/progress/", {"module": self.quiz_module.id}, format="json"
        )

        self.assertEqual(upload_progress.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(quiz_progress.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserProgress.objects.filter(user=self.student).exists())


class QuestionAPITests(APITestCase):
    """Soal + opsi quiz dikelola pemilik course; kunci jawaban disembunyikan
    dari student sampai hasil final."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course Q")
        self.quiz_module = CourseModule.objects.create(
            course=self.course, title="Kuis", module_category="quiz", point=100
        )
        self.text_module = CourseModule.objects.create(
            course=self.course, title="Materi", module_category="text", point=100
        )

    def payload(self, **overrides):
        body = {
            "module": self.quiz_module.id,
            "question_text": "2 + 2 = ?",
            "question_type": "choices",
            "explanation": "Karena 2+2=4.",
            "options": [
                {"option_text": "4", "is_correct": True},
                {"option_text": "5", "is_correct": False},
            ],
        }
        body.update(overrides)
        return body

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/question/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_creates_question_with_nested_options(self):
        self.client.force_authenticate(user=self.owner)

        first = self.client.post("/question/", self.payload(), format="json")
        second = self.client.post(
            "/question/", self.payload(question_text="3 + 3?"), format="json"
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        data = first.json()
        self.assertEqual(len(data["options"]), 2)
        self.assertEqual(data["sequence"], 1)
        self.assertEqual(second.json()["sequence"], 2)

    def test_non_owner_cannot_create_question(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post("/question/", self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Question.objects.filter(module=self.quiz_module).exists())

    def test_student_list_hides_correctness_and_explanation(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post("/question/", self.payload(), format="json").json()
        self.client.force_authenticate(user=self.other)

        response = self.client.get(
            f"/question/?module={self.quiz_module.id}"
        ).json()

        self.assertEqual(response["count"], 1)
        item = response["results"][0]
        self.assertEqual(item["id"], created["id"])
        self.assertEqual(item["explanation"], "")
        for option in item["options"]:
            self.assertNotIn("is_correct", option)

    def test_owner_list_reveals_correctness(self):
        self.client.force_authenticate(user=self.owner)
        self.client.post("/question/", self.payload(), format="json")

        item = self.client.get(
            f"/question/?module={self.quiz_module.id}"
        ).json()["results"][0]

        self.assertEqual(item["explanation"], "Karena 2+2=4.")
        self.assertTrue(item["options"][0]["is_correct"])

    def test_question_requires_min_two_options(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/",
            self.payload(options=[{"option_text": "4", "is_correct": True}]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_question_requires_exactly_one_correct_option(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/",
            self.payload(
                options=[
                    {"option_text": "4", "is_correct": True},
                    {"option_text": "5", "is_correct": True},
                ]
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_boolean_question_requires_exactly_two_options(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/",
            self.payload(
                question_type="boolean",
                options=[
                    {"option_text": "Benar", "is_correct": True},
                    {"option_text": "Salah", "is_correct": False},
                    {"option_text": "Tidak", "is_correct": False},
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_essay_question_rejects_options(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/", self.payload(question_type="essai"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_essay_question_without_options_is_valid(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/",
            self.payload(question_type="essai", options=[]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_question_only_allowed_on_quiz_module(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/question/", self.payload(module=self.text_module.id), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_question_locked_after_attempt(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post("/question/", self.payload(), format="json").json()
        student = User.objects.create_user(username="s2", password="secret123")
        CourseEnrollment.objects.create(course=self.course, user=student)
        submission = Submission.objects.create(
            user=student, assignment=None, submission_url=""
        )
        option = QuestionOption.objects.filter(question_id=created["id"]).first()
        UserAnswer.objects.create(
            submission=submission,
            question_id=created["id"],
            question_option=option,
        )

        patch_response = self.client.patch(
            f"/question/{created['id']}/", {"question_text": "Diubah"}, format="json"
        )
        delete_response = self.client.delete(f"/question/{created['id']}/")

        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Question.objects.filter(pk=created["id"]).exists())

    def test_quiz_module_rejects_module_content(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/module-content/",
            {"module": self.quiz_module.id, "content_text": "<p>brief</p>"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ModuleContent.objects.filter(module=self.quiz_module).exists())


class QuizFlowTests(APITestCase):
    """Alur quiz: start (draft) → jawab per soal → submit → skor otomatis."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.student = User.objects.create_user(
            username="student", password="secret123"
        )
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course Z")
        self.quiz = CourseModule.objects.create(
            course=self.course, title="Kuis", module_category="quiz", point=100
        )
        # 4 soal pilihan (bobot masing-masing 25)
        self.q1 = make_choice_question(self.quiz, "Q1", correct_index=0)
        self.q2 = make_choice_question(self.quiz, "Q2", correct_index=1)
        self.q3 = make_boolean_question(self.quiz, "Q3", correct_is_true=True)
        self.q4 = make_boolean_question(self.quiz, "Q4", correct_is_true=False)
        CourseEnrollment.objects.create(course=self.course, user=self.student)
        self.client.force_authenticate(user=self.student)

    def start(self, module_id=None):
        return self.client.post(
            f"/module/{module_id or self.quiz.id}/quiz/start/", {}, format="json"
        )

    def answer(self, submission_id, question, option=None, text=""):
        body = {"submission": submission_id, "question": question.pk}
        if option is not None:
            body["question_option"] = option.pk
        if text:
            body["answer_text"] = text
        return self.client.post("/user-answer/", body, format="json")

    def submit(self, submission_id, module_id=None):
        return self.client.post(
            f"/module/{module_id or self.quiz.id}/quiz/submit/",
            {"submission": submission_id},
            format="json",
        )

    def correct_option(self, question, chosen_index=0):
        return question.questionoption_set.order_by("sequence")[chosen_index]

    def test_start_creates_resumable_draft(self):
        first = self.start()
        second = self.start()

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertFalse(first.json()["completed"])
        self.assertEqual(first.json()["submission"]["id"], second.json()["submission"]["id"])
        self.assertEqual(
            Submission.objects.filter(user=self.student, assignment=None).count(), 1
        )

    def test_start_requires_enrollment(self):
        self.client.force_authenticate(user=self.other)

        response = self.start()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_requires_existing_questions(self):
        empty_quiz = CourseModule.objects.create(
            course=self.course, title="Kosong", module_category="quiz", point=10
        )

        response = self.start(empty_quiz.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_rejects_non_quiz_module(self):
        text_module = CourseModule.objects.create(
            course=self.course, title="Materi", module_category="text"
        )

        response = self.start(text_module.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_questions_hidden_before_submit(self):
        data = self.start().json()

        for question in data["questions"]:
            self.assertEqual(question["explanation"], "")
            for option in question["options"]:
                self.assertNotIn("is_correct", option)

    def test_answer_upserts_single_row(self):
        submission_id = self.start().json()["submission"]["id"]
        first_option = self.correct_option(self.q1, 0)
        second_option = self.correct_option(self.q1, 1)

        first = self.answer(submission_id, self.q1, option=first_option)
        second = self.answer(submission_id, self.q1, option=second_option)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        answers = UserAnswer.objects.filter(submission_id=submission_id)
        self.assertEqual(answers.count(), 1)
        self.assertEqual(answers.first().question_option, second_option)

    def test_choices_answer_requires_option(self):
        submission_id = self.start().json()["submission"]["id"]

        response = self.answer(submission_id, self.q1)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_answer_option_must_belong_to_question(self):
        submission_id = self.start().json()["submission"]["id"]
        foreign_option = self.correct_option(self.q2, 0)

        response = self.answer(submission_id, self.q1, option=foreign_option)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_answer_someone_elses_submission(self):
        submission_id = self.start().json()["submission"]["id"]
        self.client.force_authenticate(user=self.other)

        response = self.answer(submission_id, self.q1, option=self.correct_option(self.q1))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_rejected_until_all_answered(self):
        submission_id = self.start().json()["submission"]["id"]
        self.answer(submission_id, self.q1, option=self.correct_option(self.q1, 0))
        self.answer(submission_id, self.q2, option=self.correct_option(self.q2, 1))

        response = self.submit(submission_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errors = response.json()["errors"]
        self.assertIn("Lengkapi semua jawaban", str(errors))
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.reviewed_by, "")

    def answer_all_correctly(self, submission_id):
        self.answer(submission_id, self.q1, option=self.correct_option(self.q1, 0))
        self.answer(submission_id, self.q2, option=self.correct_option(self.q2, 1))
        self.answer(submission_id, self.q3, option=self.correct_option(self.q3, 0))
        self.answer(submission_id, self.q4, option=self.correct_option(self.q4, 1))

    def test_submit_scores_correct_answers_and_finishes_module(self):
        submission_id = self.start().json()["submission"]["id"]
        self.answer_all_correctly(submission_id)

        response = self.submit(submission_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["completed"])
        self.assertIs(data["result"]["pending"], False)
        self.assertEqual(data["result"]["score"], 100)
        self.assertEqual(data["result"]["max_score"], 100)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.score, 100)
        self.assertEqual(submission.reviewed_by, "system")
        progress = UserProgress.objects.get(module=self.quiz, user=self.student)
        self.assertEqual(progress.status, UserProgress.ProgressStatus.FINISH)
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 100)

    def test_partial_correct_answers_score_proportionally(self):
        submission_id = self.start().json()["submission"]["id"]
        self.answer(submission_id, self.q1, option=self.correct_option(self.q1, 0))
        self.answer(submission_id, self.q2, option=self.correct_option(self.q2, 1))
        self.answer(submission_id, self.q3, option=self.correct_option(self.q3, 0))
        self.answer(submission_id, self.q4, option=self.correct_option(self.q4, 0))

        response = self.submit(submission_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["result"]["correct"], 3)
        self.assertEqual(response.json()["result"]["score"], 75)

    def test_questions_revealed_after_submit(self):
        submission_id = self.start().json()["submission"]["id"]
        self.answer_all_correctly(submission_id)

        data = self.submit(submission_id).json()

        for question in data["questions"]:
            self.assertIn("is_correct", question["options"][0])

    def test_retake_blocked_after_submit(self):
        submission_id = self.start().json()["submission"]["id"]
        self.answer_all_correctly(submission_id)
        self.submit(submission_id)

        second_submit = self.submit(submission_id)
        restart = self.start()

        self.assertEqual(second_submit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(restart.status_code, status.HTTP_200_OK)
        self.assertTrue(restart.json()["completed"])
        self.assertEqual(restart.json()["submission"]["id"], submission_id)
        self.assertEqual(
            Submission.objects.filter(user=self.student, assignment=None).count(), 1
        )

    def test_submit_rejects_non_quiz_module(self):
        text_module = CourseModule.objects.create(
            course=self.course, title="Materi", module_category="text"
        )
        submission_id = self.start().json()["submission"]["id"]

        response = self.submit(submission_id, module_id=text_module.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unanswered_draft_is_adopted_not_duplicated(self):
        first = self.start()
        other_quiz = CourseModule.objects.create(
            course=self.course, title="Kuis 2", module_category="quiz", point=50
        )
        make_choice_question(other_quiz, "X1")

        switch = self.start(other_quiz.id)
        back = self.start()

        self.assertEqual(switch.json()["submission"]["id"], first.json()["submission"]["id"])
        self.assertEqual(back.json()["submission"]["id"], first.json()["submission"]["id"])
        self.assertEqual(
            Submission.objects.filter(user=self.student, assignment=None).count(), 1
        )


class EssayQuizGradingTests(APITestCase):
    """Quiz ber-essay: skor otomatis ditahan, mentor menilai essay → final."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.student = User.objects.create_user(
            username="student", password="secret123"
        )
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Course E")
        self.quiz = CourseModule.objects.create(
            course=self.course, title="Kuis Essay", module_category="quiz", point=100
        )
        # 3 pilihan (auto_max 75) + 1 essay (essay_max 25)
        self.q1 = make_choice_question(self.quiz, "Q1", correct_index=0)
        self.q2 = make_choice_question(self.quiz, "Q2", correct_index=0)
        self.q3 = make_choice_question(self.quiz, "Q3", correct_index=0)
        self.essay = make_essay_question(self.quiz, "Jelaskan konsepnya.")
        CourseEnrollment.objects.create(course=self.course, user=self.student)
        self.client.force_authenticate(user=self.student)

    def submit_pending_quiz(self):
        start = self.client.post(
            f"/module/{self.quiz.id}/quiz/start/", {}, format="json"
        ).json()
        submission_id = start["submission"]["id"]
        for question in (self.q1, self.q2, self.q3):
            option = question.questionoption_set.order_by("sequence").first()
            self.client.post(
                "/user-answer/",
                {
                    "submission": submission_id,
                    "question": question.pk,
                    "question_option": option.pk,
                },
                format="json",
            )
        self.client.post(
            "/user-answer/",
            {
                "submission": submission_id,
                "question": self.essay.pk,
                "answer_text": "Konsepnya begini.",
            },
            format="json",
        )
        response = self.client.post(
            f"/module/{self.quiz.id}/quiz/submit/",
            {"submission": submission_id},
            format="json",
        )
        return submission_id, response

    def grade(self, submission_id, answers, user=None):
        self.client.force_authenticate(user=user or self.owner)
        return self.client.post(
            f"/submission/{submission_id}/grade-essay/",
            {"answers": answers},
            format="json",
        )

    def test_essay_quiz_stays_pending_after_submit(self):
        submission_id, response = self.submit_pending_quiz()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["result"]["pending"])
        self.assertEqual(data["result"]["auto_score"], 75)
        self.assertEqual(data["result"]["essay_max"], 25)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.score, 75)
        self.assertEqual(submission.reviewed_by, "")
        self.assertFalse(response.json()["submission"]["is_graded"])
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 75)

    def test_grade_essay_finalizes_score(self):
        submission_id, _ = self.submit_pending_quiz()
        essay_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.essay
        )

        response = self.grade(submission_id, [{"id": essay_answer.pk, "score": 25}])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["score"], 100)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.score, 100)
        self.assertEqual(submission.reviewed_by, "owner")
        essay_answer.refresh_from_db()
        self.assertEqual(essay_answer.score, 25)
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 100)

    def test_grade_essay_rejects_total_over_module_point(self):
        submission_id, _ = self.submit_pending_quiz()
        essay_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.essay
        )

        response = self.grade(submission_id, [{"id": essay_answer.pk, "score": 26}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.score, 75)
        self.assertEqual(submission.reviewed_by, "")

    def test_grade_essay_rejects_non_essay_answer(self):
        submission_id, _ = self.submit_pending_quiz()
        choice_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.q1
        )

        response = self.grade(submission_id, [{"id": choice_answer.pk, "score": 10}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_grade_essay_rejects_empty_payload(self):
        submission_id, _ = self.submit_pending_quiz()

        response = self.grade(submission_id, [])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_grade_essay_denied_for_non_owner(self):
        submission_id, _ = self.submit_pending_quiz()
        essay_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.essay
        )

        response = self.grade(
            submission_id, [{"id": essay_answer.pk, "score": 25}], user=self.other
        )

        # submission course lain tidak terlihat → tidak bocor ke-403
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Submission.objects.get(pk=submission_id).score, 75)

    def test_grade_essay_is_idempotent_on_regrade(self):
        submission_id, _ = self.submit_pending_quiz()
        essay_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.essay
        )

        first = self.grade(submission_id, [{"id": essay_answer.pk, "score": 25}])
        second = self.grade(submission_id, [{"id": essay_answer.pk, "score": 25}])

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Submission.objects.get(pk=submission_id).score, 100)

    def test_grade_essay_rejected_for_upload_submission(self):
        assignment = Assignment.objects.create(
            course_module=CourseModule.objects.create(
                course=self.course, title="Tugas", module_category="upload"
            ),
            name="A1",
            description="d",
        )
        upload_submission = Submission.objects.create(
            user=self.student, assignment=assignment, submission_url="https://x.com/a"
        )

        response = self.grade(upload_submission.pk, [{"id": 1, "score": 5}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_grade_essay_rejected_before_submit(self):
        start = self.client.post(
            f"/module/{self.quiz.id}/quiz/start/", {}, format="json"
        ).json()
        submission_id = start["submission"]["id"]
        for question in (self.q1, self.q2, self.q3):
            option = question.questionoption_set.order_by("sequence").first()
            self.client.post(
                "/user-answer/",
                {
                    "submission": submission_id,
                    "question": question.pk,
                    "question_option": option.pk,
                },
                format="json",
            )
        self.client.post(
            "/user-answer/",
            {
                "submission": submission_id,
                "question": self.essay.pk,
                "answer_text": "Belum disubmit.",
            },
            format="json",
        )
        essay_answer = UserAnswer.objects.get(
            submission_id=submission_id, question=self.essay
        )

        response = self.grade(submission_id, [{"id": essay_answer.pk, "score": 25}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.reviewed_by, "")

    def test_grade_essay_requires_all_essay_answers(self):
        quiz2 = CourseModule.objects.create(
            course=self.course, title="Kuis 2", module_category="quiz", point=50
        )
        choice = make_choice_question(quiz2, "C1")
        e1 = make_essay_question(quiz2, "E1")
        e2 = make_essay_question(quiz2, "E2")
        start = self.client.post(
            f"/module/{quiz2.id}/quiz/start/", {}, format="json"
        ).json()
        submission_id = start["submission"]["id"]
        option = choice.questionoption_set.order_by("sequence").first()
        for question, body in (
            (choice, {"question_option": option.pk}),
            (e1, {"answer_text": "jawab 1"}),
            (e2, {"answer_text": "jawab 2"}),
        ):
            self.client.post(
                "/user-answer/",
                {"submission": submission_id, "question": question.pk, **body},
                format="json",
            )
        submit = self.client.post(
            f"/module/{quiz2.id}/quiz/submit/",
            {"submission": submission_id},
            format="json",
        )
        self.assertEqual(submit.status_code, status.HTTP_200_OK)

        ans1 = UserAnswer.objects.get(submission_id=submission_id, question=e1)
        ans2 = UserAnswer.objects.get(submission_id=submission_id, question=e2)
        partial = self.grade(submission_id, [{"id": ans1.pk, "score": 10}])
        full = self.grade(
            submission_id,
            [{"id": ans1.pk, "score": 10}, {"id": ans2.pk, "score": 15}],
        )

        self.assertEqual(partial.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Semua jawaban essay", str(partial.json()))
        self.assertEqual(full.status_code, status.HTTP_200_OK)
        self.assertEqual(full.json()["score"], 42)
        submission = Submission.objects.get(pk=submission_id)
        self.assertEqual(submission.score, 42)


class BadgeTests(APITestCase):
    """Badge hybrid: otomatis course_complete + manual mentor (/user-badge/)."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.student = User.objects.create_user(
            username="student", password="secret123"
        )
        self.other = User.objects.create_user(username="other", password="secret123")
        self.course = Course.objects.create(user=self.owner, title="Badge Course")
        self.module = CourseModule.objects.create(course=self.course, title="M1")
        self.module_2 = CourseModule.objects.create(course=self.course, title="M2")
        CourseEnrollment.objects.create(course=self.course, user=self.student)
        self.auto_badge = Badge.objects.create(
            course=self.course,
            name="Graduate",
            description="Selesaikan semua module",
            rule_type=Badge.RuleType.COURSE_COMPLETE,
        )
        self.manual_badge = Badge.objects.create(
            course=self.course,
            name="Best Assignment",
            description="Tugas terbaik",
            rule_type=Badge.RuleType.MANUAL,
        )

    def finish(self, module, user=None):
        user = user or self.student
        UserProgress.objects.update_or_create(
            module=module,
            user=user,
            defaults={
                "status": UserProgress.ProgressStatus.FINISH,
                "complete_at": timezone.now(),
            },
        )

    # --- Otomatis (course_complete) ---

    def test_auto_badge_awarded_when_all_modules_finished(self):
        self.finish(self.module)
        self.client.force_authenticate(user=self.student)
        response = self.client.post(
            "/progress/", {"module": self.module_2.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            UserBadge.objects.filter(
                user=self.student, badge=self.auto_badge, awarded_by="system"
            ).exists()
        )
        earned = response.json()["earned_badges"]
        self.assertEqual([item["id"] for item in earned], [self.auto_badge.id])

    def test_auto_badge_not_awarded_before_complete(self):
        self.finish(self.module)

        self.assertFalse(UserBadge.objects.filter(badge=self.auto_badge).exists())

    def test_auto_badge_idempotent(self):
        self.finish(self.module)
        self.finish(self.module_2)
        from server.apps.remotech.services.badges import sync_badges

        first = sync_badges(self.student, self.course)
        second = sync_badges(self.student, self.course)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(
            UserBadge.objects.filter(user=self.student, badge=self.auto_badge).count(),
            1,
        )

    def test_auto_badge_revoked_when_progress_unmarked(self):
        self.finish(self.module)
        self.finish(self.module_2)
        self.client.force_authenticate(user=self.student)
        self.client.post("/progress/", {"module": self.module_2.id}, format="json")
        row = UserProgress.objects.get(module=self.module_2, user=self.student)

        self.client.delete(f"/progress/{row.id}/")

        self.assertFalse(UserBadge.objects.filter(badge=self.auto_badge).exists())

    def test_manual_badge_never_auto_awarded(self):
        self.finish(self.module)
        self.finish(self.module_2)
        from server.apps.remotech.services.badges import sync_badges

        sync_badges(self.student, self.course)

        self.assertFalse(UserBadge.objects.filter(badge=self.manual_badge).exists())

    def test_manual_badge_not_revoked_by_sync(self):
        UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by=self.owner.username
        )
        self.finish(self.module)
        self.finish(self.module_2)
        from server.apps.remotech.services.badges import sync_badges

        sync_badges(self.student, self.course)

        self.assertTrue(UserBadge.objects.filter(badge=self.manual_badge).exists())

    def test_auto_badge_not_awarded_without_enrollment_flow(self):
        # sync tetap jalan berdasarkan progress; cukup pastikan user lain
        # (tanpa progress) tidak menerima badge.
        self.finish(self.module)
        self.finish(self.module_2)

        self.assertFalse(
            UserBadge.objects.filter(user=self.other, badge=self.auto_badge).exists()
        )

    # --- Endpoint /user-badge/ (award manual mentor) ---

    def test_mentor_awards_manual_badge(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        row = UserBadge.objects.get(user=self.student, badge=self.manual_badge)
        self.assertEqual(row.awarded_by, "owner")
        self.assertEqual(response.json()["user_name"], "student")

    def test_award_rejects_auto_badge(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/user-badge/",
            {"badge": self.auto_badge.id, "user": self.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UserBadge.objects.filter(badge=self.auto_badge).exists())

    def test_award_rejects_non_owner_mentor(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_award_rejects_non_enrolled_student(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.other.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_award_rejects_duplicate(self):
        UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by="owner"
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.student.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            UserBadge.objects.filter(user=self.student, badge=self.manual_badge).count(),
            1,
        )

    def test_owner_can_revoke_student_badge(self):
        row = UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by="owner"
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f"/user-badge/{row.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserBadge.objects.filter(id=row.id).exists())

    def test_other_user_cannot_revoke(self):
        row = UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by="owner"
        )
        self.client.force_authenticate(user=self.other)

        response = self.client.delete(f"/user-badge/{row.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(UserBadge.objects.filter(id=row.id).exists())

    def test_update_methods_not_allowed(self):
        row = UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by="owner"
        )
        self.client.force_authenticate(user=self.owner)

        patch_response = self.client.patch(f"/user-badge/{row.id}/", {}, format="json")
        put_response = self.client.put(f"/user-badge/{row.id}/", {}, format="json")

        self.assertEqual(
            patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(put_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # --- GET /user-badge/me/ ---

    def test_me_lists_earned_and_locked_with_progress(self):
        self.finish(self.module)
        self.client.force_authenticate(user=self.student)
        # Module terakhir lewat API → sync_leaderboard + sync_badges berjalan.
        self.client.post("/progress/", {"module": self.module_2.id}, format="json")

        response = self.client.get("/user-badge/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = {row["badge"]["id"]: row for row in response.json()}
        self.assertTrue(rows[self.auto_badge.id]["earned"])
        self.assertFalse(rows[self.manual_badge.id]["earned"])
        locked = rows[self.manual_badge.id]
        self.assertEqual(locked["progress"]["completed"], 2)
        self.assertEqual(locked["progress"]["total"], 2)
        self.assertEqual(locked["course"], self.course.id)

    def test_me_scoped_to_enrolled_courses(self):
        stranger_course = Course.objects.create(user=self.owner, title="Other")
        Badge.objects.create(
            course=stranger_course, name="Other Badge", description="x"
        )
        self.client.force_authenticate(user=self.student)

        response = self.client.get("/user-badge/me/").json()

        self.assertEqual({row["course"] for row in response}, {self.course.id})

    def test_me_filter_by_course(self):
        self.client.force_authenticate(user=self.student)

        response = self.client.get(f"/user-badge/me/?course={self.course.id}").json()
        other = Course.objects.create(user=self.owner, title="Nope")
        filtered_out = self.client.get(f"/user-badge/me/?course={other.id}").json()

        self.assertEqual(len(response), 2)
        self.assertEqual(filtered_out, [])

    # --- CRUD /badge/ ---

    def test_badge_list_is_public(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/badge/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_badge_create_requires_owner(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            "/badge/",
            {"course": self.course.id, "name": "X", "description": "y"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_badge_owner_can_create_with_preset_icon(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/badge/",
            {
                "course": self.course.id,
                "name": "Fire Badge",
                "description": "Semangat",
                "icon_name": "fire",
                "rule_type": Badge.RuleType.MANUAL,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["icon_name"], "fire")
        self.assertIsNone(response.json()["icon_image"])
        self.assertEqual(response.json()["course_title"], "Badge Course")

    def test_badge_owner_can_delete(self):
        badge = Badge.objects.create(
            course=self.course, name="Temp", description="x"
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(f"/badge/{badge.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_badge_update_not_owner_forbidden(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            f"/badge/{self.manual_badge.id}/", {"name": "Hacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Reward ---

    def test_badge_create_with_reward(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            "/badge/",
            {
                "course": self.course.id,
                "name": "Reward Badge",
                "description": "x",
                "reward": "Sertifikat + akses premium",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["reward"], "Sertifikat + akses premium")

    def test_badge_reward_defaults_to_empty_and_updatable(self):
        self.assertEqual(self.manual_badge.reward, "")

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            f"/badge/{self.manual_badge.id}/",
            {"reward": "Hadiah baru"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["reward"], "Hadiah baru")

    # --- /user-badge/me/: earned_at + awarded_by ---

    def test_my_badges_include_earned_at_and_awarded_by(self):
        self.owner.first_name = "Mentor"
        self.owner.last_name = "Jago"
        self.owner.email = "mentor.jago@example.com"
        self.owner.save()
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.student.id},
            format="json",
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get("/user-badge/me/", {"course": self.course.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entries = {item["badge"]["id"]: item for item in response.json()}

        earned = entries[self.manual_badge.id]
        self.assertTrue(earned["earned"])
        self.assertIsNotNone(earned["earned_at"])
        # awarded_by menyimpan username; tampil "Nama Lengkap - email".
        self.assertEqual(earned["awarded_by"], "Mentor Jago - mentor.jago@example.com")

        locked = entries[self.auto_badge.id]
        self.assertFalse(locked["earned"])
        self.assertIsNone(locked["earned_at"])
        self.assertEqual(locked["awarded_by"], "")

    def test_my_badges_awarded_by_falls_back_without_full_name(self):
        # Tanpa nama lengkap → tampil email saja.
        self.owner.email = "owner@example.com"
        self.owner.save()
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            "/user-badge/",
            {"badge": self.manual_badge.id, "user": self.student.id},
            format="json",
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get("/user-badge/me/", {"course": self.course.id})

        earned = {
            item["badge"]["id"]: item for item in response.json()
        }[self.manual_badge.id]
        self.assertEqual(earned["awarded_by"], "owner@example.com")

    # --- Unique constraint ---

    def test_user_badge_unique_constraint(self):
        from django.db import IntegrityError, transaction

        UserBadge.objects.create(
            user=self.student, badge=self.manual_badge, awarded_by="owner"
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserBadge.objects.create(
                    user=self.student, badge=self.manual_badge, awarded_by="owner"
                )


class LateDeadlineTests(APITestCase):
    """Tenggat pengumpulan (CD6) + penalti keterlambatan lembut (CD8).

    Submit telat selalu diterima; `Submission.is_late` di-snapshot saat
    momen submit pertama; poin leaderboard memakai skor efektif
    (skor mentah tetap utuh untuk penilaian mentor).
    """

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="secret123")
        self.student = User.objects.create_user(
            username="student", password="secret123"
        )
        self.course = Course.objects.create(user=self.owner, title="Course D")
        CourseEnrollment.objects.create(course=self.course, user=self.student)
        self.client.force_authenticate(user=self.student)

    def make_upload_module(self, due_at=None, point=100, penalty=50):
        module = CourseModule.objects.create(
            course=self.course,
            title="Tugas",
            module_category="upload",
            point=point,
            due_at=due_at,
            late_penalty_percent=penalty,
        )
        assignment = Assignment.objects.create(
            course_module=module, name="Tugas 1", description="d"
        )
        return module, assignment

    def make_quiz_module(self, due_at=None, point=100, penalty=50):
        module = CourseModule.objects.create(
            course=self.course,
            title="Kuis",
            module_category="quiz",
            point=point,
            due_at=due_at,
            late_penalty_percent=penalty,
        )
        make_choice_question(module, "Q1", correct_index=0)
        return module

    def submit_upload(self, assignment, url="https://example.com/hasil.pdf"):
        return self.client.post(
            "/submission/",
            {"assignment": assignment.id, "submission_url": url},
            format="json",
        )

    def submit_quiz(self, module):
        start = self.client.post(f"/module/{module.id}/quiz/start/", {}, format="json")
        submission_id = start.json()["submission"]["id"]
        question = module.question_set.first()
        option = question.questionoption_set.order_by("sequence").first()
        self.client.post(
            "/user-answer/",
            {"submission": submission_id, "question": question.pk, "question_option": option.pk},
            format="json",
        )
        return self.client.post(
            f"/module/{module.id}/quiz/submit/",
            {"submission": submission_id},
            format="json",
        )

    # --- Unit: helper penalti ---

    def test_penalized_score_helper(self):
        self.assertEqual(penalized_score(100, False, 50), 100)
        self.assertEqual(penalized_score(100, True, 0), 100)
        self.assertEqual(penalized_score(100, True, 100), 0)
        self.assertEqual(penalized_score(80, True, 50), 40)
        self.assertEqual(penalized_score(80, False, 50), 80)

    # --- Upload: snapshot is_late + poin leaderboard ---

    def test_upload_on_time_is_not_late(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() + timedelta(hours=1)
        )

        data = self.submit_upload(assignment).json()

        self.assertFalse(data["is_late"])
        self.assertEqual(data["effective_score"], 0)
        self.assertEqual(data["late_penalty_percent"], 50)

    def test_upload_without_due_at_is_not_late(self):
        module, assignment = self.make_upload_module(due_at=None)

        data = self.submit_upload(assignment).json()

        self.assertFalse(data["is_late"])

    def test_upload_after_due_at_is_marked_late(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() - timedelta(minutes=5)
        )

        data = self.submit_upload(assignment).json()

        self.assertTrue(data["is_late"])

    def test_late_upload_leaderboard_uses_penalized_score(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() - timedelta(minutes=5), point=100, penalty=50
        )
        self.submit_upload(assignment)
        self.client.force_authenticate(user=self.owner)
        self.client.patch(
            f"/submission/{Submission.objects.get(assignment=assignment).id}/",
            {"score": 80},
            format="json",
        )

        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 40)  # 80 * (100-50) / 100
        detail = LeaderboardDetail.objects.get(leaderboard=leaderboard)
        self.assertEqual(detail.point, 40)

    def test_on_time_upload_leaderboard_full_points(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() + timedelta(hours=1), point=100, penalty=50
        )
        self.submit_upload(assignment)
        self.client.force_authenticate(user=self.owner)
        self.client.patch(
            f"/submission/{Submission.objects.get(assignment=assignment).id}/",
            {"score": 80},
            format="json",
        )

        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 80)

    def test_penalty_zero_late_still_full_points(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() - timedelta(minutes=5), point=100, penalty=0
        )
        self.submit_upload(assignment)
        self.client.force_authenticate(user=self.owner)
        self.client.patch(
            f"/submission/{Submission.objects.get(assignment=assignment).id}/",
            {"score": 80},
            format="json",
        )

        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 80)

    def test_penalty_hundred_late_gets_zero_points(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() - timedelta(minutes=5), point=100, penalty=100
        )
        self.submit_upload(assignment)
        self.client.force_authenticate(user=self.owner)
        self.client.patch(
            f"/submission/{Submission.objects.get(assignment=assignment).id}/",
            {"score": 80},
            format="json",
        )

        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 0)

    def test_is_late_snapshot_kept_on_url_resubmit(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() + timedelta(hours=1)
        )
        created = self.submit_upload(assignment).json()
        # Tenggat lewat, lalu student memperbarui tautan (belum dinilai).
        module.due_at = timezone.now() - timedelta(minutes=5)
        module.save(update_fields=["due_at"])

        response = self.submit_upload(assignment, url="https://example.com/v2.pdf")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()["is_late"])  # snapshot submit pertama

    def test_is_late_is_read_only_for_client(self):
        module, assignment = self.make_upload_module(due_at=None)

        data = self.submit_upload(assignment).json()

        # Kiriman `is_late` dari client diabaikan backend.
        self.assertFalse(data["is_late"])

    def test_effective_score_in_submission_response(self):
        module, assignment = self.make_upload_module(
            due_at=timezone.now() - timedelta(minutes=5), point=100, penalty=50
        )
        self.submit_upload(assignment)
        self.client.force_authenticate(user=self.owner)
        submission_id = Submission.objects.get(assignment=assignment).id
        self.client.patch(f"/submission/{submission_id}/", {"score": 80}, format="json")

        self.client.force_authenticate(user=self.student)
        data = self.client.get(f"/submission/{submission_id}/").json()

        self.assertEqual(data["score"], 80)
        self.assertEqual(data["effective_score"], 40)
        self.assertEqual(data["late_penalty_percent"], 50)
        self.assertTrue(data["is_late"])

    # --- Quiz: is_late + penalti ---

    def test_quiz_after_due_at_is_late_and_penalized(self):
        module = self.make_quiz_module(
            due_at=timezone.now() - timedelta(minutes=5), point=100, penalty=50
        )

        response = self.submit_quiz(module)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["submission"]["is_late"])
        # 1 dari 1 soal benar = 100 poin mentah, terpenalti 50% ? 50.
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 50)

    def test_quiz_on_time_full_points(self):
        module = self.make_quiz_module(
            due_at=timezone.now() + timedelta(hours=1), point=100, penalty=50
        )

        response = self.submit_quiz(module)

        self.assertFalse(response.json()["submission"]["is_late"])
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 100)

    def test_quiz_without_due_at_full_points(self):
        module = self.make_quiz_module(due_at=None, point=100, penalty=50)

        response = self.submit_quiz(module)

        self.assertFalse(response.json()["submission"]["is_late"])
        leaderboard = Leaderboard.objects.get(user=self.student, course=self.course)
        self.assertEqual(leaderboard.total_points, 100)
