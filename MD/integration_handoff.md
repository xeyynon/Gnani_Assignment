# Integration handoff: backend contracts

The exact interfaces a new STT, TTS or LLM backend has to provide. They're taken from the current code (checked 2026-10-26). If you change one, update this file.

## STT backend (`dukaan_dost/stt_<name>.py`)
Selected by `STT_PROVIDER` in `stt_provider.py`. Today the choices are `sarvam` (the default) and `google`; we're adding `gnani`.

```python
def warmup() -> None: ...

def start_streaming_session(language_code: str | None = None,
                            is_stale=None) -> StreamingSession: ...

class StreamingSession:
    latest_partial: str                      # newest interim text; feeds the speculative knowledge prefetch
    def feed(self, chunk: bytes) -> None: ...  # raw 16 kHz mono s16 PCM, any length
    def finish(self) -> tuple[str, str]: ...   # (transcript, language_code); blocks until final
```
Reference: `stt_sarvam.py` (`StreamingSession` at line ~320, `start_streaming_session` at ~544).

What every backend must do:
- **`is_stale`** is a callable. When it returns True (the call has ended), give up at once, including while waiting for a concurrency slot.
- **Concurrency semaphore:** `stt_sarvam.py` caps sessions with `SARVAM_MAX_CONCURRENT_SESSIONS` (default 10). Copy the pattern with its own env var.
- **`finish()` never raises into the recorder.** On failure it returns `("", language_code)` and logs.
- **Language codes:** BCP-47 like `hi-IN`. Only `en-IN`, `hi-IN` and `te-IN` are accepted downstream (`SUPPORTED_LANGUAGE_CODES`).

Register it:
```python
# stt_provider.py
elif STT_PROVIDER == "gnani":
    from . import stt_gnani as _backend
```

## TTS backend (`dukaan_dost/tts_<name>.py`)
Today `dukaan_dost/app.py` imports straight from `tts_google` (line ~72). We'll add `tts_provider.py`, chosen with `TTS_PROVIDER=google|gnani`, and point that import at it.

```python
def warmup() -> None: ...

def synthesize(text: str, language_code: str) -> bytes | None: ...
    # a complete WAV file, 16 kHz LINEAR16 mono; None on failure

def start_streaming_synthesis(text: str, language_code: str) -> StreamingSynthesis: ...

class StreamingSynthesis:
    def chunks(self): ...          # generator of RAW 16 kHz mono s16 PCM bytes (no WAV header)
    @property
    def failed(self) -> bool: ...  # True if synthesis failed; check after chunks() ends

def needs_digit_spelling(text: str) -> bool: ...
```
What every backend must do:
- **`chunks()` must always end.** The upstream critical bug was a thread that hung forever when client construction failed before its `try/finally`. Wrap the whole worker body so the end sentinel is always sent.
- **Locks around lazy singletons**, for the client, the connection and the voice cache. Warmup and the first call can race.
- **Barge-in:** the caller stops reading `chunks()` partway through. The backend must cope: either finish the request quietly in the background, or close and reopen the connection before the next request (Timbre allows one request at a time per connection).

## LLM (`dukaan_dost/llm_gemini.py`)
```python
def warmup(model: str) -> None: ...
def ask(model, messages, max_tokens, temperature) -> str: ...
def stream(model, messages, max_tokens, temperature): ...  # yields text pieces
```
The change: `_get_client()` uses `genai.Client(api_key=GEMINI_API_KEY)` when that key is set, and otherwise `genai.Client(vertexai=True, project=…, location=…)` as it does today.

## Shop config (`shops/<SHOP_NAME>/`)
- `config.yaml`: **must** have `system_prompt` (a string) and `fallback_messages` (a map from language code to text, e.g. `en-in`, `hi-in`, `te-in`).
- `knowledge/core/always_on.md`: sent on every turn.
- `knowledge/<fixed names>.md`: only these names are read (`KNOWLEDGE_FILES` in `knowledge_retriever.py`): `products_pricing.md`, `ordering_payment.md`, `delivery_shipping.md`, `packaging.md`, `refund_policy.md`, `payment_issues.md`, `faq.md`, `recommendations.md`. Each is split on `##` headings and scored by keyword overlap with the transcript, so **put each product (or small group) under its own `##` heading, with its Hindi and Telugu names in the same section**.

## Keys
Follow the pattern in `dukaan_dost/app.py` (lines ~93–120): try `from local_config import X`, fall back to the env var, and `os.environ.setdefault`. New keys: `GNANI_API_KEY`, `GEMINI_API_KEY`. Add both to `local_config.example.py` with placeholders.
