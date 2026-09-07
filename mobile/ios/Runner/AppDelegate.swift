import Flutter
import GoogleMaps
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Map-pin selection (CUS-002, AC3, `google_maps_flutter`). Blank
    // placeholder -- a real key is an external prerequisite supplied later
    // (mirrors AUTH-002's accepted native-config gap,
    // `Plan_S03_CUS-002.md`). Maps will not render on a real device until a
    // real key replaces this.
    GMSServices.provideAPIKey("")
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }
}
