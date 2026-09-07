import 'address_form_mode.dart';
import 'saved_address.dart';

/// Arguments passed to `AppRoutes.addressForm` via GoRouter's `extra` — the
/// generic (non-first-address) entry into `AddressFormScreen`, covering
/// both S-12's add/edit and the AC5 re-prompt (whose only difference is a
/// non-null [subtitle]). `AppRoutes.addFirstAddress` (S-05) is a separate,
/// dedicated route/screen and never uses this typedef — see
/// `AddFirstAddressScreen`.
typedef AddressFormArgs = ({
  AddressFormMode mode,
  SavedAddress? existingAddress,
  String? subtitle,
});
