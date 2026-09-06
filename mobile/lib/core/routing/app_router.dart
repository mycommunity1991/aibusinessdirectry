import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/domain/models/otp_entry_args.dart';
import '../../features/auth/presentation/screens/language_selection_screen.dart';
import '../../features/auth/presentation/screens/otp_entry_screen.dart';
import '../../features/auth/presentation/screens/phone_entry_screen.dart';
import '../../features/auth/presentation/screens/splash_screen.dart';
import '../../features/customer/presentation/screens/profile_settings_screen.dart';
import '../../features/home/presentation/screens/home_placeholder_screen.dart';
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
    ],
  );
}

/// A single, cached [GoRouter] instance for the running app — created once
/// per [ProviderScope] so navigation state survives widget rebuilds.
final appRouterProvider = Provider<GoRouter>((ref) => buildAppRouter());
