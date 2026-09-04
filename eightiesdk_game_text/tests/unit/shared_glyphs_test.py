"""Python binding for the shared-glyphs contract."""

from dataclasses import dataclass, replace
from unittest import TestCase

from eightiesdk_game_text.contribution import (
    TextContribution,
    contribute_text,
)
from eightiesdk_game_text.declarations import TextStore, Typeface
from eightiesdk_game_text.tests.shared_glyphs_spec import SharedGlyphsSpec
from eightiesdk_game_text.tests.unit.glyph_store_test import ART


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


class SharedGlyphsTest(SharedGlyphsSpec, TestCase):
    def setUp(self):
        self.target = Target('nes', object(), object(), object())
        self.state = State(
            self.target.profile,
            self.target.cartridge,
            self.target.configuration,
        )

    def given_a_typeface_drawn_as_art(self, drawings):
        self.drawings = {character: ART[character] for character in drawings}
        self.typeface = Typeface.from_art(self.drawings)

    def given_a_second_typeface_with_the_same_drawings(self):
        self.other = Typeface.from_art(self.drawings)

    def given_two_stores_saying(self, first, second):
        self.first = TextStore(
            [Line(text, n) for n, text in enumerate(first)],
            typeface=self.typeface,
        )
        self.second = TextStore(
            [Line(text, n) for n, text in enumerate(second)],
            typeface=self.typeface,
        )

    def given_the_second_store_names_the_other_typeface(self):
        self.second = TextStore(self.second.records, typeface=self.other)

    def _contribute(self, store, owner):
        return contribute_text(
            store,
            self.target,
            None,
            build_state=self.state,
            declaration_owner=owner,
        )

    def when_both_stores_are_contributed(self):
        self.state = self._contribute(self.first, 'first')
        self.state = self._contribute(self.second, 'second')

    def _glyphs(self):
        last = [
            item
            for item in self.state.extension_contributions
            if isinstance(item, TextContribution)
        ][-1]
        return last.glyphs

    def assert_the_stores_share_one_glyph_store_holding(self, characters):
        first, second = self._glyphs()
        self.assertIs(first, second)
        self.assertEqual(sorted(characters), sorted(first.characters))

    def _glyph_claims(self):
        return [
            claim
            for claim in self.state.resource_claims
            if claim.resource == 'rom_payload_bytes'
            and 'glyph' in claim.evidence.source
        ]

    def assert_the_second_glyph_claim_spends(self, size):
        claims = self._glyph_claims()
        self.assertEqual(
            ['text:first', 'text:second'], [c.owner for c in claims]
        )
        self.assertEqual(size, claims[1].spent)

    def assert_the_stores_keep_separate_glyph_stores(self):
        first, second = self._glyphs()
        self.assertIsNot(first, second)
        self.assertEqual(['A', 'B'], sorted(first.characters))
        self.assertEqual(['B', 'Z'], sorted(second.characters))


__all__ = ['SharedGlyphsTest']
