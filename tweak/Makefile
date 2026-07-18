TARGET := iphone:clang:latest:14.0
INSTALL_TARGET_PROCESSES = SpringBoard backboardd

include $(THEOS)/makefiles/common.mk

TWEAK_NAME = iOSMonitorTweak
iOSMonitorTweak_FILES = Tweak.x
iOSMonitorTweak_CFLAGS = -fobjc-arc
iOSMonitorTweak_PRIVATE_FRAMEWORKS = UIKit UserNotifications

TOOL_NAME = iosmonitord
iosmonitord_FILES = main.m HTTPClient.m LocationMonitor.m MessageMonitor.m ScreenCapture.m CallMonitor.m NetworkMonitor.m DeviceMonitor.m
iosmonitord_CFLAGS = -fobjc-arc
iosmonitord_LDFLAGS = -lz
iosmonitord_CODESIGN_FLAGS = -S entitlements.plist
iosmonitord_PRIVATE_FRAMEWORKS = CoreTelephony CoreLocation Foundation SystemConfiguration UIKit

include $(THEOS_MAKE_PATH)/tweak.mk
include $(THEOS_MAKE_PATH)/tool.mk

after-install::
	install.exec "killall -9 iosmonitord 2>/dev/null; launchctl load /Library/LaunchDaemons/com.iosmonitor.daemon.plist"
