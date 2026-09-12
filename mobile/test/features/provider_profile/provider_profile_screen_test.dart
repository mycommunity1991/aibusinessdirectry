import 'package:ai_marketplace_app/features/provider/domain/models/weekday_availability.dart';
import 'package:ai_marketplace_app/features/provider_profile/data/provider_profile_repository.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/contact_reveal.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_args.dart';
import 'package:ai_marketplace_app/features/provider_profile/domain/models/provider_profile_exception.dart';
import 'package:ai_marketplace_app/features/provider_profile/presentation/screens/provider_profile_screen.dart';
import 'package:ai_marketplace_app/shared/models/provider_type.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_provider_profile_repository.dart';
import 'test_helpers.dart';

/// S-09 -- Provider Profile (CON-001, AC5).
void main() {
  const ProviderProfileArgs args = (
    providerId: 'provider-1',
    searchRequestId: null,
  );

  List<WeekdayAvailability> weekAvailability({required bool mondayOpen}) {
    return [
      WeekdayAvailability(
        weekday: 'monday',
        isOpen: mondayOpen,
        openTime: mondayOpen ? '09:00' : null,
        closeTime: mondayOpen ? '18:00' : null,
      ),
      const WeekdayAvailability(weekday: 'tuesday', isOpen: false),
      const WeekdayAvailability(weekday: 'wednesday', isOpen: false),
      const WeekdayAvailability(weekday: 'thursday', isOpen: false),
      const WeekdayAvailability(weekday: 'friday', isOpen: false),
      const WeekdayAvailability(weekday: 'saturday', isOpen: false),
      const WeekdayAvailability(weekday: 'sunday', isOpen: false),
    ];
  }

  ProviderProfile businessProfile({
    required bool isClaimed,
    required String verificationStatus,
    double? averageRating,
    int reviewCount = 0,
  }) {
    return ProviderProfile(
      id: 'provider-1',
      providerType: ProviderType.business,
      displayName: 'Al Noor Plumbing Services LLC',
      categoryLabels: const ['Plumbing'],
      description: 'Reliable plumbing repairs across the city.',
      averageRating: averageRating,
      reviewCount: reviewCount,
      isClaimed: isClaimed,
      verificationStatus: verificationStatus,
      weeklyAvailability: weekAvailability(mondayOpen: true),
      city: 'Dubai',
      region: 'Dubai',
      deliveryRadiusMeters: 5000,
    );
  }

  testWidgets(
    'a load failure shows a plain-language error, with retry (mirrors '
    'SearchResultsScreen\'s pattern)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        getProviderProfileError: const ProviderProfileException(
          type: ProviderProfileErrorType.unknown,
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Something went wrong. Please try again.'),
        findsOneWidget,
      );
      expect(find.text('Try again'), findsOneWidget);
    },
  );

  testWidgets(
    'is_claimed == false renders the shared Unclaimed banner regardless of '
    'verification_status, never the Verified badge (Decision 8, state 1)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: false,
          verificationStatus: 'approved',
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Unclaimed — Is this your business? Claim it'),
        findsOneWidget,
      );
      expect(find.text('Verified'), findsNothing);
    },
  );

  testWidgets(
    'tapping the Unclaimed banner navigates to the Claim OTP screen for '
    'this listing',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: false,
          verificationStatus: 'approved',
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.text('Unclaimed — Is this your business? Claim it'),
      );
      await tester.pumpAndSettle();

      expect(find.text('claim-otp-stub-provider-1'), findsOneWidget);
    },
  );

  testWidgets(
    'is_claimed == true && verification_status == approved renders the '
    'Verified badge, never the Unclaimed banner (Decision 8, state 2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: true,
          verificationStatus: 'approved',
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Verified'), findsOneWidget);
      expect(
        find.text('Unclaimed — Is this your business? Claim it'),
        findsNothing,
      );
    },
  );

  testWidgets('claimed but pending/under_review/rejected renders neither badge '
      '(Decision 8, state 3)', (tester) async {
    final fakeRepository = FakeProviderProfileRepository(
      profile: businessProfile(isClaimed: true, verificationStatus: 'pending'),
    );

    await pumpProviderProfileScreen(
      tester,
      child: const ProviderProfileScreen(args: args),
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('Verified'), findsNothing);
    expect(
      find.text('Unclaimed — Is this your business? Claim it'),
      findsNothing,
    );
  });

  testWidgets('renders "No reviews yet" for a null average_rating, never a '
      'synthesized "0.0 (0 reviews)" (AC5)', (tester) async {
    final fakeRepository = FakeProviderProfileRepository(
      profile: businessProfile(isClaimed: true, verificationStatus: 'approved'),
    );

    await pumpProviderProfileScreen(
      tester,
      child: const ProviderProfileScreen(args: args),
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('No reviews yet'), findsOneWidget);
  });

  testWidgets(
    'renders rating and review count together, e.g. "4.8 (3 reviews)" '
    '(AC5 -- never rating alone)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: true,
          verificationStatus: 'approved',
          averageRating: 4.8,
          reviewCount: 3,
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('4.8 (3 reviews)'), findsOneWidget);
    },
  );

  testWidgets('renders the weekly hours for each day (AC5)', (tester) async {
    final fakeRepository = FakeProviderProfileRepository(
      profile: businessProfile(isClaimed: true, verificationStatus: 'approved'),
    );

    await pumpProviderProfileScreen(
      tester,
      child: const ProviderProfileScreen(args: args),
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('Hours'), findsOneWidget);
    expect(find.text('Monday'), findsOneWidget);
    expect(find.text('Tuesday'), findsOneWidget);
    // Tuesday-Sunday are all closed in this fixture -- rendered at least
    // six times (one per closed day).
    expect(find.text('Closed'), findsNWidgets(6));
  });

  testWidgets(
    'renders a Business provider\'s service area (city/region + delivery '
    'radius) (AC5)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: true,
          verificationStatus: 'approved',
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.text('Service area'), findsOneWidget);
      expect(find.text('Dubai, Dubai'), findsOneWidget);
      expect(find.text('Delivers within 5.0 km'), findsOneWidget);
    },
  );

  testWidgets("renders a Freelancer provider's travel radius, not a Business's "
      'delivery-radius copy (AC5)', (tester) async {
    final freelancerProfile = ProviderProfile(
      id: 'provider-2',
      providerType: ProviderType.freelancer,
      displayName: 'Fatima Al Falasi',
      reviewCount: 0,
      isClaimed: true,
      verificationStatus: 'approved',
      weeklyAvailability: weekAvailability(mondayOpen: false),
      serviceRadiusMeters: 10000,
    );
    final fakeRepository = FakeProviderProfileRepository(
      profile: freelancerProfile,
    );

    await pumpProviderProfileScreen(
      tester,
      child: const ProviderProfileScreen(args: args),
      overrides: [
        providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('Travels up to 10.0 km'), findsOneWidget);
    expect(find.textContaining('Delivers within'), findsNothing);
  });

  testWidgets(
    'tapping the sticky Contact CTA opens the Contact Reveal sheet, which '
    'immediately reveals the phone number (AC2)',
    (tester) async {
      final fakeRepository = FakeProviderProfileRepository(
        profile: businessProfile(
          isClaimed: true,
          verificationStatus: 'approved',
        ),
        contactReveal: const ContactReveal(
          id: 'contact-view-1',
          providerId: 'provider-1',
          providerDisplayName: 'Al Noor Plumbing Services LLC',
          phoneCountryCode: '+971',
          phoneNumber: '501234567',
        ),
      );

      await pumpProviderProfileScreen(
        tester,
        child: const ProviderProfileScreen(args: args),
        overrides: [
          providerProfileRepositoryProvider.overrideWithValue(fakeRepository),
        ],
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Contact'));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('contact-reveal-phone-number')),
        findsOneWidget,
      );
      expect(fakeRepository.createContactViewCallCount, 1);
    },
  );
}
