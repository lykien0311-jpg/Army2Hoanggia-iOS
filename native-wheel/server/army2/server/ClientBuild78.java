package army2.server;

import java.io.IOException;

public final class ClientBuild78 {
    public static final String JAR = "2.4.2-HG130-JAR";
    public static final String APK = "2.4.2-HG130-APK";
    public static final String IPA = "2.4.1-HG78-IPA";
    public static final String IPA_MAPS = "2.4.1-B275-IPA";
    public static final String NOTICE = "Cập nhật bản mới tại army2hoanggia.com";

    private ClientBuild78() {}

    public static boolean legacyIpa(String original, Object current) {
        return original.equals(current) || IPA_MAPS.equals(current);
    }

    public static boolean accepted(String version) {
        return JAR.equals(version) || APK.equals(version) || legacyIpa(IPA, version);
    }

    public static boolean allow(ClientEntry client) throws IOException {
        if (accepted(client.versionARM)) {
            return true;
        }
        client.notice(NOTICE);
        GameGuard61.authenticated(client, client.r61State);
        return false;
    }
}
