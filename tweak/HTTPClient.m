#import "include/monitor.h"

NSString *const kDefaultServerURL = @"http://127.0.0.1:8080";

static HTTPClient *sharedClient = nil;

@implementation HTTPClient

+ (instancetype)sharedClient {
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        sharedClient = [[self alloc] init];
        sharedClient.serverURL = kDefaultServerURL;
    });
    return sharedClient;
}

- (void)post:(NSString *)endpoint params:(NSDictionary *)params {
    NSString *urlStr = [NSString stringWithFormat:@"%@/api/ingest/%@", self.serverURL, endpoint];
    NSURL *url = [NSURL URLWithString:urlStr];
    NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
    req.HTTPMethod = @"POST";
    req.timeoutInterval = 10;

    NSMutableString *body = [NSMutableString string];
    for (NSString *key in params) {
        NSString *value = [params[key] description];
        NSString *encoded = [value stringByAddingPercentEncodingWithAllowedCharacters:[NSCharacterSet URLQueryAllowedCharacterSet]];
        if (body.length > 0) [body appendString:@"&"];
        [body appendFormat:@"%@=%@", key, encoded];
    }
    req.HTTPBody = [body dataUsingEncoding:NSUTF8StringEncoding];
    [req setValue:@"application/x-www-form-urlencoded" forHTTPHeaderField:@"Content-Type"];

    [[[NSURLSession sharedSession] dataTaskWithRequest:req completionHandler:^(NSData *data, NSURLResponse *resp, NSError *err) {
        if (err) NSLog(@"[iOSMonitor] HTTP error: %@", err);
    }] resume];
}

- (void)postImage:(NSString *)endpoint imageData:(NSData *)data {
    NSString *urlStr = [NSString stringWithFormat:@"%@/api/ingest/%@", self.serverURL, endpoint];
    NSURL *url = [NSURL URLWithString:urlStr];
    NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
    req.HTTPMethod = @"POST";
    req.timeoutInterval = 30;

    NSString *boundary = @"----iOSMonitorBoundary";
    [req setValue:[NSString stringWithFormat:@"multipart/form-data; boundary=%@", boundary] forHTTPHeaderField:@"Content-Type"];

    NSMutableData *body = [NSMutableData data];
    [body appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[@"Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[@"Content-Type: image/jpeg\r\n\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:data];
    [body appendData:[[NSString stringWithFormat:@"\r\n--%@--\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    req.HTTPBody = body;

    [[[NSURLSession sharedSession] dataTaskWithRequest:req completionHandler:^(NSData *d, NSURLResponse *r, NSError *err) {
        if (err) NSLog(@"[iOSMonitor] Image upload error: %@", err);
    }] resume];
}

@end
