import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict
from app.core.config import settings

logger = logging.getLogger("imaction.llm")


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for Large Language Model (LLM) Providers.
    Defines the contract for text generation operations.
    """

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generates text synchronously for a given prompt.
        """
        pass

    @abstractmethod
    async def generate_text_async(self, prompt: str, **kwargs) -> str:
        """
        Generates text asynchronously for a given prompt.
        """
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Any, **kwargs) -> Any:
        """
        Generates structured data adhering to a Pydantic schema model.
        """
        pass

    @abstractmethod
    async def generate_structured_async(self, prompt: str, schema: Any, **kwargs) -> Any:
        """
        Generates structured data asynchronously adhering to a Pydantic schema model.
        """
        pass



class MockLLMProvider(BaseLLMProvider):
    """
    Local Offline Mock LLM Provider.
    Returns deterministic/simulated textual responses for quick prototype cycles.
    """

    def __init__(self) -> None:
        logger.info("Initialized MockLLMProvider.")

    def generate_text(self, prompt: str, **kwargs) -> str:
        logger.info("Mock LLM generating response.")
        return f"[Mock LLM Response] Derived output for prompt: '{prompt[:60]}...'"

    async def generate_text_async(self, prompt: str, **kwargs) -> str:
        return self.generate_text(prompt, **kwargs)

    def generate_structured(self, prompt: str, schema: Any, **kwargs) -> Any:
        logger.info(f"Mock LLM generating structured response for schema: {schema.__name__}")
        
        prompt_lower = prompt.lower()
        is_challenge = "challenge" in schema.__name__.lower()
        
        # Isolate the user query or main query topic from the prompt for precise mock routing
        query_text = prompt_lower
        for header in ["user query:", "query:"]:
            idx = prompt_lower.find(header)
            if idx != -1:
                query_text = prompt_lower[idx:idx+250]
                break
                
        if is_challenge:
            # Determine structured Devil's Advocate challenge outputs
            if "payout" in query_text or "stripe" in query_text:
                return schema(
                    originalHypothesis="Stripe webhook payment gateway verification timeouts leading to international bank routing validation failures.",
                    challengeFinding="Detected support tickets reporting delayed processing status instead of direct validation errors, indicating a message queue bottleneck rather than a direct connection failure.",
                    alternativeHypothesis="The queue processor handling the Stripe webhook notifications was saturated and dropping delivery packets under high concurrent transaction load.",
                    riskLevel="MEDIUM",
                    confidenceAdjustment=-0.15,
                    recommendedNextCheck="Inspect RabbitMQ/Celery worker queue length metrics and delivery delay logs during the incident window."
                )
            elif "version" in query_text or "header" in query_text or "api" in query_text:
                return schema(
                    originalHypothesis="API client-server version mismatch on endpoint /v2/payments client header handshakes.",
                    challengeFinding="Found that multiple Legacy API clients were successfully processed during the incident window, indicating that version enforcement was not globally applied.",
                    alternativeHypothesis="Intermittent routing failure at the Nginx API gateway caused header parameters to be stripped during path redirection.",
                    riskLevel="HIGH",
                    confidenceAdjustment=-0.20,
                    recommendedNextCheck="Audit Nginx path redirection rewrite rules and verify if specific header configurations are stripped on redirect."
                )
            else:
                return schema(
                    originalHypothesis="General fintech system network socket timeout on database connection pools.",
                    challengeFinding="No database connection exceptions were found in PostgreSQL primary log lines, but thread pool saturation logs were present.",
                    alternativeHypothesis="Application container CPU throttling under peak traffic restricted connection pool thread creation.",
                    riskLevel="LOW",
                    confidenceAdjustment=-0.05,
                    recommendedNextCheck="Check Kubernetes HPA container CPU/memory usage logs and thread allocation sizes during the event."
                )
        else:
            # Determine SRE incident response structure based on matching strings in prompt
            if "payout" in query_text or "stripe" in query_text:
                return schema(
                    rootCause="Stripe webhook payment gateway verification timeouts leading to international bank routing validation failures.",
                    confidenceScore=0.95,
                    recommendedAction="Update webhook routing endpoints, configure standard routing verification flags, and deploy routing schema upgrades.",
                    supportingEvidenceCount=3,
                    executiveSummary="Recurring network timeouts caused Stripe webhook notifications to fail validation tests. Recommend deploying standard bank routing filters and adjusting SRE routing parameters."
                )
            elif "version" in query_text or "header" in query_text or "api" in query_text:
                return schema(
                    rootCause="API client-server version mismatch on endpoint /v2/payments client header handshakes.",
                    confidenceScore=0.88,
                    recommendedAction="Rollback the latest payment client header push and deploy strict server-side version validation controls.",
                    supportingEvidenceCount=2,
                    executiveSummary="Incompatible API header requirements triggered bad requests (400) on payment flows. Recommending version rollbacks and SRE handshake updates."
                )
            else:
                return schema(
                    rootCause="General fintech system network socket timeout on database connection pools.",
                    confidenceScore=0.75,
                    recommendedAction="Increase pool sizing limits, enable network socket timeout retries, and check database connection statuses.",
                    supportingEvidenceCount=1,
                    executiveSummary="Database socket timeouts degraded payment and routing transactions. Recommend upgrading SRE database connection sizing rules."
                )

    async def generate_structured_async(self, prompt: str, schema: Any, **kwargs) -> Any:
        return self.generate_structured(prompt, schema, **kwargs)



