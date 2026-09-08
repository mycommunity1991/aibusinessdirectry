import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/models/otp_entry_args.dart';
import '../../features/auth/presentation/screens/language_selection_screen.dart';
import '../../features/auth/presentation/screens/otp_entry_screen.dart';
import '../../features/auth/presentation/screens/phone_entry_screen.dart';
import '../../features/auth/presentation/screens/splash_screen.dart';
import '../../features/customer/domain/models/address_form_args.dart';
import '../../features/customer/presentation/screens/add_first_address_screen.dart';
import '../../features/customer/presentation/screens/address_form_screen.dart';
import '../../features/customer/presentation/screens/profile_settings_screen.dart';
import '../../features/customer/presentation/screens/saved_addresses_screen.dart';
import '../../features/home/presentation/screens/home_placeholder_screen.dart';
import '../../features/provider/presentation/screens/business_details_screen.dart';
import '../../features/provider/presentation/screens/choose_provider_type_screen.dart';
import '../../features/provider/presentation/screens/freelancer_details_screen.dart';
import '../../features/provider/presentation/screens/provider_basic_info_screen.dart';
import '../../features/provider/presentation/screens/provider_intro_screen.dart';
import '../../features/provider/presentation/screens/storefront_screen.dart';
import '../../features/verification/domain/models/verification_confirm_args.dart';
import '../../features/verification/presentation/screens/verification_confirm_screen.dart';
import '../../features/verification/presentation/screens/verification_status_screen.dart';
import '../../features/verification/presentation/screens/verification_upload_screen.dart';
import 'app_routes.dart';

/// Builds the app's [GoRouter]. Exposed as a factory (rather than a single
/// top-level instance) so tests can construct an isolated router per case.
GoRouter buildAppRouter({String initialLocation = AppRoutes.splash}) {
  return GoRouter(
    initialLocation: initialLocation,
    routes: [
      GoRoute(
        path: AppRoutes.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppRoutes.language,
        builder: (context, state) => const LanguageSelectionScreen(),
      ),
      GoRoute(
        path: AppRoutes.phoneEntry,
        builder: (context, state) => const PhoneEntryScreen(),
      ),
      GoRoute(
        path: AppRoutes.otpEntry,
        // OTP Entry requires the phone number entered on S-03 — a direct
        // deep link with no `extra` bounces back to Phone Entry instead of
        // rendering with missing data.
        redirect: (context, state) =>
            state.extra is OtpEntryArgs ? null : AppRoutes.phoneEntry,
        builder: (context, state) {
          final args = state.extra as OtpEntryArgs;
          return OtpEntryScreen(
            countryCode: args.countryCode,
            phoneNumber: args.phoneNumber,
            expiresInSeconds: args.expiresInSeconds,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.homePlaceholder,
        builder: (context, state) => const HomePlaceholderScreen(),
      ),
      GoRoute(
        path: AppRoutes.profileSettings,
        builder: (context, state) => const ProfileSettingsScreen(),
      ),
      GoRoute(
        path: AppRoutes.addFirstAddress,
        builder: (context, state) => const AddFirstAddressScreen(),
      ),
      GoRoute(
        path: AppRoutes.savedAddresses,
        builder: (context, state) => const SavedAddressesScreen(),
      ),
      GoRoute(
        path: AppRoutes.addressForm,
        // The shared Add/Edit form always needs its `AddressFormArgs` —
        // reachable only via `push(..., extra: ...)`, never a bare deep
        // link, mirroring OTP Entry's own `extra`-required redirect.
        redirect: (context, state) =>
            state.extra is AddressFormArgs ? null : AppRoutes.savedAddresses,
        builder: (context, state) {
          final args = state.extra as AddressFormArgs;
          return AddressFormScreen(
            mode: args.mode,
            existingAddress: args.existingAddress,
            subtitle: args.subtitle,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.providerIntro,
        builder: (context, state) => const ProviderIntroScreen(),
      ),
      GoRoute(
        path: AppRoutes.chooseProviderType,
        builder: (context, state) => const ChooseProviderTypeScreen(),
      ),
      GoRoute(
        path: AppRoutes.providerBasicInfo,
        builder: (context, state) => const ProviderBasicInfoScreen(),
      ),
      GoRoute(
        path: AppRoutes.businessDetails,
        builder: (context, state) => const BusinessDetailsScreen(),
      ),
      GoRoute(
        path: AppRoutes.freelancerDetails,
        builder: (context, state) => const FreelancerDetailsScreen(),
      ),
      GoRoute(
        path: AppRoutes.storefront,
        builder: (context, state) => const StorefrontScreen(),
      ),
      GoRoute(
        path: AppRoutes.verificationUpload,
        builder: (context, state) => const VerificationUploadScreen(),
      ),
      GoRoute(
        path: AppRoutes.verificationConfirm,
        // The confirm step always needs its `VerificationConfirmArgs` --
        // reachable only via `push(..., extra: ...)`, never a bare deep
        // link, mirroring `AddressFormScreen`'s own `extra`-required
        // redirect.
        redirect: (context, state) => state.extra is VerificationConfirmArgs
            ? null
            : AppRoutes.verificationUpload,
        builder: (context, state) {
          final args = state.extra as VerificationConfirmArgs;
          return VerificationConfirmScreen(args: args);
        },
      ),
      GoRoute(
        path: AppRoutes.verificationStatus,
        builder: (context, state) => const VerificationStatusScreen(),
      ),
    ],
  );
}

/// A single, cached [GoRouter] instance for the running app — created once
/// per [ProviderScope] so navigation state survives widget rebuilds.
final appRouterProvider = Provider<GoRouter>((ref) => buildAppRouter());
