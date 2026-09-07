"""KeyPool rotation behaviour."""

from __future__ import annotations

import time

import pytest

from mizoeval.models.keypool import AllKeysExhausted, KeyPool


def test_from_file_reads_one_key_per_line_ignoring_blanks_and_comments(tmp_path):
    f = tmp_path / "keys.txt"
    f.write_text("k1\n\n# a comment\nk2 \n  k3\n", encoding="utf-8")
    pool = KeyPool.from_file(f)
    assert pool.keys == ["k1", "k2", "k3"]


def test_rotate_advances_and_cools_the_previous_key():
    pool = KeyPool(keys=["a", "b", "c"], cooldown_s=60)
    assert pool.current() == "a"
    pool.rotate("http 429")
    assert pool.current() == "b"
    status = pool.status()
    assert status["total_rotations"] == 1
    assert status["cooling"][0]["index"] == 0


def test_rotation_wraps_and_skips_cooling_keys():
    pool = KeyPool(keys=["a", "b"], cooldown_s=60)
    pool.rotate("x")          # a cools, now on b
    pool.rotate("y")          # b cools, wrap -> a still cooling -> exhausted
    with pytest.raises(AllKeysExhausted):
        pool.current()


def test_a_cooled_key_becomes_available_again_after_the_cooldown():
    pool = KeyPool(keys=["a", "b"], cooldown_s=0.2)
    pool.rotate("x")
    pool.rotate("y")
    with pytest.raises(AllKeysExhausted):
        pool.current()
    time.sleep(0.25)
    assert pool.current() in ("a", "b")  # one has cooled off


def test_single_key_pool_is_valid_but_exhausts_immediately_on_rotate():
    pool = KeyPool(keys=["only"])
    assert pool.current() == "only"
    pool.rotate("spent")
    with pytest.raises(AllKeysExhausted):
        pool.current()


def test_empty_pool_is_rejected():
    with pytest.raises(ValueError):
        KeyPool(keys=[])


def test_status_never_exposes_key_values():
    pool = KeyPool(keys=["super-secret-1", "super-secret-2"])
    pool.rotate("429")
    blob = repr(pool.status())
    assert "super-secret" not in blob
