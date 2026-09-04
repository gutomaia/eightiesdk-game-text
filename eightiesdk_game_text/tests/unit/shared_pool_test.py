"""Python binding for the shared-pool contract."""

from dataclasses import dataclass, replace
from unittest import TestCase

from eightiesdk_game_text.contribution import (
    TextContribution,
    contribute_text,
)
from eightiesdk_game_text.declarations import TextStore
from eightiesdk_game_text.tests.shared_pool_spec import SharedPoolSpec


@dataclass
class Question:
    ask: str
    alternatives: list[str]
    correct: int


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
    """An immutable state with both neutral ports, as every platform
    extension state has them."""

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


@dataclass(frozen=True)
class ClaimsOnlyState:
    profile: object
    cartridge: object
    configuration: object
    resource_claims: tuple = ()

    def with_resource_claims(self, claims):
        return replace(
            self, resource_claims=self.resource_claims + tuple(claims)
        )


class SharedPoolTest(SharedPoolSpec, TestCase):
    def given_two_stores_sharing_a_string(self):
        self.bank = TextStore(
            [
                Question('HOW TALL?', ['2744', '2500'], 1),
                Question('WHO?', ['2500', '2850'], 0),
            ]
        )
        self.script = TextStore([Line('2500', 0), Line('SAY WHO?', 1)])
        self.target = Target('nes', object(), object(), object())

    def given_a_build_state_with_both_ports(self):
        self.state = State(
            self.target.profile,
            self.target.cartridge,
            self.target.configuration,
        )

    def given_a_build_state_without_the_contribution_port(self):
        self.state = ClaimsOnlyState(
            self.target.profile,
            self.target.cartridge,
            self.target.configuration,
        )

    def _contribute(self, store, owner):
        return contribute_text(
            store,
            self.target,
            None,
            build_state=self.state,
            declaration_owner=owner,
        )

    def when_both_stores_are_contributed(self):
        self.state = self._contribute(self.bank, 'bank')
        self.state = self._contribute(self.script, 'script')
        self.refusal = None

    def when_the_first_store_is_contributed(self):
        try:
            self.state = self._contribute(self.bank, 'bank')
        except Exception as error:
            self.refusal = error
        else:
            self.refusal = None

    def _last(self):
        contributions = [
            item
            for item in self.state.extension_contributions
            if isinstance(item, TextContribution)
        ]
        self.assertTrue(contributions, 'no text contribution retained')
        return contributions[-1]

    def _encoded(self, text):
        cartridge = self._last().cartridge
        return bytes(cartridge.alphabet.index(c) for c in text)

    def assert_the_shared_string_is_in_the_pool_once(self):
        pool = self._last().cartridge.pool
        self.assertEqual(1, pool.count(self._encoded('2500') + b'\xff'))

    def assert_one_alphabet_covers_both_stores(self):
        alphabet = self._last().cartridge.alphabet
        self.assertEqual(sorted(' 024578?AHLOSTWY'), sorted(alphabet))

    def _claims(self):
        return [
            claim
            for claim in self.state.resource_claims
            if claim.resource == 'rom_payload_bytes'
        ]

    def assert_the_first_claim_spends(self, size):
        self.assertEqual(size, self._claims()[0].spent)

    def assert_the_second_claim_spends_only_its_new_bytes(self, size):
        self.assertEqual(size, self._claims()[1].spent)
        self.assertIn(
            '1 string already in the pool', self._claims()[1].evidence.source
        )

    def assert_the_claims_are_owned_by_each_store(self):
        self.assertEqual(
            ['text:bank', 'text:script'],
            [claim.owner for claim in self._claims()],
        )

    def assert_the_last_contribution_carries_both_stores(self):
        last = self._last()
        self.assertEqual(('bank', 'script'), last.owners)
        self.assertEqual((self.bank, self.script), last.stores)
        self.assertEqual(2, len(last.cartridge.stores))

    def assert_each_store_reads_its_own_records_from_the_shared_pool(self):
        bank, script = self._last().cartridge.stores
        self.assertEqual('WHO?', bank.read_text(1, 'ask'))
        self.assertEqual(['2500', '2850'], bank.read_texts(1, 'alternatives'))
        self.assertEqual('2500', script.read_text(0, 'say'))
        self.assertEqual('SAY WHO?', script.read_text(1, 'say'))
        self.assertIs(bank.pool, script.pool)

    def assert_missing_contribution_port_was_refused(self):
        self.assertIsInstance(self.refusal, ValueError)
        self.assertIn('with_extension_contribution', str(self.refusal))


__all__ = ['SharedPoolTest']
