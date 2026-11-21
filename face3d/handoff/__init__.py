"""face3d.handoff: shape-key stack and Multires hand-off maths (DESIGN 4.17).

Public re-exports of the modules listed in DESIGN 2.3 (finalised by WP-23).  Every name is importable
from its module path as before; a name that exists in two modules is exported once.
Submodules stay importable as attributes (``from face3d.handoff import keys``).
"""
from .keys import (BASIS, ID, ASYM, ARTIST, STAGE_PREFIX, Key, KeyStack, protect_mask, mask_to_data_weights,
    topology_guard, TopologyMismatch, HANDOFF_DEFAULTS)

__all__ = [
    'ARTIST', 'ASYM', 'BASIS', 'HANDOFF_DEFAULTS', 'ID', 'Key', 'KeyStack', 'STAGE_PREFIX',
    'TopologyMismatch', 'mask_to_data_weights', 'protect_mask', 'topology_guard',
]
