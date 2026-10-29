"""F6.6: the `ARCHITECTURE.md` §5 sanitizing rule, stated in one module.

The rule is the shape a PAN-OS name takes when it becomes a Terraform name. Three names read it:

1. the local name of a block (§5),
2. the unit directory name (`unit_manifest.py`, F6.1 rule 2),
3. the variable name of a site value (`site_data.py`, F6.6).

It lives in a module, and not only in `TerraformGenerator`, because the post-run gate must read it
without the generator: `sanity_checks.check_import_blocks` compares the variable name a block prints
against the value an import id states, and the name is this rule applied to that value. Every caller
takes the rule as an argument or reads it here, so no module defines a second one.

`sanitize` replaces every character outside `[A-Za-z0-9_]` with `_`, strips leading and trailing `_`,
prefixes `_` when the result starts with a digit, and lowercases. A name that sanitizes to nothing is
`UNNAMED`.

Usage:
    from naming import UNNAMED, sanitize, variable_name
    variable_name('fw-2.example.com')    # 'fw_2_example_com'
    unit_manifest.directory_name(facts, sanitize)
"""

import re

# A name that sanitizes to nothing, as §5 states it.
UNNAMED = 'unnamed'


def sanitize(name: str) -> str:
    """The §5 shape of a name."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    sanitized = sanitized.strip('_')
    # An identifier cannot start with a digit, so §5 prefixes an underscore.
    if sanitized and sanitized[0].isdigit():
        sanitized = f'_{sanitized}'
    return sanitized.lower()


def variable_name(value: str) -> str:
    """A site value read through §5 as a Terraform variable name.

    The same rule as `sanitize`, with the §5 fallback, so a value that sanitizes to nothing still
    names a variable. The gate reads this one function, so the emitter and the gate cannot give a
    value two different names.
    """
    return sanitize(value) or UNNAMED


def variable_text(value: str) -> str:
    """The text a block prints for a site value: `var.` plus the §5 name of the value (F6.6).

    The emitter prints this, the gate compares against it, and the tests read it through this function,
    so the three cannot give one value two shapes.
    """
    return f'var.{variable_name(value)}'
