"""Python binding for the text contribution contract."""

import tomllib
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from unittest import TestCase

from eightiesdk_resources.resource_plan import MEASURED

import eightiesdk_game_text
from eightiesdk_game_text.tests.contribution_spec import (
    TextContributionSpec,
)

PACKAGE_ROOT = Path(eightiesdk_game_text.__file__).parent
GROUP = 'eightiesdk.game_extensions'
ADAPTER = 'eightiesdk_game_text.contribution:contribute_text'


@dataclass
class Line:
    say: str
    choices: list[str]
    mood: int


@dataclass(frozen=True)
class Target:
    name: str
    profile: object
    cartridge: object
    configuration: object


class Replacement:
    def __init__(self, claims, contributions=()):
        self.resource_claims = tuple(claims)
        self.extension_contributions = tuple(contributions)

    def with_extension_contribution(self, contribution):
        return Replacement(
            self.resource_claims,
            self.extension_contributions + (contribution,),
        )


class ClaimingBuildState:
    def __init__(self, target):
        self.profile = target.profile
        self.cartridge = target.cartridge
        self.configuration = target.configuration
        self.resource_claims = ()
        self.extension_contributions = ()
        self.received = []

    def with_resource_claims(self, claims):
        self.received.append(tuple(claims))
        return Replacement(self.resource_claims + tuple(claims))

    def with_extension_contribution(self, contribution):
        return Replacement(self.resource_claims, (contribution,))


class PortlessBuildState:
    def __init__(self, target):
        self.profile = target.profile
        self.cartridge = target.cartridge
        self.configuration = target.configuration


class TextContributionTest(TextContributionSpec, TestCase):
    def given_records_with_text_fields(self):
        # HAND-COUNTED, so the expectation does not come from the
        # encoder under test. Two records of (say, choices, mood):
        #   records  2 x (2 + 1 + 2 + 1)            = 12
        #   pool     'hi'+end 'a'+end 'b'+end 'yo'+end = 10
        #   tables   one ['a', 'b'] offset table, shared  = 4
        # Three different parts, so a double count cannot pass as a
        # sum by accident.
        self.records = [
            Line('hi', ['a', 'b'], 1),
            Line('yo', ['a', 'b'], 2),
        ]
        self.expected_bytes = 12 + 10 + 4

    def given_a_target(self, name):
        self.target = Target(name, object(), object(), object())

    def given_build_state_with_a_claim_port(self):
        self.build_state = ClaimingBuildState(self.target)

    def given_build_state_without_a_claim_port(self):
        self.build_state = PortlessBuildState(self.target)

    def given_target_profile_disagrees_with_build_state(self):
        self.target = Target(
            self.target.name,
            object(),
            self.target.cartridge,
            self.target.configuration,
        )

    def when_text_is_contributed(self, *, build_state=True, owner='bank'):
        from eightiesdk_game_text.contribution import contribute_text
        from eightiesdk_game_text.declarations import TextStore

        self.owner = owner
        arguments = {}
        if build_state:
            arguments['build_state'] = self.build_state
        if owner is not None:
            arguments['declaration_owner'] = owner
        try:
            self.result = contribute_text(
                TextStore(self.records), self.target, None, **arguments
            )
        except Exception as error:
            self.refusal = error
            self.result = None
        else:
            self.refusal = None

    def when_package_metadata_is_read(self):
        manifest = tomllib.loads(
            (PACKAGE_ROOT.parent / 'pyproject.toml').read_text(
                encoding='utf-8'
            )
        )
        self.declared = manifest['tool']['poetry']['plugins'][GROUP]
        self.installed = {
            entry.name: entry.value
            for entry in entry_points(group=GROUP)
            if entry.dist.name == 'eightiesdk-game-text'
        }

    def _resolved(self):
        self.assertIsNone(self.refusal, str(self.refusal))
        return self.result

    def _claim(self):
        result = self._resolved()
        self.assertEqual(1, len(result.resource_claims))
        return result.resource_claims[0]

    def assert_the_state_replacement_was_returned(self):
        result = self._resolved()
        self.assertIsInstance(result, Replacement)
        self.assertEqual(1, len(self.build_state.received))

    def assert_one_rom_claim_names_the_owner(self):
        claim = self._claim()
        self.assertEqual(f'text:{self.owner}', claim.owner)
        self.assertEqual('cartridge', claim.lifecycle)
        self.assertEqual('cartridge/rom_payload_bytes', claim.resource)

    def assert_the_claim_spends_exactly_the_encoded_bytes(self):
        self.assertEqual(self.expected_bytes, self._claim().spent)

    def assert_the_claim_evidence_is_measured_and_names_the_package(self):
        evidence = self._claim().evidence
        self.assertIs(MEASURED, evidence.status)
        self.assertIn('eightiesdk-game-text', evidence.source)
        self.assertIn('2 records', evidence.source)

    def _assert_refused(self, *fragments):
        self.assertIsNone(self.result)
        self.assertIsInstance(self.refusal, ValueError)
        for fragment in fragments:
            self.assertIn(fragment, str(self.refusal))

    def assert_missing_build_state_was_refused(self):
        self._assert_refused('build_state')

    def assert_missing_claim_port_was_refused(self):
        self._assert_refused('with_resource_claims')

    def assert_missing_owner_was_refused(self):
        self._assert_refused('declaration_owner')

    def assert_authority_mismatch_was_refused(self):
        self._assert_refused('disagree', 'profile')

    def assert_text_announces_the_contribution_adapter(self):
        self.assertEqual({'text': ADAPTER}, self.declared)
        self.assertEqual({'text': ADAPTER}, self.installed)


__all__ = ['TextContributionTest']