class GeminiLLMProvider(BaseLLMProvider):
    """
    Production Google Gemini and Vertex AI Text Generation Provider.
    Wraps the official google-genai SDK, supporting both Vertex AI and API keys.
    """

    def __init__(self) -> None:
        from app.core.gemini_client import get_shared_gemini_client
        try:
            self.client = get_shared_gemini_client()
        except Exception as e:
            logger.critical(f"Failed to fetch shared google-genai Client for LLM: {e}", exc_info=True)
            raise RuntimeError(f"LLM Provider setup failed: {e}")

    def generate_text(self, prompt: str, **kwargs) -> str:
        # Default model is gemini-2.5-flash for general task execution
        model_name = kwargs.get("model", settings.GEMINI_MODEL)
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Error generating text via Gemini: {e}", exc_info=True)
            raise RuntimeError(f"Gemini LLM Text Generation Failed: {e}")

    async def generate_text_async(self, prompt: str, **kwargs) -> str:
        # Currently, the client offers synchronous calls; we can run in threadpool or wrap
        return self.generate_text(prompt, **kwargs)

    def generate_structured(self, prompt: str, schema: Any, **kwargs) -> Any:
        model_name = kwargs.get("model", settings.GEMINI_MODEL)
        logger.info(f"Gemini LLM generating structured response using {model_name} for schema: {schema.__name__}")
        
        try:
            from google.genai import types
            import json
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1,  # Low temperature for highly analytical deterministic outputs
                )
            )
            
            raw_text = response.text or ""
            # Parse response JSON and validate using the Pydantic schema
            parsed_json = json.loads(raw_text)
            return schema.model_validate(parsed_json)
        except Exception as e:
            logger.error(f"Error generating structured content via Gemini: {e}", exc_info=True)
            raise RuntimeError(f"Gemini LLM Structured Generation Failed: {e}")

    async def generate_structured_async(self, prompt: str, schema: Any, **kwargs) -> Any:
        return self.generate_structured(prompt, schema, **kwargs)



# ==============================================================================
# Singleton Provider Instance & Factory
# ==============================================================================
_llm_provider_instance: BaseLLMProvider = None


def get_llm_provider() -> BaseLLMProvider:
    """
    Singleton factory function returning the configured BaseLLMProvider.
    """
    global _llm_provider_instance
    if _llm_provider_instance is None:
        provider_type = settings.LLM_PROVIDER.lower().strip()
        if provider_type == "gemini":
            _llm_provider_instance = GeminiLLMProvider()
        else:
            _llm_provider_instance = MockLLMProvider()
            
    return _llm_provider_instance
