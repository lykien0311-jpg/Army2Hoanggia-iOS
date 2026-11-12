import java.nio.file.Files;
import java.nio.file.Path;
import jdk.internal.org.objectweb.asm.ClassReader;
import jdk.internal.org.objectweb.asm.ClassVisitor;
import jdk.internal.org.objectweb.asm.ClassWriter;
import jdk.internal.org.objectweb.asm.MethodVisitor;
import jdk.internal.org.objectweb.asm.Opcodes;

final class CarryIpaCompatibility {
    public static void main(String[] args) throws Exception {
        Path file = Path.of(args[0]);
        ClassReader reader = new ClassReader(Files.readAllBytes(file));
        ClassWriter writer = new ClassWriter(reader, 0);
        int[] changes = {0};
        reader.accept(new ClassVisitor(Opcodes.ASM8, writer) {
            @Override
            public MethodVisitor visitMethod(int access, String name, String desc,
                    String signature, String[] exceptions) {
                MethodVisitor parent = super.visitMethod(access, name, desc, signature, exceptions);
                return new MethodVisitor(Opcodes.ASM8, parent) {
                    private boolean ios;

                    @Override
                    public void visitLdcInsn(Object value) {
                        ios = "2.4.1-HG78-IPA".equals(value);
                        super.visitLdcInsn(value);
                    }

                    @Override
                    public void visitMethodInsn(int opcode, String owner, String method,
                            String descriptor, boolean itf) {
                        if (ios && opcode == Opcodes.INVOKEVIRTUAL && owner.equals("java/lang/String")
                                && method.equals("equals") && descriptor.equals("(Ljava/lang/Object;)Z")) {
                            super.visitMethodInsn(Opcodes.INVOKESTATIC, "army2/server/ClientBuild78",
                                "legacyIpa", "(Ljava/lang/String;Ljava/lang/Object;)Z", false);
                            ++changes[0];
                        } else {
                            super.visitMethodInsn(opcode, owner, method, descriptor, itf);
                        }
                        ios = false;
                    }
                };
            }
        }, 0);
        if (changes[0] != 1) {
            throw new IllegalStateException("Unexpected legacy iOS checks in " + file);
        }
        Files.write(file, writer.toByteArray());
    }
}
