"""Sales module: point-of-sale orders, payments and returns.

Offline-first: each order carries a client-generated ``client_uuid`` so a
retried sync never creates a duplicate. Completing a sale emits
``SaleCompleted``; inventory reacts to it at the composition root (the two
modules never import each other — see the ``module-independence`` contract).
"""
