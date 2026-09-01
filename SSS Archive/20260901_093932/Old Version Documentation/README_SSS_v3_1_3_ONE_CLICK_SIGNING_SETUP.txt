SSS v3.1.3 — One-Click Development Signing Setup
==================================================

This hotfix addresses repeated:

  [FIX] Signing configuration was not found:
  C:\Church\SermonAI\sss_signing_config.json

Run:

  Setup-SSS-Development-Signing.bat

Type:

  TEST

The helper will automatically:

  1. Find an existing "Sunday Service System Development" certificate, or
     create one if needed.

  2. Ensure its PUBLIC certificate is trusted under:
       CurrentUser\TrustedPeople

  3. Find Microsoft SignTool.

  4. Write:
       C:\Church\SermonAI\sss_signing_config.json

  5. Run the existing SSS signing checker when available.

No private key is exported.

If SignTool is missing, the helper stops and tells you that Windows SDK
Signing Tools must be installed.

After the helper reports READY, run:

  Build-SSS-Windows-Installer.bat

This development certificate is for LOCAL TESTING ONLY. Replace it with a
production code-signing certificate before public distribution.
