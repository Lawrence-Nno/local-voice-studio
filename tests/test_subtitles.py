import unittest
from app.subtitles import timestamp, make_cues, parse_srt, serialize


class SubtitleTests(unittest.TestCase):
    def test_rounding_across_time_boundaries(self):
        self.assertEqual(timestamp(59.9996), "00:01:00,000")
        self.assertEqual(timestamp(3600.001), "01:00:00,001")

    def test_readable_cues_and_round_trip(self):
        words = [{"word": word, "start": i * .4, "end": i * .4 + .3}
                 for i, word in enumerate("Hello. These subtitles keep the actual spoken words and their timing.".split())]
        cues = make_cues(words)
        self.assertEqual(cues[0]["text"], "Hello.")
        text = serialize(cues)
        self.assertEqual(serialize(parse_srt(text)), text)
        self.assertEqual(" ".join(c["text"].replace("\n", " ") for c in cues),
                         "Hello. These subtitles keep the actual spoken words and their timing.")

    def test_invalid_edits_are_rejected(self):
        for text in ("1\n00:00:02,000 --> 00:00:01,000\nBackward", "2\n00:00:00,000 --> 00:00:01,000\nWrong number",
                     "1\n00:60:00,000 --> 01:00:01,000\nInvalid minutes",
                     "1\n00:00:00,000 --> 00:00:02,000\nA\n\n2\n00:00:01,000 --> 00:00:03,000\nOverlap"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_srt(text)

    def test_gap_and_length_split_without_losing_words(self):
        words = [{"word": "word", "start": i * .2, "end": i * .2 + .1} for i in range(40)]
        cues = make_cues(words)
        self.assertGreater(len(cues), 1)
        self.assertTrue(all(len(c["text"].splitlines()) <= 2 for c in cues))
        self.assertEqual(sum(len(c["text"].split()) for c in cues), 40)


if __name__ == "__main__":
    unittest.main()
