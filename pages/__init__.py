# Potential nit (Bug 15): empty __init__.py is sometimes flagged as noise.
# Kept intentionally — declares this as a regular package (vs implicit namespace
# package), preserves tool/IDE compatibility, and leaves a hook for future
# explicit re-exports without restructuring imports.
