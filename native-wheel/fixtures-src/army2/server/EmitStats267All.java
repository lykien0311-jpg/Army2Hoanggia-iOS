package army2.server;
import java.nio.file.*;import java.util.*;
/** 0/1/3/15/21 gems, all five families, ten characters and both balance modes. */
public final class EmitStats267All {
 public static void main(String[] args)throws Exception{
  Probe88.setup();var u=Probe88.user();List<Object> rows=new ArrayList<>();
  for(boolean modern:new boolean[]{true,false})for(int hero=0;hero<10;hero++)for(int family=0;family<5;family++)for(int count:new int[]{0,1,3,15,21}){
   Balance494.character(hero).put("enabled",modern);Probe88.gear(u,hero,0,10,0,130+family);
   int remaining=count,stat=new int[]{4,0,2,3,1}[family];
   for(var g:Items67.bag(u)){
    int n=Math.min(5,remaining);remaining-=n;g.slot=new int[n];Arrays.fill(g.slot,130+family);g.slotNull=0;
    g.invAdd[stat]+=(short)(21*n);g.percenAdd[stat]+=(short)(2*n);
   }
   if(remaining!=0)throw new AssertionError("gem distribution");
   Map<String,Object> row=new LinkedHashMap<>();row.put("hero",hero);row.put("modern",modern);row.put("family",family);row.put("count",count);
   row.put("points",java.util.stream.IntStream.range(0,5).map(i->u.getPointAdd()[i]).boxed().toList());row.put("nativeBase",Probe88.NATIVE[hero]);
   long[] expected=Display89.ability(u),jar=Probe88.ui(u);if(!Arrays.equals(expected,jar))throw new AssertionError("server/JAR oracle "+hero+" "+family+" "+count);
   row.put("expected",Arrays.stream(expected).boxed().toList());row.put("jar_expected",Arrays.stream(jar).boxed().toList());
   u.packets.clear();u.sendRuongDoInfo();
   for(var p:u.packets)if(p.getCommand()==-110||p.getCommand()==-124||p.getCommand()==101)row.put(Integer.toString(p.getCommand()),Base64.getEncoder().encodeToString(p.getData()));
   rows.add(row);
  }
  Files.writeString(Path.of(args[0]),org.json.simple.JSONValue.toJSONString(rows));System.out.println("PASS "+rows.size()+" server/JAR fixtures including 21 gems");System.exit(0);
 }
}
