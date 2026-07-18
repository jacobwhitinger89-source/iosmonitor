#import "include/monitor.h"
#import <UIKit/UIKit.h>
#import <SystemConfiguration/CaptiveNetwork.h>
#import <dlfcn.h>

@interface DeviceMonitor ()
@property (nonatomic, strong) NSTimer *timer;
@end

@implementation DeviceMonitor

- (void)start {
    dispatch_async(dispatch_get_main_queue(), ^{
        self.timer = [NSTimer scheduledTimerWithTimeInterval:60.0 repeats:YES block:^(NSTimer *t) {
            [self reportStatus];
        }];
        [self reportStatus];
    });
    NSLog(@"[iOSMonitor] DeviceMonitor started");
}

- (void)reportStatus {
    UIDevice *dev = [UIDevice currentDevice];
    dev.batteryMonitoringEnabled = YES;
    float level = dev.batteryLevel;
    BOOL charging = (dev.batteryState == UIDeviceBatteryStateCharging ||
                     dev.batteryState == UIDeviceBatteryStateFull);

    NSString *wifi = @"";
    NSArray *interfaces = (__bridge_transfer NSArray *)CNCopySupportedInterfaces();
    for (id iface in interfaces) {
        NSDictionary *info = (__bridge_transfer NSDictionary *)CNCopyCurrentNetworkInfo((__bridge CFStringRef)iface);
        if (info[@"SSID"]) {
            wifi = info[@"SSID"];
            break;
        }
    }

    int signal = 0;
    void *libCT = dlopen("/System/Library/Frameworks/CoreTelephony.framework/CoreTelephony", RTLD_LAZY);
    if (libCT) {
        Class CTClass = NSClassFromString(@"CTTelephonyNetworkInfo");
        if (CTClass) {
            id ctInfo = [[CTClass alloc] init];
            id radioTech = [ctInfo performSelector:@selector(serviceCurrentRadioAccessTechnology)];
            if (radioTech) signal = 3;
        }
        dlclose(libCT);
    }

    [[HTTPClient sharedClient] post:@"device_status" params:@{
        @"battery_level": @(level >= 0 ? level * 100 : 0),
        @"is_charging": @(charging),
        @"wifi_ssid": wifi ?: @"",
        @"signal_strength": @(signal)
    }];
}

@end
