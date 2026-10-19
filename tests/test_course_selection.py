import unittest
from test_login_downloads import cms


class CourseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.courses = [{'id': str(2000+i), 'code': f'COURSE{i}'} for i in range(1, 11)]

    def numbers(self, text):
        return [self.courses.index(course)+1 for course in cms.parse_course_selection(text, self.courses)]

    def test_inclusive_range(self):
        self.assertEqual(self.numbers('1-6'), [1, 2, 3, 4, 5, 6])

    def test_mixed_ranges(self):
        self.assertEqual(self.numbers('1-3, 5, 7-9'), [1, 2, 3, 5, 7, 8, 9])

    def test_spaces_duplicates_and_order(self):
        self.assertEqual(self.numbers('5, 1 - 3 2-4 5'), [5, 1, 2, 3, 4])

    def test_existing_formats(self):
        self.assertEqual(self.numbers('1, 2004 course6'), [1, 4, 6])
        self.assertEqual(self.numbers('all'), list(range(1, 11)))
        self.assertEqual(self.numbers(''), [])

    def test_invalid_ranges_rejected(self):
        for text in ('0-3', '3-1', '1-11', '1--3', '-1', '1, nonsense'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.numbers(text)
