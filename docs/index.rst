Text
====

Text a cartridge carries by address: records authored as plain Python
dataclasses, a pool of every distinct string stored once, an alphabet
ordered by frequency so a common character costs one byte, and glyphs
kept only for the characters the text uses, one bit per pixel, from
any typeface a game brings. The extension knows what text costs and
how to draw a glyph; where text is drawn belongs to whoever owns the
surface.

A game never imports this package. It declares a ``TextStore`` and the
runtime finds the resolver through the ``eightiesdk.game_extensions``
entry point:

.. code-block:: python

   class Quiz(Game):
       def declare(self):
           self.bank = TextStore(QUESTIONS)

.. toctree::
   :maxdepth: 2
   :caption: The extension

   overview
   declaration
   storage
   drawing
   proving

.. toctree::
   :maxdepth: 1
   :caption: Reference

   adr/index
   api
