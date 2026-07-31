import concurrent.futures
import logging
import os

logger = logging.getLogger("granite_client")

DEFAULT_OLLAMA_MODEL = "granite4:1b"
DEFAULT_WATSONX_MODEL_ID = "ibm/granite-3-8b-instruct"
DEFAULT_WATSONX_URL = "https://us-south.ml.cloud.ibm.com"


class GraniteClient:
    """
    Wrapper for IBM Granite LLM calls.

    Provider is selected via the LLM_PROVIDER env var:
      - "watsonx" (default): calls IBM watsonx.ai. If the call errors or
        times out (missing credentials, network issue, etc.) it falls back
        to a local Ollama Granite model so demos stay reliable offline.
      - "ollama": always uses the local Ollama Granite model directly -
        useful for offline dev/demo without watsonx credentials.
    """

    def __init__(self, model: str = None, provider: str = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "watsonx")).lower()
        # GRANITE_MODEL is the single knob for swapping the local demo model
        # (e.g. granite4:1b vs granite4:3b) without touching code; OLLAMA_MODEL
        # is kept as a fallback name for backwards compatibility.
        self.ollama_model = (
            model
            or os.getenv("GRANITE_MODEL")
            or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        )
        self.watsonx_model_id = os.getenv("WATSONX_MODEL_ID", DEFAULT_WATSONX_MODEL_ID)
        self.watsonx_timeout = float(os.getenv("WATSONX_TIMEOUT_SECONDS", "30"))
        # Generous but still finite: on CPU-only inference a single call can
        # legitimately take 100-170s+ for longer prompts (e.g. resume
        # analysis with rewrite suggestions), so this needs real headroom
        # above observed worst-case latency, not just the "typical" case -
        # the point is bounding a genuine hang, not racing normal slowness.
        self.ollama_timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "240"))
        # How long Ollama keeps the model resident in memory after a call
        # before unloading it. Ollama's own default is 5m; a demo doing many
        # back-to-back calls benefits from holding it much longer so a gap
        # between requests doesn't force a multi-second-to-multi-minute
        # reload. "-1" means keep loaded indefinitely.
        self.ollama_keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self._watsonx_model = None

    def generate(self, prompt: str) -> str:
        if self.provider == "watsonx":
            try:
                return self._generate_watsonx(prompt)
            except Exception as exc:
                logger.warning(
                    "watsonx.ai call failed (%s); falling back to local Ollama Granite model '%s'.",
                    exc,
                    self.ollama_model,
                )

        # No mock/canned-response fallback here on purpose: a genuine Ollama
        # failure or timeout must propagate to the caller so each agent's
        # own honest fallback (fallback_used flag, 503 to the client, etc.)
        # runs - silently returning fake data would defeat that everywhere.
        return self._generate_ollama(prompt)

    def _get_watsonx_model(self):
        if self._watsonx_model is not None:
            return self._watsonx_model

        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            url=os.getenv("WATSONX_URL", DEFAULT_WATSONX_URL),
            api_key=os.environ["WATSONX_API_KEY"],
        )

        self._watsonx_model = ModelInference(
            model_id=self.watsonx_model_id,
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )
        return self._watsonx_model

    def _generate_watsonx(self, prompt: str) -> str:
        model = self._get_watsonx_model()

        # Enforce a hard wall-clock timeout independent of the SDK's own
        # HTTP client, since a hung watsonx call must not block a demo.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(model.generate_text, prompt=prompt)
            return future.result(timeout=self.watsonx_timeout)

    def _generate_ollama(self, prompt: str) -> str:
        from ollama import chat

        def _call():
            response = chat(
                model=self.ollama_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                keep_alive=self.ollama_keep_alive,
            )
            return response["message"]["content"]

        # Same hard wall-clock timeout pattern as _generate_watsonx above -
        # without this, a stalled Ollama daemon (crashed model worker,
        # network hiccup, wedged connection) blocks the calling thread
        # forever with no way for any caller up the stack to recover.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call)
            return future.result(timeout=self.ollama_timeout)
    