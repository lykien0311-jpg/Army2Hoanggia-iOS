package army2.server;

import java.io.IOException;

/** Login admission for the new release; checked before any account lookup or takeover. */
public final class ClientBuild78 {
    public static final String JAR = "2.4.1-HG78-JAR";
    public static final String APK = "2.4.1-HG78-APK";
    public static final String IPA = "2.4.1-HG78-IPA";
    public static final String NOTICE = "Cập nhật bản mới tại army2hoanggia.com";
    private ClientBuild78() {}
    public static boolean accepted(String version) {
        return JAR.equals(version) || APK.equals(version) || IPA.equals(version);
    }
    public static boolean allow(ClientEntry client) throws IOException {
        if (accepted(client.versionARM)) return true;
        client.notice(NOTICE);
        // Match the native login rejection lifecycle, leaving the notice queued for delivery.
        GameGuard61.authenticated(client, client.r61State);
        return false;
    }
}
