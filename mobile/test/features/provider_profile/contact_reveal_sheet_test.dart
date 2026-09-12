import 'package:ai_marketplace_app/core/theme/app_theme.dart';
import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_reveal.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_args.dart';
import 'package:ai_marketplace_app/features/provider_profile/presentation/utils/contact_launcher.dart';
import 'package:ai_marketplace_app/features/provider_profile/presentation/widgets/contact_reveal_sheet.dart';
import 'package:ai_marketplace_app/l10n/generated/app_localizations.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_contact_launcher.dart';
import 'fakes/fake_provider_profile_repository.dart';

/// The Contact Reveal bottom sheet (CON-001, AC2/AC6).
void main() {
  const ProviderProfileArgs args = (
    providerId: 'provider-1',
    searchRequestId: null,
  );

  Future<void> pumpSheet(
    WidgetTester tester, {
    required List<Override> overrides,
    Locale? locale,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides,
        child: MaterialApp(
          theme: AppTheme.light(),
          locale: locale,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => ContactRevealSheet.show(context, args),
                child: const Text('open-sheet'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('open-sheet'));
    await tester.pumpAndSettle();
  }

  const reveal = ContactReveal(
    id: 'contact-view-1',
    providerId: 'provider-1',
    providerDisplayName: 'Al Noor Plumbing Services LLC',
    phoneCountryCode: '+971',
    phoneNumber: '501234567',
  );

  testWidgets(
    'immediately shows the phone number and a Call button on success -- '
    'no quote/approval/messaging step in between (AC2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: reveal,
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(find.text('+971 501234567'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('contact-reveal-call-button')),
        findsOneWidget,
      );
      expect(fakeRepository.createContactViewCallCount, 1);
      expect(fakeRepository.lastCreateContactViewArgs, (
        providerId: 'provider-1',
        searchRequestId: null,
      ));
    },
  );

  testWidgets(
    'shows the WhatsApp button only when whatsapp_number is present (AC2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: const ContactReveal(
          id: 'contact-view-1',
          providerId: 'provider-1',
          providerDisplayName: 'Al Noor Plumbing Services LLC',
          phoneCountryCode: '+971',
          phoneNumber: '501234567',
          whatsappNumber: '+971501234567',
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.byKey(const ValueKey('contact-reveal-whatsapp-button')),
        findsOneWidget,
      );
    },
  );

  testWidgets('omits the WhatsApp button when whatsapp_number is null', (
    tester,
  ) async {
    final fakeRepository = FakeProviderProfileRepository(contactReveal: reveal);

    await pumpSheet(
      tester,
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );

    expect(
      find.byKey(const ValueKey('contact-reveal-whatsapp-button')),
      findsNothing,
    );
  });

  testWidgets(
    'always includes the "contact happens outside the app" note (AC6)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: reveal,
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.byKey(const ValueKey('contact-reveal-outside-app-note')),
        findsOneWidget,
      );
      expect(
        find.text("You'll be leaving the app to contact them directly."),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'always includes the "contact happens outside the app" note in Arabic '
    'too, not only English (AC6, Plan_S08_CON-001.md Verification Plan)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: reveal,
      );

      await pumpSheet(
        tester,
        locale: const Locale('ar'),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.byKey(const ValueKey('contact-reveal-outside-app-note')),
        findsOneWidget,
      );
      expect(
        find.text('ستغادر التطبيق للتواصل معهم مباشرة.'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'tapping Call launches the device dialer with the combined country '
    'code and number, no spaces (AC2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: reveal,
      );
      final fakeLauncher = FakeContactLauncher();

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
          contactLauncherProvider.overrideWithValue(fakeLauncher),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('contact-reveal-call-button')),
      );
      await tester.pump();

      expect(fakeLauncher.lastCallPhoneNumber, '+971501234567');
    },
  );

  testWidgets(
    'tapping WhatsApp launches with digits only -- no "+"/spaces/dashes '
    '(AC2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        contactReveal: const ContactReveal(
          id: 'contact-view-1',
          providerId: 'provider-1',
          providerDisplayName: 'Al Noor Plumbing Services LLC',
          phoneCountryCode: '+971',
          phoneNumber: '501234567',
          whatsappNumber: '+971 50-123-4567',
        ),
      );
      final fakeLauncher = FakeContactLauncher();

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
          contactLauncherProvider.overrideWithValue(fakeLauncher),
        ],
      );

      await tester.tap(
        find.byKey(const ValueKey('contact-reveal-whatsapp-button')),
      );
      await tester.pump();

      expect(fakeLauncher.lastWhatsAppNumber, '971501234567');
    },
  );

  testWidgets(
    'a self-dealing rejection (403) shows a clear, specific message, never '
    'a raw status code (AC3/AC4, Decision 10)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        createContactViewError: const ContactException(
          type: ContactErrorType.selfDealing,
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(find.text("You can't contact your own listing."), findsOneWidget);
      expect(
        find.byKey(const ValueKey('contact-reveal-phone-number')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'a generic failure shows a plain-language error, with a retry that '
    're-calls the repository',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        createContactViewError: const ContactException(
          type: ContactErrorType.network,
        ),
      );

      await pumpSheet(
        tester,
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );

      expect(
        find.text(
          "We couldn't connect. Check your internet connection and try again.",
        ),
        findsOneWidget,
      );
      expect(fakeRepository.createContactViewCallCount, 1);

      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();

      expect(fakeRepository.createContactViewCallCount, 2);
    },
  );
}
