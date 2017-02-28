"""Small plugin to reduce SNAKES duplicated checks in the context of
Medusa benchmarks.
"""

import snakes.plugins

@snakes.plugins.plugin("snakes.nets")
def extend (module) :
    class Transition (module.Transition) :
        def enabled (self, binding) :
            return True
    return Transition
