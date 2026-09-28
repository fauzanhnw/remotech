import io
import os
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, APITestCase

from server.apps.remotech.models import Course, CourseModule, ModuleContent
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
