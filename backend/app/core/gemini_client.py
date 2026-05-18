import os
import logging
import threading
from app.core.config import settings

logger = logging.getLogger("imaction.gemini_client")

_shared_client = None
_client_lock = threading.Lock()


def get_shared_gemini_client():
    """
    Returns a unified, thread-safe singleton genai.Client.

    Priority order (mirrors Cloud Run deployment reality):
      1. Vertex AI via ADC — when GOOGLE_CLOUD_PROJECT is set.
         On Cloud Run the service account's ADC is automatic; no key needed.
      2. Explicit API key — for local dev without gcloud auth.
      3. Implicit ADC — gcloud application-default login on dev workstation.

    The singleton is created once and reused across embedding + LLM services
    to avoid duplicate HTTP connection pools and redundant credential refreshes.
    """
    global _shared_client

    # Fast-path: client already initialised
    if _shared_client is not None:
        return _shared_client

    with _client_lock:
        # Double-checked locking
        if _shared_client is not None:
            return _shared_client

        project = settings.GOOGLE_CLOUD_PROJECT or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = settings.GOOGLE_CLOUD_LOCATION or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")

        try:
            from google import genai

            if project:
                logger.info(
                    "Initialising Shared Gemini Client via Vertex AI ADC — "
                    f"project={project}, location={location}"
                )
                _shared_client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=location,
                )
            elif api_key:
                logger.info("Initialising Shared Gemini Client via explicit API key.")
                _shared_client = genai.Client(api_key=api_key)
            else:
                logger.info("Initialising Shared Gemini Client via implicit ADC (gcloud auth).")
                _shared_client = genai.Client()

            logger.info("Shared Gemini client ready.")
            return _shared_client

        except ImportError:
            msg = "google-genai SDK is not installed. Run: pip install google-genai>=1.16.0"
            logger.critical(msg)
            raise ImportError(msg)
        except Exception as e:
            logger.critical(f"Failed to initialise shared Gemini client: {e}", exc_info=True)
            raise RuntimeError(f"Shared Gemini client setup failed: {e}")
