from gpthub_orchestrator.classifier import classify_messages


def test_text_only_simple():
    m = [{"role": "user", "content": "hello"}]
    c = classify_messages(m)
    assert "text" in c["modalities"]
    assert c["task_type"] == "simple_chat"


def test_image_triggers_vision_task():
    m = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "what is this"},
                {"type": "image_url", "image_url": {"url": "https://example.com/x.png"}},
            ],
        }
    ]
    c = classify_messages(m)
    assert "image" in c["modalities"]
    assert c["task_type"] in ("image_analysis", "multimodal_workflow")
