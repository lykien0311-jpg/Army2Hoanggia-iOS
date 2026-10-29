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
    CGContextRef c=UIGraphicsGetCurrentContext();CGContextSaveGState(c);CGContextSetAlpha(c,self.enabled?1:.4);
    CGFloat scale=fmin(2.7,self.bounds.size.width/320*4.5),textWidth=AGTextWidth(self.accessibilityLabel,NO)*scale;
    CGFloat cx=self.tag==1?8+textWidth/2:self.tag==2?rect.size.width-8-textWidth/2:CGRectGetMidX(rect);
    AGPixelText(self.accessibilityLabel,cx,(rect.size.height-13*scale)/2,rect.size.width-12,scale,NO);
    CGContextRestoreGState(c);
}
@end
static CGFloat AGPanelScale(CGFloat width,CGFloat height){return fmin(width/320.0,fmin(1.8,fmax(.95,height/450.0)));}
static UIColor *AGBorder(void){return [UIColor colorWithRed:65/255.0 green:102/255.0 blue:128/255.0 alpha:1];}
static UIColor *AGMuted(void){return [UIColor colorWithRed:142/255.0 green:173/255.0 blue:197/255.0 alpha:1];}
static void AGFill(CGFloat x,CGFloat y,CGFloat width,CGFloat height,UIColor *color){[color setFill];UIRectFill(CGRectMake(x,y,width,height));}
static void AGFrame(CGFloat width,CGFloat height,CGFloat scale){
    AGFill(0,0,width,height,AGInk());
    AGFill(scale,scale,width-2*scale,height-2*scale,[UIColor colorWithRed:.38 green:.53 blue:.7 alpha:1]);
    AGFill(6*scale,6*scale,width-12*scale,height-12*scale,AGPaper());
    for(int i=0;i<4;i++){
        CGFloat x=i%2?width-10*scale:scale,y=i/2?height-10*scale:scale;
        UIColor *gold=[UIColor colorWithRed:1 green:.88 blue:.32 alpha:1];
        AGFill(x,y,9*scale,9*scale,[UIColor colorWithRed:.65 green:.55 blue:.16 alpha:1]);
        AGFill(x+scale,y+scale,8*scale,8*scale,gold);
        AGFill(x+(i%2?0:4*scale),y+(i/2?0:4*scale),6*scale,6*scale,AGPaper());
    }
}
@interface AGClassicPanel:UIView
@property(nonatomic) AGSnapshot snapshot;
@property(nonatomic) BOOL loaded,locked;
@property(nonatomic) int64_t remaining;
@property(nonatomic,copy) NSString *notice;
@end
@implementation AGClassicPanel
- (void)drawRect:(CGRect)rect{
    CGFloat w=rect.size.width,h=rect.size.height,s=AGPanelScale(w,h),cx=w/2;
    // Video 28835 layout with the user's larger, screen-relative typography.
    // The controller scrolls compact screens instead of shrinking the text.
    CGFloat body=1.5*s,heading=1.3*s;
    AGFrame(w,h,s);
    AGFill(10*s,10*s,w-20*s,32*s,AGBorder());AGFill(11*s,11*s,w-22*s,30*s,AGMuted());
    AGPixelText(@"VÒNG XOAY MAY MẮN",cx,8*s,w-28*s,heading,YES);
    NSString *clock=self.loaded?[NSString stringWithFormat:@"%02lld:%02lld",(long long)(self.remaining/60),(long long)(self.remaining%60)]:@"--:--";
    AGPixelText(clock,cx,54*s,w-28*s,heading,YES);
    NSString *state=!self.loaded?@"Đang tải dữ liệu":self.snapshot.count<2?@"Chờ người chơi thứ 2":self.locked?@"Đang chờ kết quả":@"Đang đếm ngược";
    AGPixelText(state,cx,92*s,w-28*s,body,NO);
    AGPixelText(@"Tỷ lệ thắng",cx,126*s,w-28*s,body,NO);
    AGFill(cx-105*s,151*s,210*s,25*s,AGBorder());AGFill(cx-104*s,152*s,208*s,23*s,AGMuted());
    double percent=self.loaded&&self.snapshot.total>0?fmin(1,fmax(0,(double)self.snapshot.own/self.snapshot.total)):0;
    if(percent>0)AGFill(cx-104*s,152*s,208*s*percent,23*s,[UIColor colorWithRed:1 green:220/255.0 blue:62/255.0 alpha:1]);
    NSString *pct=percent>0?[NSString stringWithFormat:@"%.2f%%",percent*100]:@"0%";
    AGPixelText(pct,cx,153*s,202*s,body,NO);
    AGSnapshot a=self.snapshot;NSArray<NSString *> *lines=self.loaded?@[
      [NSString stringWithFormat:@"Quỹ: %@ xu",AGMoney(a.total)],
      [NSString stringWithFormat:@"Số người tham gia: %d",a.count],
      [NSString stringWithFormat:@"Bạn đã tham gia: %@ xu",AGMoney(a.own)],
      [NSString stringWithFormat:@"Xu của bạn: %@ xu",AGMoney(a.balance)],
      [NSString stringWithFormat:@"Thuế: %d%% - Tối đa 50tr xu",a.tax]]:@[@"Quỹ: ... xu",@"Số người tham gia: ...",@"Bạn đã tham gia: ... xu",@"Xu của bạn: ... xu",@"Thuế: ... - Tối đa 50tr xu"];
    for(int i=0;i<5;i++)AGPixelText(lines[i],cx,(193+i*21)*s,w-28*s,body,NO);
    AGFill(14*s,315*s,w-28*s,.75*s,AGMuted());
    AGPixelText(@"Người vừa chiến thắng",cx,329*s,w-28*s,body,NO);
    AGPixelText(self.loaded&&a.hasResult?AGString(a.winner):@"Chưa có kết quả",cx,350*s,w-28*s,body,NO);
    AGPixelText([NSString stringWithFormat:@"Số xu thắng: %@ xu",self.loaded&&a.hasResult?AGMoney(a.resultPrize):@"0"],cx,371*s,w-28*s,body,NO);
    AGPixelText([NSString stringWithFormat:@"Số xu tham gia: %@ xu",self.loaded&&a.hasResult?AGMoney(a.resultStake):@"0"],cx,392*s,w-28*s,body,NO);
    if(self.notice.length)AGPixelText(self.notice,cx,h-24*s,w-28*s,body,NO);
}
@end

@interface AGAmountPanel:UIView
@property(nonatomic) CGFloat layoutScale;
@end
@implementation AGAmountPanel
- (void)drawRect:(CGRect)rect{
    CGFloat s=self.layoutScale;AGFrame(rect.size.width,rect.size.height,s);
    if(rect.size.height>=66)AGPixelText(@"Nhập xu: 1.000.000 - 50.000.000",rect.size.width/2,8*s,rect.size.width-24*s,1.25*s,NO);
}
@end

