#import "PixelFonts.h"
static UIColor *AGInk(void){return [UIColor colorWithRed:40/255.0 green:77/255.0 blue:112/255.0 alpha:1];}
static UIColor *AGPaper(void){return [UIColor colorWithRed:198/255.0 green:213/255.0 blue:237/255.0 alpha:1];}
static UIImage *AGFontImage(BOOL title){
    static UIImage *body,*heading;static dispatch_once_t once;
    dispatch_once(&once,^{body=[UIImage imageWithData:[[NSData alloc]initWithBase64EncodedString:AGBodyPNG options:0]];heading=[UIImage imageWithData:[[NSData alloc]initWithBase64EncodedString:AGTitlePNG options:0]];});
    return title?heading:body;
}
static NSUInteger AGGlyph(unichar c,BOOL title){
    NSString *chars=title?AGTitleChars:AGBodyChars;
    NSRange r=[chars rangeOfString:[NSString stringWithCharacters:&c length:1]];
    return r.location==NSNotFound?0:r.location;
}
static CGFloat AGTextWidth(NSString *text,BOOL title){
    const unsigned char *widths=title?AGTitleWidths:AGBodyWidths;CGFloat w=0;
    for(NSUInteger i=0;i<text.length;i++)w+=widths[AGGlyph([text characterAtIndex:i],title)];return w;
}
static void AGPixelText(NSString *text,CGFloat cx,CGFloat y,CGFloat maxWidth,CGFloat scale,BOOL title){
    text=[text precomposedStringWithCanonicalMapping];CGFloat w=AGTextWidth(text,title);if(w>0)scale=fmin(scale,maxWidth/w);
    CGFloat x=cx-w*scale/2;
    UIImage *image=AGFontImage(title);CGFloat height=title?21:13;const unsigned char *widths=title?AGTitleWidths:AGBodyWidths;
    CGContextRef c=UIGraphicsGetCurrentContext();CGContextSaveGState(c);CGContextSetInterpolationQuality(c,kCGInterpolationNone);CGContextSetShouldAntialias(c,NO);
    for(NSUInteger i=0;i<text.length;i++){
        NSUInteger glyph=AGGlyph([text characterAtIndex:i],title);
        CGImageRef crop=CGImageCreateWithImageInRect(image.CGImage,CGRectMake(0,glyph*height,image.size.width,height));
        if(crop){[[UIImage imageWithCGImage:crop]drawInRect:CGRectMake(round(x),round(y),image.size.width*scale,height*scale)];CGImageRelease(crop);}
        x+=widths[glyph]*scale;
    }
    CGContextRestoreGState(c);
}
@interface AGPixelButton:UIButton
@end
@implementation AGPixelButton
- (void)setHighlighted:(BOOL)value{[super setHighlighted:value];[self setNeedsDisplay];}
- (void)setEnabled:(BOOL)value{[super setEnabled:value];[self setNeedsDisplay];}
- (void)drawRect:(CGRect)rect{
    [(self.highlighted?[UIColor colorWithRed:1 green:.9 blue:.3 alpha:1]:AGPaper())setFill];UIRectFill(rect);
    CGContextRef c=UIGraphicsGetCurrentContext();CGContextSetAlpha(c,self.enabled?1:.4);
    CGFloat scale=fmin(2,self.bounds.size.width/80);
    AGPixelText(self.accessibilityLabel,CGRectGetMidX(rect),(rect.size.height-13*scale)/2,rect.size.width-8,scale,NO);
}
@end
@interface AGClassicPanel:UIView
@property(nonatomic) AGSnapshot snapshot;
@property(nonatomic) BOOL loaded,locked;
@property(nonatomic) int64_t remaining;
@property(nonatomic,copy) NSString *notice;
@end
@implementation AGClassicPanel
- (void)drawRect:(CGRect)rect{
    CGContextRef c=UIGraphicsGetCurrentContext();CGFloat w=rect.size.width,h=rect.size.height,s=w/240.0;
    CGFloat sx=s,sy=h/280.0,cx=w/2;
    void(^box)(CGFloat,CGFloat,CGFloat,CGFloat,UIColor *)=^(CGFloat x,CGFloat y,CGFloat a,CGFloat b,UIColor *color){[color setFill];UIRectFill(CGRectMake(x*sx,y*sy,a*sx,b*sy));};
    UIColor *border=[UIColor colorWithRed:65/255.0 green:102/255.0 blue:128/255.0 alpha:1];
    UIColor *muted=[UIColor colorWithRed:142/255.0 green:173/255.0 blue:197/255.0 alpha:1];
    box(1,1,238,278,AGInk());box(2,2,236,276,[UIColor colorWithRed:.38 green:.53 blue:.7 alpha:1]);box(6,6,228,268,AGPaper());
    for(int i=0;i<4;i++){
        CGFloat x=i%2?225:2,y=i/2?265:2;
        box(x,y,13,13,[UIColor colorWithRed:.65 green:.55 blue:.16 alpha:1]);
        box(x+1,y+1,11,11,[UIColor colorWithRed:1 green:.88 blue:.32 alpha:1]);
        box(x+(i%2?0:5),y+(i/2?0:5),8,8,AGPaper());
    }
    box(12,10,216,27,border);box(13,11,214,25,muted);
    AGPixelText(@"VÒNG XOAY MAY MẮN",cx,12*sy,208*s,s,YES);
    NSString *clock=self.loaded?[NSString stringWithFormat:@"%02lld:%02lld",(long long)(self.remaining/60),(long long)(self.remaining%60)]:@"--:--";
    AGPixelText(clock,cx,53*sy,200*s,s,YES);
    NSString *state=!self.loaded?@"Đang tải dữ liệu":self.snapshot.count<2?@"Chờ người chơi thứ 2":self.locked?@"Đang chờ kết quả":@"Đang đếm ngược";
    if(self.notice.length)state=self.notice;
    AGPixelText(state,cx,78*sy,208*s,s,NO);
    AGPixelText(@"Tỷ lệ thắng",cx,98*sy,208*s,s,NO);
    box(24,111,192,19,border);box(25,112,190,17,muted);
    double percent=self.loaded&&self.snapshot.total>0?fmin(1,fmax(0,(double)self.snapshot.own/self.snapshot.total)):0;
    if(percent>0)box(25,112,190*percent,17,[UIColor colorWithRed:.45 green:.74 blue:.86 alpha:1]);
    NSString *pct=percent>0?[NSString stringWithFormat:@"%.2f%%",percent*100]:@"0%";
    AGPixelText(pct,cx,113*sy,184*s,s,NO);
    AGSnapshot a=self.snapshot;NSArray<NSString *> *lines=self.loaded?@[
      [NSString stringWithFormat:@"Quỹ: %@ xu",AGMoney(a.total)],
      [NSString stringWithFormat:@"Số người tham gia: %d",a.count],
      [NSString stringWithFormat:@"Bạn đã tham gia: %@ xu",AGMoney(a.own)],
      [NSString stringWithFormat:@"Xu của bạn: %@ xu",AGMoney(a.balance)],
      [NSString stringWithFormat:@"Thuế: %d%% - Tối đa 50tr xu",a.tax]]:@[@"Quỹ: ... xu",@"Số người tham gia: ...",@"Bạn đã tham gia: ... xu",@"Xu của bạn: ... xu",@"Thuế: ... - Tối đa 50tr xu"];
    for(int i=0;i<5;i++)AGPixelText(lines[i],cx,(141+i*13)*sy,214*s,s,NO);
    box(18,214,204,.75,muted);
    AGPixelText(@"Người vừa chiến thắng",cx,225*sy,214*s,s,NO);
    AGPixelText(self.loaded&&a.hasResult?AGString(a.winner):@"Chưa có kết quả",cx,238*sy,214*s,s,NO);
    AGPixelText([NSString stringWithFormat:@"Số xu thắng: %@ xu",self.loaded&&a.hasResult?AGMoney(a.resultPrize):@"0"],cx,251*sy,214*s,s,NO);
    AGPixelText([NSString stringWithFormat:@"Số xu tham gia: %@ xu",self.loaded&&a.hasResult?AGMoney(a.resultStake):@"0"],cx,264*sy,214*s,s,NO);
    CGContextSetAlpha(c,1);
}
@end
