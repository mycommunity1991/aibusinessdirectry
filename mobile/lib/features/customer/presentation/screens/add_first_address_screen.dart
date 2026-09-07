import 'package:flutter/widgets.dart';

import '../../../../l10n/generated/app_localizations.dart';
import 'address_form_screen.dart';

/// S-05 — the skippable first-address prompt shown right after
/// registration (`Plan_S03_CUS-002.md` item 21). A thin wrapper around
/// [AddressFormScreen]: `mode: add`, `skippable: true`, and the address is
/// always saved as the customer's default (it's necessarily their first —
/// no toggle shown).
///
/// Reached by `otp_entry_screen.dart`'s `_onVerify` and
/// `phone_entry_screen.dart`'s `_handleOAuthResult` in place of navigating
/// straight to the Home placeholder — both call
/// `authSessionControllerProvider.setSession(token)` first, so the session
/// is already fully live by the time this screen renders and "Skip" can
/// never block registration completion (AC4).
class AddFirstAddressScreen extends StatelessWidget {
  const AddFirstAddressScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AddressFormScreen(
      mode: AddressFormMode.add,
      skippable: true,
      titleOverride: l10n.addFirstAddressTitle,
      subtitle: l10n.addFirstAddressSubtitle,
      showDefaultToggle: false,
      forcedIsDefault: true,
    );
  }
}
