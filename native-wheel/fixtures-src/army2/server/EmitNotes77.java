package army2.server;
import java.io.*;import java.nio.file.*;import java.security.SecureRandom;import java.awt.*;import java.awt.image.BufferedImage;import javax.imageio.ImageIO;
/** Offline wire fixtures only. Generated answers are never included in the IPA. */
public final class EmitNotes77 {
 public static void main(String[] args)throws Exception {
  Path root=Path.of(args[0]);Files.createDirectories(root);SecureRandom random=new SecureRandom();
  for(int[] screen:new int[][]{{128,160},{176,208},{240,320},{320,240},{480,640}})for(String mode:new String[]{"sequence","matching","drag","external","jigsaw","rotate"}){
   CaptchaTypes74.Puzzle p;
   if(mode.equals("external")){BufferedImage[] images=new BufferedImage[9];for(int i=0;i<9;i++){images[i]=new BufferedImage(80,80,BufferedImage.TYPE_INT_RGB);Graphics2D g=images[i].createGraphics();g.setColor(Color.getHSBColor(i/9f,.7f,.9f));g.fillRect(0,0,80,80);g.setColor(Color.BLACK);g.drawString("Photo "+i,10,40);g.dispose();}p=new CaptchaTypes74.Puzzle(4,2,new byte[]{1,4},CaptchaRender75.external(screen[0],screen[1],"Chọn 2 ảnh theo câu hỏi thử nghiệm",images,2),null);}
   else p=CaptchaTypes74.generate(mode,screen[0],screen[1],random);
   String name=mode+"-"+screen[0]+"x"+screen[1];Path file=root.resolve(name+".bin");
   try(DataOutputStream out=new DataOutputStream(Files.newOutputStream(file))){out.writeByte(2);out.writeByte(1);out.writeUTF("fixture-"+name);out.writeLong(2000000000000L);out.writeByte(p.type());for(int v:p.frame().geometry())out.writeShort(v);out.writeByte(3);out.writeByte(p.type()==3||p.type()==5||p.type()==6?1:3);out.writeByte(p.required());out.writeByte(0);out.writeInt(p.frame().png().length);out.write(p.frame().png());out.writeBoolean(p.drag()!=null);if(p.drag()!=null){for(int v:p.drag().geometry())out.writeShort(v);out.writeInt(p.drag().png().length);out.write(p.drag().png());}}
   Files.write(root.resolve(name+".answer"),p.answer());Files.write(root.resolve(name+".png"),p.frame().png());if(p.drag()!=null)Files.write(root.resolve(name+"-piece.png"),p.drag().png());
   if(!p.accepts(p.answer()))throw new AssertionError(name);
  }
  System.out.println("PASS 30 Notes77 server-generated packet/image fixtures, 6 modes and 5 logical viewports; offline only.");
 }
}
