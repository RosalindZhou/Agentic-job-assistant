import unittest

from nodes.job_output import extract_jobs


class ExtractJobsTest(unittest.TestCase):
    def test_extracts_fenced_json_with_nested_fields(self):
        response = 'Result:\n' + '~~~json\n{"job_list": [{"title": "ML Intern", "company": "Example", "details": {"team": "ML"}}]}\n~~~'
        self.assertEqual(extract_jobs(response)[0]["title"], "ML Intern")

    def test_ignores_malformed_and_incomplete_jobs(self):
        self.assertEqual(extract_jobs('{"job_list": ['), [])
        self.assertEqual(extract_jobs('{"job_list": [1, {"title": "Intern"}]}'), [])

    def test_skips_unrelated_json(self):
        self.assertEqual(
            extract_jobs('{"notes": {}} {"job_list": [{"title": "Intern", "company": "Example"}]}'),
            [{"title": "Intern", "company": "Example"}],
        )
