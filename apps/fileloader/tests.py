import datetime
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
import gpxpy.gpx
from lib.GPX_analysis_step_complete import calculate_cooper_test


def create_synthetic_gpx(num_seconds=1000, step_meters=3.0, with_elevation=True):
    """Creates synthetic GPX XML string with 1 point per second."""
    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    start_time = datetime.datetime(2025, 1, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)
    base_lat = 52.2297
    base_lon = 21.0122

    # approx 111,000 meters per degree latitude
    deg_per_meter = 1.0 / 111000.0

    for i in range(num_seconds):
        lat = base_lat + (i * step_meters * deg_per_meter)
        lon = base_lon
        elev = 100.0 + (i * 0.05) if with_elevation else None
        point = gpxpy.gpx.GPXTrackPoint(
            latitude=lat,
            longitude=lon,
            elevation=elev,
            time=start_time + datetime.timedelta(seconds=i)
        )
        segment.points.append(point)

    return gpx.to_xml()


class GPXAnalysisLogicTests(TestCase):
    def test_short_gpx_rejected(self):
        # 600 seconds = 10 minutes (< 12 minutes)
        xml = create_synthetic_gpx(num_seconds=600)
        result, error = calculate_cooper_test(xml)
        self.assertIsNone(result)
        self.assertIn("shorter than the required 12 minutes", error)

    def test_valid_gpx_calculated(self):
        # 1000 seconds with 3.0 m/s speed (~2160 meters in 12 min)
        xml = create_synthetic_gpx(num_seconds=1000, step_meters=3.0, with_elevation=True)
        result, error = calculate_cooper_test(xml)
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertIn('chart', result)
        self.assertIn('max_value', result)
        self.assertIn('vo2max', result)
        # Expected distance in 720 seconds at ~3m/s is approx 2160m
        self.assertAlmostEqual(result['max_value'], 2160, delta=20)
        self.assertGreater(result['vo2max'], 30)

    def test_gpx_without_elevation(self):
        # Elevation is None
        xml = create_synthetic_gpx(num_seconds=800, step_meters=3.0, with_elevation=False)
        result, error = calculate_cooper_test(xml)
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertIn('chart', result)

    def test_corrupt_gpx_returns_error(self):
        corrupt = "This is not XML or GPX data"
        result, error = calculate_cooper_test(corrupt)
        self.assertIsNone(result)
        self.assertIn("Could not parse GPX file", error)


class FileloaderViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_fileloader_view(self):
        response = self.client.get(reverse('fileloader'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload your GPX file")

    def test_post_no_file(self):
        response = self.client.post(reverse('fileloader'), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No file selected")

    def test_post_invalid_extension(self):
        fake_file = SimpleUploadedFile("track.txt", b"dummy text", content_type="text/plain")
        response = self.client.post(reverse('fileloader'), {'gpxfile': fake_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only .gpx files are supported")

    def test_post_valid_gpx_redirects_and_renders_chart(self):
        xml = create_synthetic_gpx(num_seconds=800, step_meters=3.0)
        gpx_file = SimpleUploadedFile("run.gpx", xml.encode('utf-8'), content_type="application/gpx+xml")

        response = self.client.post(reverse('fileloader'), {'gpxfile': gpx_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generated Cooper Test Analysis")
        self.assertContains(response, "Fastest 12m:")
        self.assertContains(response, "Estimated VO2max:")
