import sys, os, types
sys.path.insert(0, os.getcwd())

# Stub heavy backend deps before importing the module under test.
def _stub_module(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m

def fake_generate_stream(prompt, mode=None, system=None):
    yield "Here is a helpful answer about "
    yield "downward dog."
    yield "[Cloud Stream Failed] connection reset by peer"

_stub_module("backend.services.llm_router",
             generate=lambda *a, **k: "ok",
             generate_stream=fake_generate_stream)
_stub_module("backend.services.archivist",
             search_themes_smart=lambda *a, **k: [],
             search_sutras_smart=lambda *a, **k: [],
             search_talking_points=lambda *a, **k: [],
             search_poses_smart=lambda *a, **k: [])
_stub_module("backend.prompts.theme_explanation", THEME_SYSTEM_PROMPT="sys")

from backend.agents.chat_session import ChatSession

s = ChatSession()
list(s.chat_stream("tell me about poses"))

polluted = [m for m in s.history
            if m.get("role") == "assistant" and "[Cloud Stream Failed]" in m.get("content", "")]
if polluted:
    print("REPRODUCED: mid-stream error sentinel persisted to history:", repr(polluted[0]["content"][:80]))
    sys.exit(1)
print("CLEAN: no polluted assistant turn in history")
