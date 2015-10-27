import blinker

signals = blinker.Namespace()

frozen_tree_created = signals.signal('frozen-tree-created')

frozen_tree_updated = signals.signal('frozen-tree-updated')

frozen_tree_invalidated = signals.signal('frozen-tree-invalidated')