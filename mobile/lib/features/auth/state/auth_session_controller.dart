import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/models/auth_token.dart';

/// Holds the current session's [AuthToken] in memory only.
///
/// Persisting this across app restarts (refresh tokens, secure storage,
/// `devices`/`sessions` rows) is explicitly out of scope for this story —
/// see AUTH-003 ("Stay signed in and manage active sessions").
final authSessionProvider = StateProvider<AuthToken?>((ref) => null);
