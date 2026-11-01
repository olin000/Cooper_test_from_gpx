from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from apps.fileloader.tests import create_synthetic_gpx


class GPXReaderViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_chart_without_session_renders_fileloader(self):
        response = self.client.get(reverse('gpxreader'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload your GPX file")

    def test_post_chart_view_direct_upload(self):
        xml = create_synthetic_gpx(num_seconds=800, step_meters=3.0)
        gpx_file = SimpleUploadedFile("direct_run.gpx", xml.encode('utf-8'), content_type="application/gpx+xml")

        response = self.client.post(reverse('gpxreader'), {'gpxfile': gpx_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generated Cooper Test Analysis")
        self.assertContains(response, "Estimated VO2max:")
