import 'dart:io';

import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/document_type.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_confirm_screen.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_upload_screen.dart';
import 'package:ai_marketplace_app/shared/data/current_provider_type_repository.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../shared/fakes/fake_current_provider_type_repository.dart';
import 'fakes/fake_verification_document_picker.dart';
import 'fakes/fake_verification_repository.dart';
import 'test_helpers.dart';

void main() {
  group('VerificationUploadScreen (S-19, VER-001, AC2) — Freelancer', () {
    testWidgets(
      'the document type is fixed to Emirates ID, with no chooser and no '
      'skip option',
      (tester) async {
        await pumpVerificationScreen(
          tester,
          child: const VerificationUploadScreen(),
          overrides: [
            currentProviderTypeRepositoryProvider.overrideWithValue(
              FakeCurrentProviderTypeRepository(
                providerType: ProviderType.freelancer,
              ),
            ),
            verificationRepositoryProvider.overrideWithValue(
              FakeVerificationRepository(),
            ),
          ],
        );
        await tester.pumpAndSettle();

        expect(find.textContaining('Emirates ID'), findsOneWidget);
        expect(find.byType(ChoiceChip), findsNothing);
        expect(find.byType(SwitchListTile), findsNothing);
      },
    );

    testWidgets('picking a photo and continuing calls previewDocument with '
        'emiratesId and navigates to the confirm screen', (tester) async {
      final fakeVerificationRepository = FakeVerificationRepository();
      final fakePicker = FakeVerificationDocumentPicker(
        cameraFile: File('/tmp/emirates-id.jpg'),
      );
      await pumpVerificationScreen(
        tester,
        child: const VerificationUploadScreen(),
        overrides: [
          currentProviderTypeRepositoryProvider.overrideWithValue(
            FakeCurrentProviderTypeRepository(
              providerType: ProviderType.freelancer,
            ),
          ),
          verificationRepositoryProvider.overrideWithValue(
            fakeVerificationRepository,
          ),
          verificationDocumentPickerProvider.overrideWithValue(fakePicker),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(OutlinedButton, 'Take Photo'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
      await tester.pumpAndSettle();

      expect(fakeVerificationRepository.previewDocumentCallCount, 1);
      expect(
        fakeVerificationRepository.lastPreviewedDocumentType,
        DocumentType.emiratesId,
      );
      expect(find.byType(VerificationConfirmScreen), findsOneWidget);
    });
  });

  group('VerificationUploadScreen (S-19, VER-001, AC2/Decision 3) — '
      'Business', () {
    testWidgets('shows a document-type chooser and a skip-document toggle', (
      tester,
    ) async {
      await pumpVerificationScreen(
        tester,
        child: const VerificationUploadScreen(),
        overrides: [
          currentProviderTypeRepositoryProvider.overrideWithValue(
            FakeCurrentProviderTypeRepository(
              providerType: ProviderType.business,
            ),
          ),
          verificationRepositoryProvider.overrideWithValue(
            FakeVerificationRepository(),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.byType(ChoiceChip), findsNWidgets(3));
      expect(find.byType(SwitchListTile), findsOneWidget);
    });

    testWidgets(
      'selecting Trade License and continuing previews with tradeLicense, '
      'not the default emiratesId',
      (tester) async {
        final fakeVerificationRepository = FakeVerificationRepository();
        final fakePicker = FakeVerificationDocumentPicker(
          filesFile: File('/tmp/trade-license.pdf'),
        );
        await pumpVerificationScreen(
          tester,
          child: const VerificationUploadScreen(),
          overrides: [
            currentProviderTypeRepositoryProvider.overrideWithValue(
              FakeCurrentProviderTypeRepository(
                providerType: ProviderType.business,
              ),
            ),
            verificationRepositoryProvider.overrideWithValue(
              fakeVerificationRepository,
            ),
            verificationDocumentPickerProvider.overrideWithValue(fakePicker),
          ],
        );
        await tester.pumpAndSettle();

        await tester.tap(find.text('Trade license'));
        await tester.pumpAndSettle();
        await tester.tap(find.widgetWithText(OutlinedButton, 'Choose File'));
        await tester.pumpAndSettle();
        await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
        await tester.pumpAndSettle();

        expect(
          fakeVerificationRepository.lastPreviewedDocumentType,
          DocumentType.tradeLicense,
        );
      },
    );

    testWidgets('toggling "submit without a document" and continuing submits '
        'directly, with no document, and lands on the status screen', (
      tester,
    ) async {
      final fakeVerificationRepository = FakeVerificationRepository();
      await pumpVerificationScreen(
        tester,
        child: const VerificationUploadScreen(),
        overrides: [
          currentProviderTypeRepositoryProvider.overrideWithValue(
            FakeCurrentProviderTypeRepository(
              providerType: ProviderType.business,
            ),
          ),
          verificationRepositoryProvider.overrideWithValue(
            fakeVerificationRepository,
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byType(SwitchListTile));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Continue'));
      await tester.pumpAndSettle();

      expect(fakeVerificationRepository.previewDocumentCallCount, 0);
      expect(fakeVerificationRepository.submitCallCount, 1);
      expect(
        fakeVerificationRepository.lastSubmitRequest!.documentType,
        isNull,
      );
      expect(find.text('verification-status-stub'), findsOneWidget);
    });
  });
}
