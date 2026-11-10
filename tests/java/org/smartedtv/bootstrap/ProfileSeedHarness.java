package org.smartedtv.bootstrap;

import java.io.File;

/** Test-only entry point; production code must use the pinned installFresh(). */
public final class ProfileSeedHarness {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("backup home privateDir sha256");
        boolean installed = ProfileSeed.installFreshChecked(new File(args[0]), new File(args[1]), new File(args[2]), args[3]);
        System.out.println(installed ? "INSTALLED" : "EXISTING_PROFILE_PRESERVED");
    }
}
