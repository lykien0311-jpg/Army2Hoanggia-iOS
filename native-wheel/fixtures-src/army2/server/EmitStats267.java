package army2.server;
import java.nio.file.*;import java.util.*;import java.io.*;
/** Independent server/JAR oracle for the native item identity regression. */
public final class EmitStats267 {
 public static void main(String[] args)throws Exception{
  Probe88.setup();var u=Probe88.user();int hero=0;
  Balance494.character(hero).put("enabled",true);
  var bases=new ArrayList((List)Balance494.character(hero).get("base"));bases.set(1,1035);Balance494.character(hero).put("base",bases);
  Probe88.gear(u,hero,0,10,0,134);
  int remaining=21;
  for(var g:Items67.bag(u)){
   int count=Math.min(5,remaining);remaining-=count;g.slot=new int[count];Arrays.fill(g.slot,134);g.slotNull=0;
   g.invAdd[1]+=(short)(21*count);g.percenAdd[1]+=(short)(2*count);
  }
  if(remaining!=0)throw new AssertionError("gem count");
  ((short[][])Reward65.value(u,"pointAdd"))[hero][1]=165;
  u.packets.clear();u.sendRuongDoInfo();Map<String,Object> row=new LinkedHashMap<>();
  row.put("hero",hero);row.put("points",java.util.stream.IntStream.range(0,5).map(i->u.getPointAdd()[i]).boxed().toList());
  row.put("expected",Arrays.stream(Display89.ability(u)).boxed().toList());
  row.put("jar_expected",Arrays.stream(Probe88.ui(u)).boxed().toList());
  if(Display89.ability(u)[1]!=4585||Probe88.ui(u)[1]!=4585)throw new AssertionError("oracle attack");
  u.packets.clear();u.sendRuongDoInfo();
  for(var packet:u.packets)if(packet.getCommand()==-110||packet.getCommand()==-124||packet.getCommand()==101)
   row.put(Integer.toString(packet.getCommand()),Base64.getEncoder().encodeToString(packet.getData()));
  Files.writeString(Path.of(args[0]),org.json.simple.JSONValue.toJSONString(row));
  System.out.println("PASS server and Sua12 JAR independently return 4585 from 21 attack gems (+42%); synthetic points/base, no combat change");System.exit(0);
 }
}
