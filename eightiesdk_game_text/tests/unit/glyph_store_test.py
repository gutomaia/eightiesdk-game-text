"""Python binding for the glyph store contract."""

from dataclasses import dataclass, replace
from pathlib import Path
from unittest import TestCase

from eightiesdk_game_text.contribution import (
    TextContribution,
    contribute_text,
)
from eightiesdk_game_text.declarations import TextStore, Typeface
from eightiesdk_game_text.tests.glyph_store_spec import GlyphStoreSpec

try:
    import PIL  # noqa: F401

    PILLOW = True
except ImportError:
    PILLOW = False

#: a face that draws Latin and boxes for Hangul; the refusal example
#: is only meaningful on a machine that has it
LATIN_ONLY = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


#: distinct one-cell drawings, and one pair drawn alike on purpose
def _rows(*rows):
    return '\n'.join(rows)


BAR = _rows(
    '..XX....',
    '..XX....',
    '..XX....',
    '..XX....',
    '..XX....',
    '..XX....',
    '..XX....',
    '........',
)
ART = {
    'A': _rows(
        '.XXXX...',
        'XX..XX..',
        'XX..XX..',
        'XXXXXX..',
        'XX..XX..',
        'XX..XX..',
        'XX..XX..',
        '........',
    ),
    'B': _rows(
        'XXXXX...',
        'XX..XX..',
        'XX..XX..',
        'XXXXX...',
        'XX..XX..',
        'XX..XX..',
        'XXXXX...',
        '........',
    ),
    'Z': _rows(
        'XXXXXX..',
        '....XX..',
        '...XX...',
        '..XX....',
        '.XX.....',
        'XX......',
        'XXXXXX..',
        '........',
    ),
    'I': BAR,
    'l': BAR,
}


@dataclass
class Line:
    say: str
    mood: int


@dataclass(frozen=True)
class Target:
    name: str
    profile: object
    cartridge: object
    configuration: object


@dataclass(frozen=True)
class State:
    profile: object
    cartridge: object
    configuration: object
    resource_claims: tuple = ()
    extension_contributions: tuple = ()

    def with_resource_claims(self, claims):
        return replace(
            self, resource_claims=self.resource_claims + tuple(claims)
        )

    def with_extension_contribution(self, contribution):
        return replace(
            self,
            extension_contributions=self.extension_contributions
            + (contribution,),
        )


class GlyphStoreTest(GlyphStoreSpec, TestCase):
    def setUp(self):
        self.target = Target('nes', object(), object(), object())
        self.state = State(
            self.target.profile,
            self.target.cartridge,
            self.target.configuration,
        )

    def given_a_typeface_drawn_as_art(self, drawings):
        self.typeface = Typeface.from_art(
            {character: ART[character] for character in drawings}
        )

    def given_a_typeface_file_that_cannot_draw_hangul(self):
        if not PILLOW:
            self.skipTest('Pillow not installed')
        if not LATIN_ONLY.exists():
            self.skipTest('no Latin-only face on this machine')
        self.typeface = Typeface(LATIN_ONLY, height=16)

    def given_a_typeface_file_that_does_not_exist(self):
        if not PILLOW:
            self.skipTest('Pillow not installed')
        self.typeface = Typeface(Path('/nowhere/no-such-face.ttf'), height=16)

    def given_records_saying(self, *texts):
        self.store = TextStore(
            [Line(text, n) for n, text in enumerate(texts)],
            typeface=self.typeface,
        )

    def _contribute(self):
        return contribute_text(
            self.store,
            self.target,
            None,
            build_state=self.state,
            declaration_owner='bank',
        )

    def when_the_store_is_contributed(self):
        self.state = self._contribute()

    def when_contribution_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            self._contribute()
        self.refusal = caught.exception

    def _contribution(self):
        return [
            item
            for item in self.state.extension_contributions
            if isinstance(item, TextContribution)
        ][-1]

    def _glyphs(self):
        return self._contribution().glyphs[-1]

    def assert_glyphs_exist_exactly_for(self, characters):
        self.assertEqual(sorted(characters), sorted(self._glyphs().characters))

    def assert_distinct_cells_stored(self, count):
        store = getattr(self, 'glyph_store', None) or self._glyphs()
        self.assertEqual(count, len(store.cells))

    def assert_the_glyph_claim_spends(self, size):
        # ONE claim for the owner; the glyph part is the number the
        # contribution records, and the claim is text plus glyphs
        claims = [
            claim
            for claim in self.state.resource_claims
            if claim.owner == 'text:bank'
        ]
        self.assertEqual(1, len(claims))
        text_bytes, glyph_bytes = self._contribution().costs[-1]
        self.assertEqual(size, glyph_bytes)
        self.assertEqual(text_bytes + glyph_bytes, claims[0].spent)
        self.assertIn(f'{size} bytes added', claims[0].evidence.source)

    def assert_the_refusal_names(self, *fragments):
        for fragment in fragments:
            self.assertIn(fragment, str(self.refusal))

    def given_one_reserved_slot(self):
        self.reserved = 1

    def when_the_glyphs_are_stored(self):
        from eightiesdk_game_text.glyphs import GlyphStore

        used = ''.join(self.store.texts)
        self.glyph_store = GlyphStore(
            self.typeface.glyphs_for(used), used, reserved=self.reserved
        )

    def assert_no_glyph_uses_slot(self, slot):
        for character in self.glyph_store.characters:
            self.assertNotIn(slot, self.glyph_store.slots_of(character))
        self.assertNotIn(slot, self.glyph_store.cells)


__all__ = ['GlyphStoreTest']
