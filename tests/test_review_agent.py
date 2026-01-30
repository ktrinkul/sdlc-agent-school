from src.agents.review_agent import ReviewAgent


class FakeGitHub:
    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        return "diff"

    def get_workflow_runs(self, repo: str, pr_number: int):
        return [{"id": 1}]


class FakeLLM:
    def generate_structured(self, prompt: str, system: str | None = None) -> dict:
        return {"decision": "APPROVE"}


def test_review_agent_review_pr() -> None:
    agent = ReviewAgent(github=FakeGitHub(), llm=FakeLLM())
    response = agent.review_pr("owner/repo", 1, "issue")

    assert response["decision"] == "APPROVE"
