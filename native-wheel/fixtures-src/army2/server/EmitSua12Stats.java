package army2.server;
import java.nio.file.*;import java.util.*;
/** Compile with the Sua12 ZIP's Probe88 and server test fixtures; no live user. */
public final class EmitSua12Stats {
 public static void main(String[] args)throws Exception{
  Probe88.setup();var u=Probe88.user();List<Object> cases=new ArrayList<>();
  for(boolean modern:new boolean[]{true,false})for(int hero=0;hero<10;hero++)for(int family=0;family<5;family++)for(int count:new int[]{0,1,3,15}){
   Balance494.character(hero).put("enabled",modern);Probe88.gear(u,hero,60,10,count,130+family);
   u.packets.clear();u.sendRuongDoInfo();Map<String,Object> row=new LinkedHashMap<>();
   row.put("hero",hero);row.put("modern",modern);row.put("family",family);row.put("count",count);row.put("points",java.util.stream.IntStream.range(0,5).map(i->u.getPointAdd()[i]).boxed().toList());row.put("nativeBase",Probe88.NATIVE[hero]);row.put("expected",Arrays.stream(Display89.ability(u)).boxed().toList());
   for(var packet:u.packets)if(packet.getCommand()==-110||packet.getCommand()==-124||packet.getCommand()==101)
    row.put(Integer.toString(packet.getCommand()),Base64.getEncoder().encodeToString(packet.getData()));
   cases.add(row);
  }
  Files.writeString(Path.of(args[0]),org.json.simple.JSONValue.toJSONString(cases));
  System.out.println("Exported "+cases.size()+" actual Sua12 config, snapshot and inventory fixtures");System.exit(0);
 }
}
