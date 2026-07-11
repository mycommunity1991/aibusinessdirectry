# Rule: UI & Material Design 3

## Component Composition
* **Small, Pure Widgets:** Break complex screens down into small, stateless, passive widgets. A widget's `build` method should rarely exceed 50 lines.
* **Avoid Helper Methods:** Prefer extracting UI components into separate `StatelessWidget` classes rather than returning `Widget` from helper methods within the same class (for better Flutter rebuild optimization).

## Design System
* [cite_start]**Material Design 3:** Strictly utilize Material Design 3 (MD3) components and typography. Rely on `Theme.of(context)` for colors and text styles rather than hardcoding values.
* **Responsiveness:** Do not hardcode fixed widths or heights for structural layouts. Use `Expanded`, `Flexible`, and `LayoutBuilder` to ensure the UI scales correctly across all mobile device screen sizes.