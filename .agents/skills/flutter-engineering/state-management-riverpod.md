# Rule: Riverpod & State Management

## Provider Types
* [cite_start]**AsyncNotifierProvider:** Use `AsyncNotifierProvider` for any state that requires asynchronous initialization (e.g., fetching data from an API via Dio).
* **NotifierProvider:** Use `NotifierProvider` for synchronous, local state management.
* **Provider:** Use basic `Provider` strictly for dependency injection (e.g., providing a Repository instance to a Controller).
* **Avoid StateProvider:** Minimize the use of `StateProvider`. Encapsulate logic inside a `Notifier` instead of exposing raw state setters to the UI.

## Data Fetching & Caching
* [cite_start]**Single Source of Truth:** Repositories fetch data via Dio  and return Dart models. Riverpod providers consume repositories and expose `AsyncValue` to the UI.
* **UI State Handling:** The UI must exhaustively pattern-match `AsyncValue` using `.when()`, explicitly handling `data`, `loading`, and `error` states.