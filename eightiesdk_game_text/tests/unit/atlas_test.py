from unittest import TestCase

from eightiesdk_game_text.atlas import Atlas, OutOfSlots
from eightiesdk_game_text.font import Font
from eightiesdk_game_text.tests.atlas_spec import AtlasSpec
from eightiesdk_game_text.tests.font_spec import FontSpec


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
        # Eight slots, one reserved: a 2x2 glyph takes four, so the
        # second cannot fit. EVERY CELL MUST BE DISTINCT — cells
        # are shared now, so four copies of one drawing would cost
        # four slots between them and never run out. Earlier this
        # binding used the same drawing four times and stopped
        # proving anything the moment sharing landed.
        from eightiesdk_game_text.font import Glyph

        crowd = Font(
            {
                chr(0x41 + n): Glyph(
                    [(n * 4 + k + 1,) * 8 for k in range(4)],
                    columns=2,
                )
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

    def when_claiming_a_glyph_whose_cells_are_all_present(self):
        from eightiesdk_game_text.font import Glyph

        # capacity 8, one reserved: 'A' takes all seven remaining
        # slots, so nothing NEW can fit. 'B' is drawn from the very
        # same cells in a different order.
        cells = [(n + 1,) * 8 for n in range(7)]
        font = Font(
            {
                'A': Glyph(cells, columns=7),
                'B': Glyph(list(reversed(cells)), columns=7),
            }
        )
        self.atlas = Atlas(font, capacity=self.CAPACITY, reserved=1)
        self.atlas.claim('A')
        self.refused = None
        try:
            self.slots = self.atlas.claim('B')
        except OutOfSlots as error:
            self.refused = error

    def assert_it_was_not_refused(self):
        self.assertIsNone(self.refused, str(self.refused))
        self.assertEqual(7, len(self.atlas.upload))

    def when_claiming_two_glyphs_sharing_a_cell(self):
        from eightiesdk_game_text.font import Glyph

        # two 1x2 glyphs whose BOTTOM cell is identical and whose
        # top cell is not — the shape a stem-sharing script makes
        stem = (0x18,) * 8
        font = Font(
            {
                'P': Glyph([(0x7C,) * 8, stem], columns=1),
                'Q': Glyph([(0x3E,) * 8, stem], columns=1),
            }
        )
        self.atlas = Atlas(font, capacity=self.CAPACITY, reserved=1)
        self.first = self.atlas.claim('P')
        self.second = self.atlas.claim('Q')
        self.shared = stem

    def assert_shared_slot_appears_in_both(self):
        common = set(self.first) & set(self.second)
        self.assertEqual(1, len(common), (self.first, self.second))
        slot = common.pop()
        self.assertEqual(self.shared, self.atlas.upload[slot])

    def assert_shared_cell_uploaded_once(self):
        stored = list(self.atlas.upload.values())
        self.assertEqual(1, stored.count(self.shared))
        self.assertEqual(3, len(self.atlas.upload))

    def assert_refusal_mentions_capacity(self):
        self.assertIn(str(self.CAPACITY), str(self.refusal))
