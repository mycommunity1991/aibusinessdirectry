import 'package:flutter/widgets.dart';
import 'package:intl/intl.dart';

import '../../l10n/generated/app_localizations.dart';

/// Formats [value] relative to "now" (`DateTime.now()`, read fresh on each
/// call) in coarse buckets -- "Just now," "X minutes ago," "X hours ago,"
/// "X days ago" -- falling back to an absolute short date once [value] is
/// more than ~30 days in the past (LEAD-001, AC1's "relative timestamp").
///
/// No new package dependency: `intl` is already a dependency of this app's
/// own generated localizations (`flutter gen-l10n`) -- reused here only for
/// the final absolute-date fallback's locale-aware formatting, mirroring
/// `rating_label.dart`'s "small, dependency-free, `AppLocalizations`-backed
/// formatter" shape.
String formatRelativeTime(BuildContext context, DateTime value) {
  final l10n = AppLocalizations.of(context);
  final difference = DateTime.now().difference(value);

  if (difference.inMinutes < 1) return l10n.relativeTimeJustNowLabel;
  if (difference.inHours < 1) {
    return l10n.relativeTimeMinutesAgoLabel(difference.inMinutes);
  }
  if (difference.inDays < 1) {
    return l10n.relativeTimeHoursAgoLabel(difference.inHours);
  }
  if (difference.inDays < 30) {
    return l10n.relativeTimeDaysAgoLabel(difference.inDays);
  }
  final locale = Localizations.localeOf(context).toString();
  return DateFormat.yMMMd(locale).format(value);
}
