import asyncio
from collections.abc import Callable
from typing import TypeVar

from bot.utils.logger.logger import logger

T = TypeVar('T')

MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 15.0


async def retry_on_transient_errors(
    operation: Callable[[], T],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    max_delay: float = MAX_DELAY_SECONDS,
) -> T:
    """Run a (possibly blocking) operation, retrying on transient errors.

    Retried:
      - gspread.APIError with HTTP code 408/429/403(usageLimits)/5xx or code -1
        (unparseable API response, usually transient),
      - google.auth.exceptions.RefreshError (stale token),
      - ConnectionError / TimeoutError (network).

    Anything else is raised immediately (no data loss, no infinite retries).
    """
    import gspread.exceptions
    from google.auth import exceptions as google_auth_exceptions

    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except gspread.exceptions.APIError as exc:
            code = exc.code
            if code not in (-1, 408, 429) and code != 403 and not code >= 500:
                # non-transient (400/401/404/409/...): do not retry
                raise
            last_exc = exc
        except (google_auth_exceptions.RefreshError, ConnectionError, TimeoutError) as exc:
            last_exc = exc

        if attempt == max_attempts:
            break

        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
        logger.warning(
            'Transient error (attempt %d/%d): %s; retrying in %.1fs',
            attempt, max_attempts, last_exc, delay,
        )
        await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
