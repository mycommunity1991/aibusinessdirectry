import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// The single, reusable text field used across every form in the app —
/// per `docs/AI/07_UI_GUIDELINES.md` ("duplicate UI components are
/// prohibited").
class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    required this.label,
    this.hintText,
    this.controller,
    this.onChanged,
    this.keyboardType,
    this.textInputAction,
    this.inputFormatters,
    this.maxLength,
    this.enabled = true,
    this.autofocus = false,
    this.maxLines = 1,
    this.minLines,
  });

  final String label;
  final String? hintText;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final List<TextInputFormatter>? inputFormatters;
  final int? maxLength;
  final bool enabled;
  final bool autofocus;

  /// Defaults to a single-line field, matching every existing form on this
  /// screen -- pass a larger value (e.g. for the AI Conversation compose
  /// step's free-text description, AI-001) to allow multi-line entry.
  final int? maxLines;
  final int? minLines;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      onChanged: onChanged,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      inputFormatters: inputFormatters,
      maxLength: maxLength,
      enabled: enabled,
      autofocus: autofocus,
      maxLines: maxLines,
      minLines: minLines,
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        counterText: '',
      ),
    );
  }
}
