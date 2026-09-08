import 'dart:io';

import 'package:ai_marketplace_app/features/provider/data/provider_repository.dart';
import 'package:ai_marketplace_app/features/provider/domain/models/portfolio_photo.dart';
import 'package:ai_marketplace_app/features/provider/presentation/widgets/portfolio_manager.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_portfolio_image_picker.dart';
import 'fakes/fake_provider_repository.dart';

/// Mutable box the test reads after interacting with the widget, updated by
/// [PortfolioManager.onPhotosChanged] -- lets each test assert the visible
/// list without inspecting private State.
class _PhotosHolder {
  _PhotosHolder(this.photos);
  List<PortfolioPhoto> photos;
}

Future<void> _pumpPortfolioManager(
  WidgetTester tester, {
  required _PhotosHolder holder,
  required FakeProviderRepository repository,
  FakePortfolioImagePicker? imagePicker,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        providerRepositoryProvider.overrideWithValue(repository),
        if (imagePicker != null)
          portfolioImagePickerProvider.overrideWithValue(imagePicker),
      ],
      child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: StatefulBuilder(
            builder: (context, setState) {
              return PortfolioManager(
                photos: holder.photos,
                onPhotosChanged: (updated) =>
                    setState(() => holder.photos = updated),
              );
            },
          ),
        ),
      ),
    ),
  );
}

void main() {
  group('PortfolioManager (S-25, PRO-002, item 29) — empty state', () {
    testWidgets(
      'shows empty-state copy and an Add Photo action when there are no '
      'photos yet',
      (tester) async {
        final holder = _PhotosHolder(const []);
        await _pumpPortfolioManager(
          tester,
          holder: holder,
          repository: FakeProviderRepository(),
        );

        expect(
          find.textContaining("haven't added any portfolio photos"),
          findsOneWidget,
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Add Photo'),
          findsOneWidget,
        );
      },
    );
  });

  group('PortfolioManager — add photo', () {
    testWidgets(
      'adding a photo uploads it and appends it to the visible list',
      (tester) async {
        final repository = FakeProviderRepository();
        final picker = FakePortfolioImagePicker(
          fileToReturn: File('/tmp/test-photo.jpg'),
        );
        final holder = _PhotosHolder(const []);
        await _pumpPortfolioManager(
          tester,
          holder: holder,
          repository: repository,
          imagePicker: picker,
        );

        await tester.tap(find.widgetWithText(OutlinedButton, 'Add Photo'));
        await tester.pumpAndSettle();

        expect(picker.pickImageCallCount, 1);
        expect(repository.uploadPortfolioPhotoCallCount, 1);
        expect(holder.photos.length, 1);
        expect(
          find.textContaining("haven't added any portfolio photos"),
          findsNothing,
        );
      },
    );

    testWidgets('cancelling the picker never calls uploadPortfolioPhoto', (
      tester,
    ) async {
      final repository = FakeProviderRepository();
      final picker = FakePortfolioImagePicker(); // fileToReturn defaults null
      final holder = _PhotosHolder(const []);
      await _pumpPortfolioManager(
        tester,
        holder: holder,
        repository: repository,
        imagePicker: picker,
      );

      await tester.tap(find.widgetWithText(OutlinedButton, 'Add Photo'));
      await tester.pumpAndSettle();

      expect(picker.pickImageCallCount, 1);
      expect(repository.uploadPortfolioPhotoCallCount, 0);
      expect(holder.photos, isEmpty);
    });
  });

  group('PortfolioManager — remove photo', () {
    testWidgets(
      'removing a photo calls deletePortfolioPhoto and updates the visible '
      'list',
      (tester) async {
        const existingPhoto = PortfolioPhoto(
          id: 'photo-1',
          mediaUrl: '/media/portfolios/test/1.jpg',
          sortOrder: 0,
        );
        final repository = FakeProviderRepository(
          portfolio: const [existingPhoto],
        );
        final holder = _PhotosHolder(const [existingPhoto]);
        await _pumpPortfolioManager(
          tester,
          holder: holder,
          repository: repository,
        );

        await tester.tap(find.byTooltip('Remove photo'));
        await tester.pumpAndSettle();

        expect(repository.deletePortfolioPhotoCallCount, 1);
        expect(repository.lastDeletedPhotoId, 'photo-1');
        expect(holder.photos, isEmpty);
      },
    );
  });

  group('PortfolioManager — reorder', () {
    testWidgets(
      'moving a photo down calls reorderPortfolio with the new order and '
      'updates the visible list',
      (tester) async {
        const photo1 = PortfolioPhoto(
          id: 'photo-1',
          mediaUrl: '/media/portfolios/test/1.jpg',
          sortOrder: 0,
        );
        const photo2 = PortfolioPhoto(
          id: 'photo-2',
          mediaUrl: '/media/portfolios/test/2.jpg',
          sortOrder: 1,
        );
        final repository = FakeProviderRepository(
          portfolio: const [photo1, photo2],
        );
        final holder = _PhotosHolder(const [photo1, photo2]);
        await _pumpPortfolioManager(
          tester,
          holder: holder,
          repository: repository,
        );

        await tester.tap(find.byTooltip('Move down').first);
        await tester.pumpAndSettle();

        expect(repository.reorderPortfolioCallCount, 1);
        expect(repository.lastReorderedIds, ['photo-2', 'photo-1']);
        expect(holder.photos.map((photo) => photo.id).toList(), [
          'photo-2',
          'photo-1',
        ]);
      },
    );

    testWidgets('the first photo cannot be moved up, the last cannot be '
        'moved down', (tester) async {
      const photo1 = PortfolioPhoto(
        id: 'photo-1',
        mediaUrl: '/media/portfolios/test/1.jpg',
        sortOrder: 0,
      );
      const photo2 = PortfolioPhoto(
        id: 'photo-2',
        mediaUrl: '/media/portfolios/test/2.jpg',
        sortOrder: 1,
      );
      final repository = FakeProviderRepository(
        portfolio: const [photo1, photo2],
      );
      final holder = _PhotosHolder(const [photo1, photo2]);
      await _pumpPortfolioManager(
        tester,
        holder: holder,
        repository: repository,
      );

      final allIconButtons = tester
          .widgetList<IconButton>(find.byType(IconButton))
          .toList();
      final moveUpButtons = allIconButtons
          .where((button) => button.tooltip == 'Move up')
          .toList();
      final moveDownButtons = allIconButtons
          .where((button) => button.tooltip == 'Move down')
          .toList();

      expect(moveUpButtons.first.onPressed, isNull);
      expect(moveDownButtons.last.onPressed, isNull);
    });
  });
}
