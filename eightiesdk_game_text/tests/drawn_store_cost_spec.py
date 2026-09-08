"""What a store costs on a console that draws it.

ONE STORE, ONE BANK'S WORTH. A store drawn at run time carries its
own text, its own record table and its own cells, the way one
language sits in one bank of the owner's cartridges; a second store
over the same face does not carry the first store's strings again,
and neither carries the whole cartridge's pool. And the store's
claim is the bytes its runtime actually places, not the delta of a
shared encoding nothing places: the ledger reads what the linker
will lay down.
"""


class DrawnStoreCostSpec:
    def given_two_stores_on_a_drawing_console(self):
        """Two stores over one face, contributed in order as the
        runtime would, on a console with a text runtime."""
        raise NotImplementedError()

    def when_both_are_contributed(self):
        raise NotImplementedError()

    def assert_claim_of_equals_its_runtime_bytes(self, owner):
        """The owner's ROM claim spends exactly the bytes of the ROM
        sections its runtime contribution carries."""
        raise NotImplementedError()

    def assert_runtime_pool_of_holds_its_own_text_only(self, owner):
        """The owner's pool section is the size of that store
        encoded alone."""
        raise NotImplementedError()

    def test_a_drawn_store_claims_the_bytes_its_runtime_places(self):
        self.given_two_stores_on_a_drawing_console()
        self.when_both_are_contributed()
        self.assert_claim_of_equals_its_runtime_bytes('first')
        self.assert_claim_of_equals_its_runtime_bytes('second')

    def test_a_second_store_carries_its_own_text_only(self):
        self.given_two_stores_on_a_drawing_console()
        self.when_both_are_contributed()
        self.assert_runtime_pool_of_holds_its_own_text_only('second')
