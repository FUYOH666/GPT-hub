from gpthub_orchestrator.model_registry import load_model_roles


def test_load_packaged_model_roles_v4():
    reg = load_model_roles()
    assert reg.version == 2
    assert reg.roles["fast_text"].chain == "catalog.text_fast"
    assert reg.roles["vision_general"].chain == "catalog.vision"
