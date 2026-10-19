# Changelog

## 2026-10-19 — Course selection ranges

- Interactive course selection accepts inclusive list-number ranges such as `1-6` and mixed selections such as `1-3, 5, 7-9`.
- Spaces around hyphens are accepted. Overlapping ranges and individual selections are deduplicated in selection order.
- Existing individual numbers, IDs, and course codes remain supported. Invalid, reversed, and out-of-bounds ranges prompt for correction.
- Added offline tests for ranges and existing selection formats.

## 2026-10-19 — Password entry and CMS connection fixes

### Fixed

- Windows console password prompts display `*` as you type, with backspace and cancellation support. Previously, hidden input could look as though typing was not working.
- All three password entry paths use the same helper: sign-in, update password, and update both credentials. Leading and trailing password spaces are preserved instead of stripped.
- Replaced external `curl.exe --ntlm` calls with Python `requests` and `requests-ntlm` for page requests and file downloads. This fixes startup failure when the installed curl lacks NTLM support.
- HTTP status codes now come directly from the response, eliminating the blank `Unexpected HTTP .` caused by parsing empty curl output.
- Connection failures, timeouts, certificate failures, missing dependencies, and rejected HTTP responses produce actionable errors. Password values are redacted from transport exception messages.
- Only complete, nonempty HTTP 200 downloads are published. Transfers use a `.part` file that is removed on failure; failed or empty transfers preserve any existing destination file. HTTP error pages are no longer counted as successful downloads merely because a file was written.

### Setup and documentation

- Added `requirements.txt` and installation instructions using `python -m pip`.
- Added a dependency check before credential prompts. The error identifies the actual Python interpreter and gives a PowerShell command, avoiding repeated password prompts for missing packages.
- Documented the multiple-Python issue: packages installed for Python 3.11 are unavailable to a script launched by Python 3.14.
- Removed the curl prerequisite and documented password-change recovery, certificate checks, and redirect handling.
- Added offline regression tests and automated checks for Python 3.11 and 3.14 on Windows and Linux.
- Ignore temporary downloads and local backup files in Git. Credential settings remain local and ignored.

### Compatibility and validation

- Python 3.10+ remains the minimum supported version; Windows Python 3.11 and 3.14 were checked locally.
- HTTPS certificates are now verified instead of using curl's previous `-k` bypass. HTTP redirects are reported without automatically forwarding authentication.
- Existing settings, saved credential format, command-line options, filters, and course organization remain compatible.
- The owner confirmed successful live CMS login after the NTLM library was installed in the interpreter used to launch the script. Automated tests require neither a university account nor network access.
