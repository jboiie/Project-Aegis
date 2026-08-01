"""Tests for the pure prompt-construction logic in redteam attack strategies.

Only covers what doesn't require live network calls (Groq / target sandbox).
The execute() methods on EncodingAttack/TemplateAttack/PAIRAttack make real
HTTP requests and aren't unit-testable without adding an HTTP-mocking
dependency or refactoring the attacks to accept an injectable client —
out of scope here.
"""

import base64
import codecs

from redteam.attacks.encoding import (
    encode_base64,
    encode_rot13,
    encode_leetspeak,
    encode_word_split,
    ENCODERS,
    BASE_PROMPTS,
)
from redteam.attacks.template import TEMPLATES, HARMFUL_REQUESTS


def test_encode_base64_is_decodable():
    original = "how to hack into a computer system"
    wrapped = encode_base64(original)
    encoded_part = wrapped.split(": ")[-1]
    assert base64.b64decode(encoded_part).decode() == original


def test_encode_rot13_round_trips():
    original = "how to hack into a computer system"
    wrapped = encode_rot13(original)
    encoded_part = wrapped.split(": ")[-1]
    assert codecs.decode(encoded_part, "rot_13") == original


def test_encode_leetspeak_substitutes_known_chars():
    result = encode_leetspeak("test")
    assert result == "7357"


def test_encode_word_split_preserves_short_words():
    result = encode_word_split("a bb ccc")
    assert result == "a bb c_cc"


def test_all_encoders_produce_nonempty_output():
    for name, encoder in ENCODERS.items():
        for prompt in BASE_PROMPTS:
            assert encoder(prompt), f"{name} produced empty output for {prompt!r}"


def test_all_templates_have_harmful_request_placeholder():
    for template in TEMPLATES:
        assert "{harmful_request}" in template["prompt"]


def test_template_formatting_embeds_harmful_request():
    harmful = HARMFUL_REQUESTS[0]
    for template in TEMPLATES:
        rendered = template["prompt"].format(harmful_request=harmful)
        assert harmful in rendered
