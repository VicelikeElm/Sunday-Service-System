SSS v3.1.5 — Development Authenticode Trust Hotfix
====================================================

The v3.1.4 build successfully called SignTool and then failed during the
post-sign Windows trust check:

  Status: UnknownError
  Signer: <the exact configured SSS Development certificate thumbprint>

That means the signature was present and the expected signer certificate was
found, but Windows did not report the self-signed DEVELOPMENT certificate as a
fully public-trust-chain Valid signature.

v3.1.5 adds two protections:

1. DEVELOPMENT PUBLISHER TRUST
   The public SSS Development certificate is placed in:
     CurrentUser\TrustedPeople
     CurrentUser\TrustedPublisher

   It is deliberately NOT inserted into Trusted Root.

2. PINNED DEVELOPMENT-CERT COMPATIBILITY
   sss_signing.py may accept PowerShell Status=UnknownError ONLY when ALL of
   these are true:
     - signer thumbprint matches a trusted signer pin compiled into SSS
     - subject is exactly CN=Sunday Service System Development
     - StatusMessage says the only problem is inability to chain to a trusted
       root / untrusted self-signed root

   It does NOT accept:
     HashMismatch
     NotSigned
     wrong signer
     wrong subject
     generic UnknownError
     file/read errors
     invalid signature data

   Production/public certificates still require normal Valid trust.

FASTEST FIX:
  1. Copy this patch into C:\Church\SermonAI
  2. Run Repair-SSS-Development-Certificate-Trust.bat
  3. Run Build-SSS-Windows-Installer.bat

If it still fails, v3.1.5 now prints the full Authenticode StatusMessage so the
next failure identifies the exact Windows trust error.

Optional diagnostic:
  Check-SSS-Built-EXE-Signature.bat
