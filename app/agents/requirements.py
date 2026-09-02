from datetime import UTC, datetime

from pydantic import SecretStr

from app.models.contracts import AgentResult, RequirementsResult


class RequirementsAgent:
    name = "requirements_agent"

    def __init__(
        self,
        mode: str,
        model_name: str,
        api_key: str | None = None,
    ) -> None:
        self.mode = mode
        self.model_name = model_name
        self.api_key = api_key

    def run(
        self,
        request: str,
    ) -> AgentResult:
        if self.mode == "openai":
            from langchain_openai import ChatOpenAI

            if not self.api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY required"
                )

            model = ChatOpenAI(
                model=self.model_name,
                api_key=SecretStr(self.api_key),
                temperature=0,
            )

            structured = model.with_structured_output(
                RequirementsResult
            )

            artifact = RequirementsResult.model_validate(
                structured.invoke(
                    [
                        (
                            "system",
                            (
                                "You are STEH Requirements Agent. "
                                "Return only structured requirements. "
                                "Identify functional/non-functional "
                                "requirements, acceptance criteria, "
                                "assumptions and open questions."
                            ),
                        ),
                        (
                            "human",
                            request,
                        ),
                    ]
                )
            )

            confidence = 0.90

        else:
            artifact = RequirementsResult(
                functional_requirements=[
                    (
                        "Atender ao objetivo descrito "
                        "na solicitação."
                    )
                ],
                non_functional_requirements=[
                    (
                        "Ser testável, observável e "
                        "segura por padrão."
                    )
                ],
                acceptance_criteria=[
                    "Fluxo principal executável.",
                    "Entradas inválidas rejeitadas.",
                ],
                assumptions=[
                    (
                        "Regras não explicitadas permanecem "
                        "como premissas."
                    )
                ],
                open_questions=[
                    (
                        "Quais SLAs e regras específicas "
                        "de negócio se aplicam?"
                    )
                ],
            )

            confidence = 0.50

        return AgentResult(
            agent=self.name,
            status="SUCCESS",
            result=artifact.model_dump(),
            evidence=[
                {
                    "type": "requirements_artifact",
                    "timestamp": datetime.now(
                        UTC
                    ).isoformat(),
                }
            ],
            confidence=confidence,
        )