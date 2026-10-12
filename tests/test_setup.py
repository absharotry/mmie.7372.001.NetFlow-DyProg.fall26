"""Phase 0 smoke test: the package is importable and the core libraries load."""


def test_package_imports():
    import apsp

    assert apsp.__version__


def test_core_libraries_import():
    import networkx  # noqa: F401  (correctness oracle)
    import numpy  # noqa: F401
    import scipy.sparse.csgraph  # noqa: F401  (scipy tier)
