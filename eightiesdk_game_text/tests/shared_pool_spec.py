"""Every text store a game declares shares one pool.

A cartridge carries ONE alphabet and ONE pool however many stores
declare into it: a question bank and a dialogue script that both say
'2500' store it once, and a character common to both costs one byte
in both. The extension learns what earlier stores put in the pool by
reading the build state's retained extension contributions, which
is the neutral port every platform state already offers, and it
leaves a contribution carrying the whole cartridge so far for the
next store and for whoever renders.

Each store's claim spends ONLY THE BYTES IT ADDS, so the claims of
all stores add up to the cartridge's text exactly once.

Records used by the examples: the record spec's two questions, then
two dialogue lines of which one repeats a question's alternative.
"""


class SharedPoolSpec:
    def given_two_stores_sharing_a_string(self):
        raise NotImplementedError()

    def given_a_build_state_with_both_ports(self):
        raise NotImplementedError()

    def given_a_build_state_without_the_contribution_port(self):
        raise NotImplementedError()

    def when_both_stores_are_contributed(self):
        raise NotImplementedError()

    def when_the_first_store_is_contributed(self):
        raise NotImplementedError()

    def assert_the_shared_string_is_in_the_pool_once(self):
        raise NotImplementedError()

    def assert_one_alphabet_covers_both_stores(self):
        raise NotImplementedError()

    def assert_the_first_claim_spends(self, size):
        raise NotImplementedError()

    def assert_the_second_claim_spends_only_its_new_bytes(self, size):
        raise NotImplementedError()

    def assert_the_claims_are_owned_by_each_store(self):
        raise NotImplementedError()

    def assert_the_last_contribution_carries_both_stores(self):
        raise NotImplementedError()

    def assert_each_store_reads_its_own_records_from_the_shared_pool(self):
        raise NotImplementedError()

    def assert_missing_contribution_port_was_refused(self):
        raise NotImplementedError()

    def test_two_stores_share_one_pool(self):
        self.given_two_stores_sharing_a_string()
        self.given_a_build_state_with_both_ports()

        self.when_both_stores_are_contributed()

        self.assert_the_shared_string_is_in_the_pool_once()
        self.assert_one_alphabet_covers_both_stores()

    def test_each_store_claims_only_what_it_adds(self):
        """HAND-COUNTED. The bank alone: 12 record bytes, 30 pool
        bytes, 8 table bytes = 50. The script adds two 3-byte
        records and ONE new string, 'SAY WHO?' with its terminator,
        9 bytes; '2500' is already there. So it claims 6 + 9 = 15,
        where encoded alone it would have cost 20."""
        self.given_two_stores_sharing_a_string()
        self.given_a_build_state_with_both_ports()

        self.when_both_stores_are_contributed()

        self.assert_the_first_claim_spends(50)
        self.assert_the_second_claim_spends_only_its_new_bytes(15)
        self.assert_the_claims_are_owned_by_each_store()

    def test_the_contribution_carries_the_whole_cartridge(self):
        self.given_two_stores_sharing_a_string()
        self.given_a_build_state_with_both_ports()

        self.when_both_stores_are_contributed()

        self.assert_the_last_contribution_carries_both_stores()
        self.assert_each_store_reads_its_own_records_from_the_shared_pool()

    def test_a_state_that_cannot_retain_a_contribution_is_refused(self):
        self.given_two_stores_sharing_a_string()
        self.given_a_build_state_without_the_contribution_port()

        self.when_the_first_store_is_contributed()

        self.assert_missing_contribution_port_was_refused()


__all__ = ['SharedPoolSpec']
