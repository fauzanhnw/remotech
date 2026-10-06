import hashlib
import io
import os
import tempfile
from decimal import Decimal
from unittest.mock import patch

import requests
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase

from server.apps.remotech.models import (
    Assignment,
    Course,
    CourseEnrollment,
    CourseModule,
    CourseOrder,
    Leaderboard,
    ModuleContent,
    SetPasswordToken,
    Submission,
)
from server.apps.remotech.services.auth import (
    MENTOR_GROUP,
    PARTICIPANT_GROUP,
    register_user,
)
from server.apps.remotech.services.richtext import (
    extract_media_urls,
    sanitize_richtext,
)
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
        self.assertEqual(by_course["results"][0]["course"], self.course_a.id)

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
        self.module = CourseModule.objects.create(course=self.course, title="M1")
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
