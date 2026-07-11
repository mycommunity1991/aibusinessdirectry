# Rule: Validation & Error Handling

## Pydantic v2 Standards
* **V2 Syntax Mandatory:** Strictly use Pydantic v2 methods (`model_validate`, `model_dump`) instead of v1 methods (`parse_obj`, `dict`).
* **Strict Mode:** Enable `model_config = ConfigDict(strict=True)` on critical schemas to prevent silent type coercions (e.g., converting the string "123" to an integer 123).

## Exception Handling
* **Custom Domain Exceptions:** Do not raise raw `HTTPException` inside the business or domain layers. Create custom domain exception classes (e.g., `UserNotFoundException`, `InsufficientPermissionsException`).
* **Centralized Exception Mapping:** Use FastAPI's `@app.exception_handler()` to catch custom domain exceptions at the API layer and translate them into standardized HTTP responses (e.g., mapping `UserNotFoundException` to a `404 Not Found`).

## Standardized Error Responses
* **Consistent Payload:** All API errors must return a consistent JSON structure containing at minimum:
  * `error_code`: A string identifier for the error (e.g., `"USER_NOT_FOUND"`).
  * `message`: A human-readable message.
  * `details`: An optional list of specific validation failures.
* **No Stack Traces:** Never leak stack traces or internal server error details to the client in production.