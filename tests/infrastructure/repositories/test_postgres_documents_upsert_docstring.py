"""Pins the M5 module docstring so the false 'xmax = 0' claim cannot
recur and any future regression that mis-describes the upsert is caught.

We assert on the module source string directly (rather than constructing
a stub repo) so the test does not require a live Postgres connection and
matches the way `tests/infrastructure/repositories/test_documents_m7_upsert.py`
covers the actual behavior.
"""
import inspect
import pathlib

from src.infrastructure.repositories.postgres import documents as pg_docs


def test_postgres_upsert_docstring_describes_actual_strategy():
    """The docstring must describe SELECT ... FOR UPDATE + ON CONFLICT
    and the content_checksum discriminator. It must NOT claim an
    'xmax = 0' heuristic (that was carried from a now-incorrect prior
    draft and the real code uses content_checksum comparison).
    """
    source = pathlib.Path(inspect.getsourcefile(pg_docs)).read_text(encoding="utf-8")
    doc_end = source.index("from __future__")
    docstring_text = source[:doc_end]

    # Positive: the docstring must describe the real mechanism.
    lowered = docstring_text.lower()
    assert "on conflict" in lowered, (
        "module docstring must mention ON CONFLICT DO UPDATE so future "
        "drift can't reintroduce a docstring that hides the real strategy"
    )
    assert "content_checksum" in lowered, (
        "module docstring must name content_checksum as the discriminator "
        "between was_inserted / was_replaced / was_unchanged"
    )
    assert "for update" in lowered, (
        "module docstring must mention FOR UPDATE so readers know the "
        "SELECT pre-snapshot is locking the row"
    )

    # Negative: the false "xmax = 0 heuristic" claim must be absent.
    # `xmax` may appear inside a denial sentence ("we do not rely on
    # xmax"); it must not appear as a positive heuristic.
    heuristic_marker = "xmax = 0"
    assert heuristic_marker not in lowered, (
        "module docstring must NOT present an 'xmax = 0' heuristic; "
        "the real code uses content_checksum, not asyncpg-exposed xmax"
    )


def test_postgres_upsert_docstring_preserves_method_signature():
    """Sanity: refining the docstring must not touch the method body."""
    source = pathlib.Path(inspect.getsourcefile(pg_docs)).read_text(encoding="utf-8")
    assert "async def upsert_by_source(" in source, (
        "the upsert_by_source method must still exist; this test guards "
        "against an over-eager docstring refactor removing behavior"
    )
