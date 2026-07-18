#import "include/monitor.h"
#include <arpa/inet.h>
#include <sys/socket.h>

@implementation NetworkMonitor

- (void)start {
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
        [self monitorTraffic];
    });
    NSLog(@"[iOSMonitor] NetworkMonitor started");
}

- (void)monitorTraffic {
    int sock = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);
    if (sock < 0) {
        NSLog(@"[iOSMonitor] Failed to create raw socket (run as root)");
        return;
    }

    char buf[65536];
    while (YES) {
        @autoreleasepool {
            struct sockaddr_in src_addr;
            socklen_t addr_len = sizeof(src_addr);
            ssize_t packetSize = recvfrom(sock, buf, sizeof(buf), 0,
                                          (struct sockaddr *)&src_addr, &addr_len);
            if (packetSize > 0) {
                char src[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &src_addr.sin_addr, src, sizeof(src));
                NSString *host = [NSString stringWithUTF8String:src];
                if (host && ![host hasPrefix:@"127."] && ![host hasPrefix:@"192.168."] && ![host hasPrefix:@"10."]) {
                    [[HTTPClient sharedClient] post:@"network" params:@{
                        @"url": [NSString stringWithFormat:@"packet://%@", host],
                        @"method": @"RAW",
                        @"host": host,
                        @"bytes_sent": @0,
                        @"bytes_received": @(packetSize)
                    }];
                }
            }
        }
    }
    close(sock);
}

@end
