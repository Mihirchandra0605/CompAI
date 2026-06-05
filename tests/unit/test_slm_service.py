from __future__ import annotations

from infrastructure.llm_provider import LLMResponse
from infrastructure.slm_service import SLMService


class FakeLLM:
    def __init__(self) -> None:
        self.last_prompt = ""

    async def generate(self, prompt, system_prompt=None, temperature=0.0, max_tokens=4096):
        self.last_prompt = prompt
        return LLMResponse(content="ok", model="fake")

    async def generate_structured(self, prompt, output_schema, system_prompt=None, temperature=0.0):
        self.last_prompt = prompt
        return {"ok": True}


class FakeVectorStore:
    def search(self, query: str, n_results: int = 3):
        return [
            {
                "content": "TRAI QoS latency clauses require measurable evidence.",
                "metadata": {"source": "trai-qos.txt"},
                "id": "chunk-1",
            }
        ]


async def test_slm_service_augments_prompt_with_rag_context():
    llm = FakeLLM()
    service = SLMService(llm_provider=llm, vector_store=FakeVectorStore())

    response = await service.query("Extract compliance intent.", use_rag=True)

    assert response == "ok"
    assert "RAG Context Provided" in llm.last_prompt
    assert "trai-qos.txt" in llm.last_prompt
    assert "Extract compliance intent." in llm.last_prompt


def test_extract_json_payload_from_markdown_fence():
    from infrastructure.llm_provider import _extract_json_payload

    content = '```json\n{"intents": [{"intent_id": "int:1", "clause_reference": "sec", "description": "desc"}]}\n```'
    extracted = _extract_json_payload(content)

    assert extracted == '{"intents": [{"intent_id": "int:1", "clause_reference": "sec", "description": "desc"}]}'
