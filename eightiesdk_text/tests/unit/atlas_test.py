from unittest import TestCase

from eightiesdk_text.atlas import Atlas, OutOfSlots
from eightiesdk_text.font import Font
from eightiesdk_text.tests.atlas_spec import AtlasSpec
from eightiesdk_text.tests.font_spec import FontSpec


class AtlasTest(AtlasSpec, TestCase):
    def given_atlas(self):
        self.font = Font.from_art(
            {
                'F': '\n'.join(FontSpec.NARROW),
                'W': '\n'.join(FontSpec.WIDE),
            }
        )
        self.atlas = Atlas(self.font, capacity=self.CAPACITY, reserved=1)
        self.previous = None

    def when_claiming(self, character):
        self.previous = getattr(self, 'slots', None)
        self.slots = self.atlas.claim(character)

    def when_claiming_until_full(self):
        # eight slots, one reserved: 'W' takes four, so a second
        # 'W'-sized glyph cannot fit. Distinct drawings, because
        # a repeat would reuse rather than allocate.
        crowd = Font.from_art(
            {
                chr(0x41 + n): '\n'.join(FontSpec.WIDE)
                for n in range(4)
            }
        )
        atlas = Atlas(crowd, capacity=self.CAPACITY, reserved=1)
        with self.assertRaises(OutOfSlots) as caught:
            for character in sorted(crowd.characters):
                atlas.claim(character)
        self.refusal = caught.exception

    def assert_slot_count(self, count):
        self.assertEqual(count, len(self.slots))

    def assert_slots_are_the_same_as_last_time(self):
        self.assertEqual(self.previous, self.slots)

    def assert_reserved_slot_untouched(self, slot):
        self.assertNotIn(slot, self.atlas.upload)

    def assert_upload_holds(self, character):
        glyph = self.font.glyph(character)
        self.assertEqual(
            list(glyph.cells),
            [self.atlas.upload[slot] for slot in self.slots],
        )

    def assert_upload_slot_count(self, count):
        self.assertEqual(count, len(self.atlas.upload))

    def assert_refusal_mentions_capacity(self):
        self.assertIn(str(self.CAPACITY), str(self.refusal))
