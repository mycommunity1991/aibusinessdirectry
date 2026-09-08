import 'package:ai_marketplace_app/features/verification/data/verification_repository.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/document_type.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_document.dart';
import 'package:ai_marketplace_app/features/verification/domain/models/verification_record.dart';
import 'package:ai_marketplace_app/features/verification/presentation/screens/verification_status_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_verification_repository.dart';
import 'test_helpers.dart';

void main() {
  group('VerificationStatusScreen (S-20, VER-001, AC6) — empty state', () {
    testWidgets(
      'shows "not submitted yet" copy and a Start Verification CTA when '
      'getMyCurrentStatus returns null',
      (tester) async {
        final fakeRepository = FakeVerificationRepository();
        await pumpVerificationScreen(
          tester,
          child: const VerificationStatusScreen(),
          overrides: [
            verificationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.getMyCurrentStatusCallCount, 1);
        expect(
          find.text("You haven't submitted verification yet."),
          findsOneWidget,
        );
        expect(
          find.widgetWithText(FilledButton, 'Start Verification'),
          findsOneWidget,
        );

        await tester.tap(
          find.widgetWithText(FilledButton, 'Start Verification'),
        );
        await tester.pumpAndSettle();

        expect(find.text('verification-upload-stub'), findsOneWidget);
      },
    );
  });

  group('VerificationStatusScreen (S-20, VER-001) — each status renders '
      'its own badge/copy', () {
    testWidgets('pending renders the "under review" badge and copy', (
      tester,
    ) async {
      await pumpVerificationScreen(
        tester,
        child: const VerificationStatusScreen(),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(
            FakeVerificationRepository(existingRecord: fakePendingRecord()),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Under review'), findsOneWidget);
      expect(
        find.textContaining("We're reviewing your documents"),
        findsOneWidget,
      );
      expect(find.widgetWithText(FilledButton, 'Resubmit'), findsNothing);
    });

    testWidgets('under_review renders the same "under review" badge/copy '
        'as pending', (tester) async {
      await pumpVerificationScreen(
        tester,
        child: const VerificationStatusScreen(),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(
            FakeVerificationRepository(existingRecord: fakeUnderReviewRecord()),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Under review'), findsOneWidget);
      expect(
        find.textContaining("We're reviewing your documents"),
        findsOneWidget,
      );
    });

    testWidgets('approved renders the "Approved" badge and success copy', (
      tester,
    ) async {
      await pumpVerificationScreen(
        tester,
        child: const VerificationStatusScreen(),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(
            FakeVerificationRepository(existingRecord: fakeApprovedRecord()),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Approved'), findsOneWidget);
      expect(find.textContaining("You're verified"), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Resubmit'), findsNothing);
    });

    testWidgets('rejected renders the "Rejected" badge, the plain-language '
        'rejection reason, and a Resubmit action routing to S-19', (
      tester,
    ) async {
      await pumpVerificationScreen(
        tester,
        child: const VerificationStatusScreen(),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(
            FakeVerificationRepository(
              existingRecord: fakeRejectedRecord(
                rejectionReason: 'The photo was too blurry to read.',
              ),
            ),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Rejected'), findsOneWidget);
      expect(find.text('The photo was too blurry to read.'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Resubmit'));
      await tester.pumpAndSettle();

      expect(find.text('verification-upload-stub'), findsOneWidget);
    });
  });

  group('VerificationStatusScreen (VER-001, Decision 7) — document '
      'previews never use a raw URL', () {
    testWidgets(
      'fetches a submitted document\'s bytes through the repository and '
      'renders them in-app, never via a network URL',
      (tester) async {
        final fakeRepository = FakeVerificationRepository(
          existingRecord: VerificationRecord(
            id: 'record-with-document',
            status: VerificationRecordStatus.pending,
            submittedAt: DateTime.utc(2026, 1, 1),
            documents: const [
              VerificationDocument(
                id: 'doc-1',
                documentType: DocumentType.emiratesId,
              ),
            ],
          ),
          documentBytesById: const {
            'doc-1': [1, 2, 3],
          },
        );
        await pumpVerificationScreen(
          tester,
          child: const VerificationStatusScreen(),
          overrides: [
            verificationRepositoryProvider.overrideWithValue(fakeRepository),
          ],
        );
        await tester.pumpAndSettle();

        expect(fakeRepository.getDocumentBytesCallCount, 1);
        expect(fakeRepository.lastRequestedDocumentId, 'doc-1');
        expect(find.byType(Image), findsWidgets);
      },
    );
  });

  group('VerificationStatusScreen (VER-001) — never another account\'s '
      'data', () {
    testWidgets('renders exactly what the (per-call-authenticated) repository '
        'returns for the caller, with no id ever passed to '
        'getMyCurrentStatus', (tester) async {
      final fakeRepository = FakeVerificationRepository(
        existingRecord: fakeApprovedRecord(id: 'my-own-record'),
      );
      await pumpVerificationScreen(
        tester,
        child: const VerificationStatusScreen(),
        overrides: [
          verificationRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      // `getMyCurrentStatus()` takes no id parameter at all -- there is
      // no route through which this screen could request, or the
      // repository could return, another account's record.
      expect(fakeRepository.getMyCurrentStatusCallCount, 1);
      expect(find.text('Approved'), findsOneWidget);
    });
  });
}
