"""Golden routing + role prompt merge (classifier + router + messages)."""

from __future__ import annotations

import os

os.environ.setdefault("LITELLM_BASE_URL", "http://127.0.0.1:9")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "k")

from gpthub_orchestrator.classifier import classify_messages
from gpthub_orchestrator.messages import apply_role_system_messages
from gpthub_orchestrator.role_prompts import load_role_prompts
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings


def _settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "litellm_base_url": "http://127.0.0.1:9",
        "orchestrator_api_key": "k",
    }
    base.update(kwargs)
    return Settings(**base)


def test_golden_simple_chat_fast_text():
    msgs = [{"role": "user", "content": "Привет, как дела?"}]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "simple_chat"
    rs = choose_model(cl, _settings())
    assert rs["model_role"] == "fast_text"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert out[0]["role"] == "system"
    assert "[GPTHub role: fast_text]" in out[0]["content"]


def test_golden_summarize_letter_doc_synthesis():
    msgs = [{"role": "user", "content": "Суммаризируй это письмо про дедлайн"}]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "summarization"
    rs = choose_model(cl, _settings())
    assert rs["model_role"] == "doc_synthesis"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: doc_synthesis]" in out[0]["content"]


def test_golden_traceback_code_local():
    msgs = [{"role": "user", "content": "Traceback: NameError in async def foo()"}]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "code_help"
    rs = choose_model(cl, _settings(code_route_preference="local"))
    assert rs["model_role"] == "reasoning_code_local"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: reasoning_code_local]" in out[0]["content"]


def test_golden_traceback_code_openrouter():
    msgs = [{"role": "user", "content": "Traceback: NameError in async def foo()"}]
    cl = classify_messages(msgs)
    rs = choose_model(cl, _settings(code_route_preference="openrouter"))
    assert rs["model_role"] == "reasoning_code_openrouter"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: reasoning_code_openrouter]" in out[0]["content"]


def test_golden_pdf_architecture_doc_synthesis():
    msgs = [{"role": "user", "content": "Проанализируй PDF с архитектурой системы"}]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "summarization"
    rs = choose_model(cl, _settings())
    assert rs["model_role"] == "doc_synthesis"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: doc_synthesis]" in out[0]["content"]


def test_golden_screenshot_vision():
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Что не так на этом скриншоте?"},
                {"type": "image_url", "image_url": {"url": "https://example.com/s.png"}},
            ],
        }
    ]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "image_analysis"
    rs = choose_model(cl, _settings())
    assert rs["model_role"] == "vision_general"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: vision_general]" in out[0]["content"]
    assert out[1] == msgs[0]


def test_golden_multimodal_debug_vision():
    msgs = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "debug this UI screenshot"},
                {"type": "image_url", "image_url": {"url": "https://example.com/ui.png"}},
            ],
        }
    ]
    cl = classify_messages(msgs)
    assert cl["task_type"] == "multimodal_workflow"
    rs = choose_model(cl, _settings())
    assert rs["model_role"] == "vision_general"
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    assert "[GPTHub role: vision_general]" in out[0]["content"]


def test_client_system_appended_after_role_prompt():
    msgs = [
        {"role": "system", "content": "Отвечай кратко по-французски."},
        {"role": "user", "content": "hello"},
    ]
    cl = classify_messages([msgs[1]])
    rs = choose_model(cl, _settings())
    pr = load_role_prompts()
    out = apply_role_system_messages(msgs, rs["model_role"], pr)
    sys_content = out[0]["content"]
    assert "[GPTHub role: fast_text]" in sys_content
    assert "французски" in sys_content
    assert "Additional instructions (from chat client)" in sys_content
