import json
import logging
from typing import TypeVar

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.config import Settings, is_placeholder_value

logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMServiceError(RuntimeError):
    pass


class GroqClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key or is_placeholder_value(settings.groq_api_key):
            raise LLMServiceError(
                "GROQ_API_KEY is not configured correctly. Replace the placeholder value in .env with a real Groq API key."
            )
        self._model = settings.groq_model
        self._client = Groq(
            api_key=settings.groq_api_key,
            timeout=settings.groq_timeout_seconds,
            max_retries=2,
        )

    def create_structured(
        self, system_prompt: str, user_prompt: str, output_model: type[ModelT]
    ) -> ModelT:
        schema = output_model.model_json_schema()
        schema_hint = json.dumps(schema, ensure_ascii=False)
        system_message = (
            f"{system_prompt}\n\n"
            "Important: respond with valid JSON only. Do not include markdown fences, explanation, or extra prose. "
            "The output must be a JSON object that matches the schema exactly. "
            f"Expected JSON schema: {schema_hint}"
        )
        user_message = (
            f"{user_prompt}\n\n"
            "Return valid JSON only. Ensure the content is valid JSON and not plain text or markdown. "
            "Match the schema exactly and include every required field."
        )

        last_error: Exception | None = None
        for _ in range(2):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message},
                    ],
                )
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("The model returned an empty response.")
                parsed = json.loads(content)
                return output_model.model_validate(parsed)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning("Groq returned invalid structured output: %s", exc)
                continue
            except Exception as exc:
                logger.exception("Groq request failed")
                raise LLMServiceError(f"The language model request failed: {exc}") from exc

        raise LLMServiceError(f"The language model returned an invalid response: {last_error}") from last_error
