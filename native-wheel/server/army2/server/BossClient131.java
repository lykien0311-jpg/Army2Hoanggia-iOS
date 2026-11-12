package army2.server;

public final class BossClient131 {
    public static boolean supported(String version) {
        return ClientBuild78.JAR.equals(version) || ClientBuild78.APK.equals(version)
            || ClientBuild78.IPA_MAPS.equals(version);
    }
}
