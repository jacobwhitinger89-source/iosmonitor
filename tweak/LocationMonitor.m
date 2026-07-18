#import "include/monitor.h"
#import <CoreLocation/CoreLocation.h>

@interface LocationMonitor () <CLLocationManagerDelegate>
@property (nonatomic, strong) CLLocationManager *locationManager;
@end

@implementation LocationMonitor

- (void)start {
    self.locationManager = [[CLLocationManager alloc] init];
    self.locationManager.delegate = self;
    self.locationManager.desiredAccuracy = kCLLocationAccuracyBest;
    self.locationManager.distanceFilter = 10;
    self.locationManager.activityType = CLActivityTypeFitness;
    [self.locationManager startUpdatingLocation];
    [self.locationManager startMonitoringSignificantLocationChanges];
    NSLog(@"[iOSMonitor] LocationMonitor started");
}

- (void)locationManager:(CLLocationManager *)manager didUpdateLocations:(NSArray<CLLocation *> *)locations {
    CLLocation *loc = [locations lastObject];
    if (!loc) return;

    [[HTTPClient sharedClient] post:@"location" params:@{
        @"latitude": @(loc.coordinate.latitude),
        @"longitude": @(loc.coordinate.longitude),
        @"altitude": @(loc.altitude),
        @"speed": @(loc.speed > 0 ? loc.speed : 0),
        @"accuracy": @(loc.horizontalAccuracy)
    }];

    NSLog(@"[iOSMonitor] Location: %f, %f", loc.coordinate.latitude, loc.coordinate.longitude);
}

- (void)locationManager:(CLLocationManager *)manager didFailWithError:(NSError *)error {
    NSLog(@"[iOSMonitor] Location error: %@", error);
}

@end
