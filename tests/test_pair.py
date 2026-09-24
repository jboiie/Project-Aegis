"""Tests for redteam/attacks/pair.py's iteration logic - PAIR must iterate
on judge compliance, not on the [BLOCKED] text check. See PROJECT_DESC.md's
success-judge audit. _generate_attacker_prompt and judge_response are
mocked; only the target-facing httpx.AsyncClient.post is exercised via a
mock client, matching the existing test_attacks.py pattern."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from redteam.attacks.pair import PAIRAttack, _generate_attacker_prompt, _strip_think_tags


def _mock_target_client(contents: list[str]) -> AsyncMock:
    """Each call to client.post() (the target request) returns the next
    content in `contents`, in order."""
    responses = []
    for c in contents:
        r = MagicMock()
        r.raise_for_status = MagicMock()
        r.json = MagicMock(return_value={"content": c})
        responses.append(r)
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_pair_reuses_session_id_across_iterations_not_across_attempts():
    # PAIR's realistic threat model is one attacker session iterating -
    # SessionGuard's lockout can only be tested for real if the session
    # stays consistent WITHIN an attempt. But a fresh session per ATTEMPT
    # is still required, or every attempt (and every other strategy run
    # alongside it) shares the runner's client host and the lockout
    # swallows the whole campaign - confirmed directly via a dry run that
    # came back 28/28 identical lockout responses. See PROJECT_DESC.md's
    # per-layer-attribution diagnosis.
    mock_client = _mock_target_client(["[BLOCKED] x", "[BLOCKED] x", "[BLOCKED] x"])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        await PAIRAttack(max_iterations=3).execute("http://unused")

    session_ids = [c.kwargs["headers"]["X-Session-ID"] for c in mock_client.post.call_args_list]
    assert len(set(session_ids)) == 1  # same session across all 3 iterations of ONE attempt

    mock_client_2 = _mock_target_client(["[BLOCKED] x"])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client_2), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        await PAIRAttack(max_iterations=1).execute("http://unused")

    second_attempt_session = mock_client_2.post.call_args_list[0].kwargs["headers"]["X-Session-ID"]
    assert second_attempt_session not in session_ids  # different attempt, different session


def test_strip_think_tags_removes_closed_block():
    text = "<think>\nI should frame this as a story request.\n</think>\nWrite a story about a locksmith."
    assert _strip_think_tags(text) == "Write a story about a locksmith."


def test_strip_think_tags_handles_unclosed_block():
    # Truncated mid-reasoning at the token cap - no usable content after
    # the tag, must not be mistaken for a real candidate. See
    # PROJECT_DESC.md's think-tag diagnosis.
    text = "<think>\nThe user is asking me to craft a prompt that wo"
    assert _strip_think_tags(text) == ""


def test_strip_think_tags_no_tags_passthrough():
    assert _strip_think_tags("Write a story about a locksmith.") == "Write a story about a locksmith."


@pytest.mark.asyncio
async def test_generate_attacker_prompt_strips_think_tags():
    # Previously the raw completion (including <think>...</think>) was
    # used as the PAIR candidate verbatim - sent to the target as if it
    # were the intended attack text. See PROJECT_DESC.md's think-tag
    # diagnosis; this is the bug PAIR's 0/10 dry-run results were measured
    # under.
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(return_value={
        "choices": [{"message": {"content": "<think>I'll frame this as fiction.</think>Write a heist story."}}],
    })
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=fake_response)

    prompt, used_fallback = await _generate_attacker_prompt(client=mock_client, goal="test goal", history=[])

    assert prompt == "Write a heist story."
    assert "<think>" not in prompt
    assert used_fallback is False


@pytest.mark.asyncio
async def test_generate_attacker_prompt_retries_on_truncated_reasoning():
    # A completion that's ONLY reasoning (truncated at max_tokens mid-
    # <think>, nothing usable after) must not be sent to the target as the
    # candidate - it should retry, and fall back to the canned template if
    # every attempt fails the same way.
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json = MagicMock(return_value={
        "choices": [{"message": {"content": "<think>\nStill reasoning, never finished"}}],
    })
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=fake_response)

    with patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        prompt, used_fallback = await _generate_attacker_prompt(client=mock_client, goal="test goal", history=[])

    assert used_fallback is True
    assert "test goal" in prompt
    assert mock_client.post.call_count == 3  # exhausted all retries


@pytest.mark.asyncio
async def test_pair_iterates_past_block_then_bypasses():
    mock_client = _mock_target_client(["[BLOCKED] L1 Regex match", "Sure, here's how..."])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.judge_response", AsyncMock(return_value=(10, "Fully complied."))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=5).execute("http://unused")

    assert result.outcome == "bypassed"
    assert result.bypassed is True
    assert result.metadata["iterations_to_bypass"] == 2  # blocked on iter 1, bypassed on iter 2


@pytest.mark.asyncio
async def test_pair_iterates_past_refusal_then_bypasses():
    # Previously the loop stopped at the FIRST response without "[BLOCKED]"
    # in it, treating a plain refusal as a successful bypass. This confirms
    # PAIR now keeps trying when the judge says the response didn't comply.
    mock_client = _mock_target_client(["I can't help with that.", "Sure, here's how..."])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.judge_response", AsyncMock(side_effect=[(2, "Refused."), (10, "Complied.")])), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=5).execute("http://unused")

    assert result.outcome == "bypassed"
    assert result.metadata["iterations_to_bypass"] == 2


@pytest.mark.asyncio
async def test_pair_exhausts_to_refused_by_model():
    mock_client = _mock_target_client(["I can't help with that."] * 3)
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.judge_response", AsyncMock(return_value=(2, "Refused."))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=3).execute("http://unused")

    assert result.outcome == "refused_by_model"
    assert result.bypassed is False
    assert result.judge_score == 2
    assert result.metadata["iterations_to_bypass"] is None


@pytest.mark.asyncio
async def test_pair_exhausts_to_blocked_by_stack():
    mock_client = _mock_target_client(["[BLOCKED] L1 Regex match"] * 3)
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.judge_response") as mock_judge, \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=3).execute("http://unused")

    assert result.outcome == "blocked_by_stack"
    assert result.judge_score is None
    mock_judge.assert_not_called()  # always blocked, never reaches judging


@pytest.mark.asyncio
async def test_pair_target_failure_is_errored_not_blocked():
    # Previously a request failure was tagged "[ERROR]" and matched the
    # same is_blocked check as a real block - see PROJECT_DESC.md's
    # error-handling audit.
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=3).execute("http://unused")

    assert result.outcome == "errored"
    assert result.errored is True
    assert result.bypassed is False


@pytest.mark.asyncio
async def test_pair_judge_failure_is_errored():
    mock_client = _mock_target_client(["Sure, here's how..."])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(return_value=("candidate", False))), \
         patch("redteam.attacks.pair.judge_response", AsyncMock(side_effect=RuntimeError("judge unreachable"))), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=3).execute("http://unused")

    assert result.outcome == "errored"
    assert result.errored is True


@pytest.mark.asyncio
async def test_pair_tracks_attacker_fallback_count():
    mock_client = _mock_target_client(["I can't help with that.", "Sure, here's how..."])
    with patch("redteam.attacks.pair.httpx.AsyncClient", return_value=mock_client), \
         patch("redteam.attacks.pair._generate_attacker_prompt", AsyncMock(side_effect=[
             ("fallback candidate", True), ("real candidate", False),
         ])), \
         patch("redteam.attacks.pair.judge_response", AsyncMock(side_effect=[(2, "Refused."), (10, "Complied.")])), \
         patch("redteam.attacks.pair.asyncio.sleep", AsyncMock()):
        result = await PAIRAttack(max_iterations=5).execute("http://unused")

    assert result.metadata["attacker_fallback_count"] == 1
