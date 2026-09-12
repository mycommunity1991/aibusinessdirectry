import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/network/api_config.dart';
import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/models/provider_type.dart';
import '../../../../shared/utils/rating_label.dart';
import '../../../../shared/widgets/app_error_message.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/unclaimed_banner.dart';
import '../../../../shared/widgets/verified_badge.dart';
import '../../../../shared/widgets/weekly_hours_editor.dart';
import '../../../provider/domain/models/weekday_availability.dart';
import '../../domain/models/provider_profile.dart';
import '../../domain/models/provider_profile_args.dart';
import '../../domain/models/provider_profile_exception.dart';
import '../../state/provider_profile_controller.dart';
import '../utils/provider_profile_error_copy.dart';
import '../widgets/contact_reveal_sheet.dart';

/// S-09 -- Provider Profile (CON-001, AC5). Name, category, description,
/// primary photo, rating+review-count together (never rating alone),
/// weekly hours, a subtype-specific service-area field, the shared
/// [UnclaimedBanner]/[VerifiedBadge] as applicable (Decision 8), and a
/// sticky bottom Contact CTA that opens the [ContactRevealSheet] (AC2) --
/// no quote request, approval wait, or in-app messaging step exists
/// anywhere between tapping Contact and seeing the phone number.
class ProviderProfileScreen extends ConsumerWidget {
  const ProviderProfileScreen({super.key, required this.args});

  final ProviderProfileArgs args;

  /// CLM-001, Decision 8 -- the unclaimed banner's CTA navigates straight
  /// to the Claim OTP screen (S-22) for this specific listing, mirroring
  /// `SearchResultsScreen._onClaimTap`'s identical pattern.
  void _onClaimTap(BuildContext context, String providerId) {
    context.push(AppRoutes.claimOtp, extra: providerId);
  }

  void _onContactTap(BuildContext context) {
    ContactRevealSheet.show(context, args);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(providerProfileControllerProvider(args.providerId));

    return Scaffold(
      appBar: AppBar(title: Text(l10n.providerProfileTitle)),
      body: SafeArea(
        child: switch (state.status) {
          ProviderProfileStatus.loading => Center(
            child: LoadingIndicator(label: l10n.loadingLabel),
          ),
          ProviderProfileStatus.error => _ErrorState(
            error: state.error!,
            onRetry: () => ref
                .read(
                  providerProfileControllerProvider(args.providerId).notifier,
                )
                .retry(),
          ),
          ProviderProfileStatus.loaded => _ProfileContent(
            profile: state.profile!,
            onClaimTap: () => _onClaimTap(context, state.profile!.id),
          ),
        },
      ),
      bottomNavigationBar: state.status == ProviderProfileStatus.loaded
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: PrimaryButton(
                  key: const ValueKey('provider-profile-contact-button'),
                  label: l10n.providerProfileContactButtonLabel,
                  onPressed: () => _onContactTap(context),
                ),
              ),
            )
          : null,
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});

  final ProviderProfileException error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppErrorMessage(
              message: providerProfileErrorMessage(context, error),
            ),
            const SizedBox(height: AppSpacing.md),
            OutlinedButton(onPressed: onRetry, child: Text(l10n.retryLabel)),
          ],
        ),
      ),
    );
  }
}

class _ProfileContent extends StatelessWidget {
  const _ProfileContent({required this.profile, required this.onClaimTap});

