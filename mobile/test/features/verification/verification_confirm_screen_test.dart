import 'dart:io';

import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/document_type.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/ocr_preview_result.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_confirm_args.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_exception.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_confirm_screen.dart';
import 'package:ai_marketplace_app/shared/widgets/app_error_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_verification_repository.dart';
import 'test_helpers.dart';

/// The stub OCR pass always returns every field empty (Decision 6,
/// `Plan_S05_VER-001.md`) -- every confirm-screen test starts from this
/// exact shape, never a pre-populated one, since a real extraction never
/// happens in this story.
const _emptyPreview = OcrPreviewResult(
  documentType: DocumentType.emiratesId,
  confidence: 0,
);

void main() {
  group('VerificationConfirmScreen (VER-001, AC4) — honest framing', () {
    testWidgets(
      'fields start empty (never pre-filled with fabricated data) and the '
      'copy never implies a real OCR read happened',
      (tester) async {
        await pumpVerificationScreen(
          tester,
          child: VerificationConfirmScreen(
            args: VerificationConfirmArgs(
              documentType: DocumentType.emiratesId,
              file: File('/tmp/emirates-id.jpg'),
              preview: _emptyPreview,
            ),
          ),
          overrides: [
            verificationRepositoryProvider.overrideWithValue(
              FakeVerificationRepository(),
            ),
          ],
        );
        await tester.pumpAndSettle();

        final fullNameField = tester.widget<TextField>(
          find.widgetWithText(TextField, 'Full name'),
        );
        expect(fullNameField.controller!.text, isEmpty);
        final idNumberField = tester.widget<TextField>(
          find.widgetWithText(TextField, 'ID number'),
        );
        expect(idNumberField.controller!.text, isEmpty);

        // Honest framing (Decision 6) -- never "here's what we read".
        expect(
          find.textContaining("couldn't read your document automatically"),
          findsOneWidget,
        );
        expect(find.textContaining("here's what we read"), findsNothing);
      },
    );
  });

  group('VerificationConfirmScreen (VER-001, AC4/AC8) — editable fields '
      'submit the user\'s own edits', () {
    testWidgets('submitting sends the typed values, not the (empty) preview '
        'response', (tester) async {
      final fakeRepository = FakeVerificationRepository();
      await pumpVerificationScreen(
        tester,
        child: VerificationConfirmScreen(
          args: VerificationConfirmArgs(
            documentType: DocumentType.emiratesId,
            file: File('/tmp/emirates-id.jpg'),
            preview: _emptyPreview,
          ),
        ),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.widgetWithText(TextField, 'Full name'),
        'Fatima Al Suwaidi',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'ID number'),
        '784-1990-1234567-1',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Expiry date'),
        '2030-01-01',
      );
      await tester.pump();

      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(fakeRepository.submitCallCount, 1);
      final request = fakeRepository.lastSubmitRequest!;
      expect(request.documentType, DocumentType.emiratesId);
      expect(request.fullName, 'Fatima Al Suwaidi');
      expect(request.idNumber, '784-1990-1234567-1');
      expect(request.expiryDate, '2030-01-01');

      // Never the (always-null) preview response's fields.
      expect(request.fullName, isNot(_emptyPreview.fullName));
    });

    testWidgets(
      'submitting with every field left blank sends null fields, never '
      'empty-string placeholders',
      (tester) async {
        final fakeRepository = FakeVerificationRepository();
        await pumpVerificationScreen(
          tester,
          child: VerificationConfirmScreen(
            args: VerificationConfirmArgs(
              documentType: DocumentType.emiratesId,
              file: File('/tmp/emirates-id.jpg'),
              preview: _emptyPreview,
            ),
          ),
          overrides: [
            verificationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
        await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
        await tester.pumpAndSettle();

        expect(fakeRepository.submitCallCount, 1);
        final request = fakeRepository.lastSubmitRequest!;
        expect(request.fullName, isNull);
        expect(request.idNumber, isNull);
        expect(request.expiryDate, isNull);
      },
    );

    testWidgets('a failed submission (409 already-in-progress) shows a plain-'
        'language error, never a raw exception', (tester) async {
      final fakeRepository = FakeVerificationRepository(
        submitError: const VerificationException(
          type: VerificationErrorType.submissionNotAllowed,
        ),
      );
      await pumpVerificationScreen(
        tester,
        child: VerificationConfirmScreen(
          args: VerificationConfirmArgs(
            documentType: DocumentType.emiratesId,
            file: File('/tmp/emirates-id.jpg'),
            preview: _emptyPreview,
          ),
        ),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Submit'));
      await tester.tap(find.widgetWithText(FilledButton, 'Submit'));
      await tester.pumpAndSettle();

      expect(find.byType(AppErrorMessage), findsOneWidget);
      expect(
        find.text('You already have a verification submission in progress.'),
        findsOneWidget,
      );
      expect(find.textContaining('VerificationException'), findsNothing);
    });
  });
}
