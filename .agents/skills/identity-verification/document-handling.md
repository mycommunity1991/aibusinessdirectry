# Rule: Document Handling

## Upload Security
* **Validate Before Storing:** Every uploaded document is checked for MIME type, extension, and max size per `06_SECURITY.md` before a `verification_documents` row is written; the original filename is never trusted or persisted as the storage key.
* **Unique Storage Keys:** Generate a unique filename/key per upload — never store user-supplied filenames directly in the file path.

## Sensitive Data
* **Government ID Data at Rest:** Emirates ID numbers and equivalent government identifiers are sensitive PII — encrypt at the field level in addition to disk-level encryption, and never include them in logs, error messages, or admin action metadata.