  final ProviderProfile profile;
  final VoidCallback onClaimTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Decision 8's first precedence state -- rendered regardless of
          // `verificationStatus` whenever the listing is unclaimed.
          if (!profile.isClaimed) UnclaimedBanner(onTap: onClaimTap),
          _ProfilePhoto(photoUrl: profile.primaryPhotoUrl),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        profile.displayName,
                        key: const ValueKey('provider-profile-display-name'),
                        style: textTheme.headlineSmall,
                      ),
                    ),
                    // Decision 8's second precedence state -- only ever
                    // shown once `!profile.isClaimed` above is false.
                    if (profile.isVerified) const VerifiedBadge(),
                  ],
                ),
                if (profile.categoryLabels.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    profile.categoryLabels.join(' • '),
                    style: textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
                const SizedBox(height: AppSpacing.xs),
                Text(
                  ratingWithReviewCountLabel(
                    l10n,
                    averageRating: profile.averageRating,
                    reviewCount: profile.reviewCount,
                  ),
                  key: const ValueKey('provider-profile-rating'),
                  style: textTheme.bodyMedium,
                ),
                if (profile.description != null &&
                    profile.description!.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.md),
                  Text(profile.description!, style: textTheme.bodyLarge),
                ],
                const SizedBox(height: AppSpacing.lg),
                _ServiceAreaSection(profile: profile),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  l10n.providerProfileHoursLabel,
                  style: textTheme.titleMedium,
                ),
                const SizedBox(height: AppSpacing.xs),
                _HoursSection(availability: profile.weeklyAvailability),
                // Room for the sticky bottom Contact CTA not to overlap the
                // last line of content.
                const SizedBox(height: AppSpacing.xxl),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfilePhoto extends StatelessWidget {
  const _ProfilePhoto({required this.photoUrl});

  final String? photoUrl;

  static const double _height = 200;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final photoUrl = this.photoUrl;

    if (photoUrl == null) {
      return _placeholder(colorScheme);
    }
    return Image.network(
      '${ApiConfig.mediaOrigin}$photoUrl',
      height: _height,
      width: double.infinity,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) => _placeholder(colorScheme),
    );
  }

  Widget _placeholder(ColorScheme colorScheme) {
    return Container(
      height: _height,
      width: double.infinity,
      color: colorScheme.surfaceContainerHighest,
      child: Icon(
        Icons.storefront_outlined,
        size: 48,
        color: colorScheme.onSurfaceVariant,
      ),
    );
  }
}

/// AC5's subtype-specific service-area field: a Business's city/region and
/// delivery radius, or a Freelancer's travel radius. Renders nothing at all
/// if the provider has no service-area data on record, rather than an
/// empty heading.
class _ServiceAreaSection extends StatelessWidget {
  const _ServiceAreaSection({required this.profile});

  final ProviderProfile profile;

  static String _km(int meters) => (meters / 1000).toStringAsFixed(1);

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final lines = <String>[];

    if (profile.providerType == ProviderType.business) {
      final location = [
        profile.city,
        profile.region,
      ].whereType<String>().where((value) => value.isNotEmpty).join(', ');
      if (location.isNotEmpty) lines.add(location);
      final deliveryRadiusMeters = profile.deliveryRadiusMeters;
      if (deliveryRadiusMeters != null) {
        lines.add(
          l10n.providerProfileDeliveryRadiusLabel(_km(deliveryRadiusMeters)),
        );
      }
    } else {
      final serviceRadiusMeters = profile.serviceRadiusMeters;
      if (serviceRadiusMeters != null) {
        lines.add(
          l10n.providerProfileServiceRadiusLabel(_km(serviceRadiusMeters)),
        );
      }
    }

    if (lines.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.providerProfileServiceAreaLabel,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: AppSpacing.xs),
        for (final line in lines)
          Text(line, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

/// AC5's weekly-hours display -- a read-only rendering of exactly the same
/// seven [WeekdayAvailability] entries `GET /providers/{id}` returns,
/// reusing [weeklyHoursOrderedDays]/[weekdayLabel]/[parseTimeOfDay] from the
/// shared `WeeklyHoursEditor` (`shared/widgets/weekly_hours_editor.dart`)
/// rather than duplicating the day-ordering/labeling logic -- this screen
/// never lets the customer edit hours, so the interactive editor widget
/// itself isn't reused, only its shared helpers.
class _HoursSection extends StatelessWidget {
  const _HoursSection({required this.availability});

  final List<WeekdayAvailability> availability;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final textTheme = Theme.of(context).textTheme;
    final byDay = {for (final entry in availability) entry.weekday: entry};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final day in weeklyHoursOrderedDays)
          Padding(
            key: ValueKey('provider-profile-hours-$day'),
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
            child: Row(
              children: [
                Expanded(child: Text(weekdayLabel(l10n, day))),
                Text(
                  _hoursLabel(context, l10n, byDay[day]),
                  style: textTheme.bodyMedium,
                ),
              ],
            ),
          ),
      ],
    );
  }

  String _hoursLabel(
    BuildContext context,
    AppLocalizations l10n,
    WeekdayAvailability? entry,
  ) {
    if (entry == null || !entry.isOpen) return l10n.closedLabel;
    final openTime = entry.openTime;
    final closeTime = entry.closeTime;
    if (openTime == null || closeTime == null) return l10n.closedLabel;
    final open = parseTimeOfDay(openTime).format(context);
    final close = parseTimeOfDay(closeTime).format(context);
    return '$open - $close';
  }
}
