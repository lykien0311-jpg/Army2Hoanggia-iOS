package army2.server;
import java.io.*;
import java.net.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.concurrent.*;
import network.Message;

/** Native login parsing and rejection notices over a real loopback connection; no database needed. */
public final class ClientBuildProbe78 {
 static int checks;static void ok(boolean b,String s){checks++;if(!b)throw new AssertionError(s);}
 static Message login(String version,String user,String pass)throws Exception {
  var b=new ByteArrayOutputStream();var o=new DataOutputStream(b);o.writeUTF(user);o.writeUTF(pass);o.writeUTF(version);o.writeUTF("z1");return new Message((byte)1,b.toByteArray());
 }
 @SuppressWarnings("unchecked") static BlockingQueue<Message> queue(ClientEntry c)throws Exception{var f=ClientEntry.class.getDeclaredField("outgoing");f.setAccessible(true);return (BlockingQueue<Message>)f.get(c);}
 public static void main(String[] args)throws Exception {
  ServerManager.clients=new ArrayList<>();ServerManager.listWait=new ArrayList<>();
  try(var listener=new ServerSocket(0,1,InetAddress.getLoopbackAddress());var peer=new Socket(InetAddress.getLoopbackAddress(),listener.getLocalPort());var socket=listener.accept()){
   ClientEntry c=new ClientEntry(socket,78001);var pending=queue(c);BangXHManager.isComplete=true;
   for(String version:List.of("","2.4.0","2.4.1","2.4.5","2.2.3","9.9.9","2.4.1-HG77-JAR","2.4.0-HG78-IPA","2.4.1-HG77-IPA","2.4.1-HG78-IPA-extra","2.4.1-HG78-JAR-extra","2.4.1-HG78-APK-extra","2.4.1-hg78-jar")){
    pending.clear();c.loginMessage(login(version,"?",""));
    ok(!c.login&&c.user==null,"old/relabelled client never enters an account: "+version);
    Message message=pending.poll();ok(message!=null&&message.getCommand()==4,"native alert packet for "+version);
    ok(new DataInputStream(new ByteArrayInputStream(message.getData())).readUTF().equals(ClientBuild78.NOTICE),"exact update message precedes credential/database checks");
   }
   BangXHManager.isComplete=false;
   for(String version:List.of(ClientBuild78.JAR,ClientBuild78.APK,ClientBuild78.IPA)){
    pending.clear();c.loginMessage(login(version,"probeuser","pass1234"));Message m=pending.poll();
    ok(m!=null&&new DataInputStream(new ByteArrayInputStream(m.getData())).readUTF().contains("Server đang tải dữ liệu"),"new build reaches the original login path: "+version);
    ok(!c.login&&c.user==null,"original loading response does not invent an authenticated account");
    pending.clear();c.loginMessage(login(version,"?",""));m=pending.poll();ok(m!=null&&!new DataInputStream(new ByteArrayInputStream(m.getData())).readUTF().equals(ClientBuild78.NOTICE),"new build still undergoes native credential validation");
   }
   ok(!ClientBuild78.accepted(null),"missing marker is rejected");
   if(args.length==1){
    try(var files=java.nio.file.Files.list(java.nio.file.Path.of(args[0]))){
     var packets=files.filter(p->p.toString().endsWith(".bin")).sorted().toList();ok(packets.size()==12,"six native IPA variants, two credential samples");
     for(var path:packets){
      byte[] bytes=java.nio.file.Files.readAllBytes(path);var fields=new DataInputStream(new ByteArrayInputStream(bytes));
      String nativeUser=fields.readUTF();fields.readUTF();ok(fields.readUTF().equals(ClientBuild78.IPA)&&fields.readUTF().equals("z1")&&fields.available()==0,"actual native IPA field order");
      pending.clear();c.loginMessage(new Message((byte)1,bytes));Message response=pending.poll();
      ok(response!=null,"native IPA login response");String noticeText=new DataInputStream(new ByteArrayInputStream(response.getData())).readUTF();
      ok(!noticeText.equals(ClientBuild78.NOTICE),"IPA packet passes version gate");
      ok(nativeUser.equals("probeuser")?noticeText.contains("Server đang tải dữ liệu"):!noticeText.contains("Server đang tải dữ liệu"),"original native username validation retained");
     }
    }
   }
   // Write and read the same native alert framing, proving the text is delivered before any EOF.
   pending.clear();c.loginMessage(login("2.4.0","probeuser","pass1234"));Message notice=pending.poll();c.r61SendOriginal(notice);peer.setSoTimeout(2000);var in=new DataInputStream(peer.getInputStream());
   ok(in.readByte()==4,"old client understands native notice opcode");byte[] body=in.readNBytes(in.readUnsignedShort());ok(new DataInputStream(new ByteArrayInputStream(body)).readUTF().equals(ClientBuild78.NOTICE),"full Vietnamese update notice reaches the socket");
  }
  System.out.println("PASS "+checks+" login78 assertions: strict JAR/APK/IPA markers, old/unknown rejection before account access, native notice framing, and unchanged new-build credential/loading validation.");
 }
}
