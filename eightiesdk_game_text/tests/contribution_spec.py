"""Contract for composing a text store into extension-neutral build state.

A game declares a text store in ``declare()``: records whose fields hold
text. The extension encodes them once per cartridge and publishes what
that costs as owner-qualified resource claims through the build state's
claim port. It knows the text it stores and what the bytes cost; it
does not know where they are drawn, which plane, or which console.
"""


class TextContributionSpec:
    """Bindings invoke ``contribute_text`` with extension-neutral values.

    The build state supplies ``with_resource_claims``,
    ``with_extension_contribution`` and the three target facts. The
    contributor must not depend on any platform, runtime or product
    package.
    """

    def given_records_with_text_fields(self):
        raise NotImplementedError()

    def given_a_target(self, name):
        raise NotImplementedError()

    def given_build_state_with_a_claim_port(self):
        raise NotImplementedError()

    def given_build_state_without_a_claim_port(self):
        raise NotImplementedError()

    def given_target_profile_disagrees_with_build_state(self):
        raise NotImplementedError()

    def when_text_is_contributed(self, *, build_state=True, owner='bank'):
        raise NotImplementedError()

    def when_package_metadata_is_read(self):
        raise NotImplementedError()

    def assert_the_state_replacement_was_returned(self):
        raise NotImplementedError()

    def assert_one_rom_claim_names_the_owner(self):
        raise NotImplementedError()

    def assert_the_claim_spends_exactly_the_encoded_bytes(self):
        raise NotImplementedError()

    def assert_the_claim_evidence_is_measured_and_names_the_package(self):
        raise NotImplementedError()

    def assert_missing_build_state_was_refused(self):
        raise NotImplementedError()

    def assert_missing_claim_port_was_refused(self):
        raise NotImplementedError()

    def assert_missing_owner_was_refused(self):
        raise NotImplementedError()

    def assert_authority_mismatch_was_refused(self):
        raise NotImplementedError()

    def assert_text_announces_the_contribution_adapter(self):
        raise NotImplementedError()

    def test_a_text_store_costs_exactly_its_encoded_bytes(self):
        self.given_records_with_text_fields()
        self.given_a_target('nes')
        self.given_build_state_with_a_claim_port()

        self.when_text_is_contributed()

        self.assert_the_state_replacement_was_returned()
        self.assert_one_rom_claim_names_the_owner()
        self.assert_the_claim_spends_exactly_the_encoded_bytes()
        self.assert_the_claim_evidence_is_measured_and_names_the_package()

    def test_contribution_without_build_state_is_refused(self):
        self.given_records_with_text_fields()
        self.given_a_target('nes')

        self.when_text_is_contributed(build_state=False)

        self.assert_missing_build_state_was_refused()

    def test_contribution_without_a_claim_port_is_refused(self):
        self.given_records_with_text_fields()
        self.given_a_target('nes')
        self.given_build_state_without_a_claim_port()

        self.when_text_is_contributed()

        self.assert_missing_claim_port_was_refused()

    def test_contribution_without_an_owner_is_refused(self):
        self.given_records_with_text_fields()
        self.given_a_target('nes')
        self.given_build_state_with_a_claim_port()

        self.when_text_is_contributed(owner=None)

        self.assert_missing_owner_was_refused()

    def test_target_and_build_state_must_agree(self):
        self.given_records_with_text_fields()
        self.given_a_target('nes')
        self.given_build_state_with_a_claim_port()
        self.given_target_profile_disagrees_with_build_state()

        self.when_text_is_contributed()

        self.assert_authority_mismatch_was_refused()

    def test_the_package_announces_the_text_resolver(self):
        self.when_package_metadata_is_read()

        self.assert_text_announces_the_contribution_adapter()


__all__ = ['TextContributionSpec']
