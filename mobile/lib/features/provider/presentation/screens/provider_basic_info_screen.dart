import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_routes.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../l10n/generated/app_localizations.dart';
import '../../../../shared/widgets/app_text_field.dart';
import '../../../../shared/widgets/primary_button.dart';
import '../../../../shared/widgets/step_indicator.dart';
import '../../../../shared/models/provider_type.dart';
import '../../state/provider_onboarding_controller.dart';

/// S-17 — Provider Basic Info (PRO-001, AC4): display name, phone/country
/// code, WhatsApp number (with a "same as phone number" convenience
/// toggle), a free-text category, and an optional description. Routes to
/// S-18a (Business Details) or S-18b (Freelancer Details) based on
/// `ProviderOnboardingController`'s already-set type — this screen never
/// sets or changes the type itself (AC3).
class ProviderBasicInfoScreen extends ConsumerStatefulWidget {
  const ProviderBasicInfoScreen({super.key});

  @override
  ConsumerState<ProviderBasicInfoScreen> createState() =>
      _ProviderBasicInfoScreenState();
}

class _ProviderBasicInfoScreenState
    extends ConsumerState<ProviderBasicInfoScreen> {
  final _displayNameController = TextEditingController();
  final _phoneCountryCodeController = TextEditingController(text: '+971');
  final _phoneNumberController = TextEditingController();
  final _whatsappController = TextEditingController();
  final _categoryController = TextEditingController();
  final _descriptionController = TextEditingController();

  bool _sameAsPhone = false;

  @override
  void initState() {
    super.initState();
    for (final controller in [
      _displayNameController,
      _phoneCountryCodeController,
      _phoneNumberController,
      _categoryController,
    ]) {
      controller.addListener(_onChanged);
    }
  }

  void _onChanged() => setState(() {});

  @override
  void dispose() {
    _displayNameController.dispose();
    _phoneCountryCodeController.dispose();
    _phoneNumberController.dispose();
    _whatsappController.dispose();
    _categoryController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  bool get _canContinue =>
      _displayNameController.text.trim().isNotEmpty &&
      _phoneCountryCodeController.text.trim().isNotEmpty &&
      _phoneNumberController.text.trim().isNotEmpty &&
      _categoryController.text.trim().isNotEmpty;

  void _onSameAsPhoneChanged(bool value) {
    setState(() {
      _sameAsPhone = value;
      if (value) {
        _whatsappController.text =
            '${_phoneCountryCodeController.text.trim()}'
            '${_phoneNumberController.text.trim()}';
      }
    });
  }

  void _onContinue() {
    if (!_canContinue) return;
    final controller = ref.read(providerOnboardingControllerProvider.notifier);
    final whatsapp = _whatsappController.text.trim();
    final description = _descriptionController.text.trim();

    controller.setBasicInfo(
      displayName: _displayNameController.text.trim(),
      phoneCountryCode: _phoneCountryCodeController.text.trim(),
      phoneNumber: _phoneNumberController.text.trim(),
      whatsappNumber: whatsapp.isEmpty ? null : whatsapp,
      categoryLabel: _categoryController.text.trim(),
      description: description.isEmpty ? null : description,
    );

    final providerType = ref
        .read(providerOnboardingControllerProvider)
        .providerType;
    if (providerType == ProviderType.freelancer) {
      context.push(AppRoutes.freelancerDetails);
    } else {
      context.push(AppRoutes.businessDetails);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    // Keeps `providerOnboardingControllerProvider` (`autoDispose`) alive for
    // as long as this screen stays on the navigation stack -- see
    // `ChooseProviderTypeScreen`'s identical `watch` for why this matters.
    ref.watch(providerOnboardingControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.providerBasicInfoTitle)),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const StepIndicator(
                currentStep: 2,
                totalSteps: providerWizardTotalSteps,
              ),
              const SizedBox(height: AppSpacing.lg),
              AppTextField(
                label: l10n.providerDisplayNameFieldLabel,
                controller: _displayNameController,
              ),
              const SizedBox(height: AppSpacing.md),
              Row(
                children: [
                  SizedBox(
                    width: 96,
                    child: AppTextField(
                      label: l10n.countryCodeFieldLabel,
                      controller: _phoneCountryCodeController,
                      keyboardType: TextInputType.phone,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: AppTextField(
                      label: l10n.phoneNumberFieldLabel,
                      hintText: l10n.phoneNumberFieldHint,
                      controller: _phoneNumberController,
                      keyboardType: TextInputType.phone,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.providerWhatsappFieldLabel,
                controller: _whatsappController,
                keyboardType: TextInputType.phone,
                enabled: !_sameAsPhone,
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(l10n.providerSameAsPhoneLabel),
                value: _sameAsPhone,
                onChanged: _onSameAsPhoneChanged,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.providerCategoryFieldLabel,
                hintText: l10n.providerCategoryFieldHint,
                controller: _categoryController,
              ),
              const SizedBox(height: AppSpacing.md),
              AppTextField(
                label: l10n.providerDescriptionFieldLabel,
                controller: _descriptionController,
              ),
              const SizedBox(height: AppSpacing.xl),
              PrimaryButton(
                label: l10n.continueLabel,
                onPressed: _canContinue ? _onContinue : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
