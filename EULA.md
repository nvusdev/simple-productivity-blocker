# End User License Agreement (EULA)

**Last Updated: May 15, 2026**

Please read this End User License Agreement ("Agreement") carefully before downloading or using Simple Productivity Blocker ("Software"). By downloading or using the Software, you are agreeing to be bound by the terms and conditions of this Agreement.

## 1. Grant of License
Subject to the terms of this Agreement, nvusdev grants you a personal, non-transferable, non-exclusive license to use the Software on your Windows devices in accordance with the MIT License terms.

## 2. System-Level Enforcement
You acknowledge that the Software operates at the Windows operating system level and performs the following actions:
- **DNS Interception:** Modifying network adapter settings to point to a local proxy.
- **Hosts File Modification:** Writing entries to the system `hosts` file.
- **NTFS ACL Management:** Modifying security descriptors on files and folders.
- **Process Termination:** Automatically closing applications and Windows File Explorer windows.
- **Browser Policy Enforcement:** Modifying Registry keys to disable DNS-over-HTTPS (DoH).

## 3. "As-Is" and No Warranty
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED. THE DEVELOPER DOES NOT WARRANT THAT THE SOFTWARE WILL BE UNINTERRUPTED OR ERROR-FREE. YOU ASSUME ALL RISKS ASSOCIATED WITH SYSTEM MODIFICATIONS.

## 4. Limitation of Liability
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. THIS INCLUDES, BUT IS NOT LIMITED TO, DATA LOSS, SYSTEM INSTABILITY, OR LOSS OF ACCESS TO FILES DUE TO FORGOTTEN PASSWORDS OR CONFIGURATION ERRORS.

## 5. Non-Bypass and Restrictions
The Software is designed to eliminate the "willpower gap." You agree not to attempt to reverse engineer, decompile, or bypass the security mechanisms of the Software for the purpose of circumventing your own productivity rules during an active session, except through the provided recovery mechanisms (e.g., `recovery_uplift.exe`).

## 6. Recovery Responsibility
You are responsible for ensuring you have backups of critical data. While SPB includes recovery mechanisms (`recovery_uplift.exe`, `dns_state.json`), the developer is not responsible for any permanent loss of access resulting from improper use or system crashes.

## 7. Governing Law
This Agreement shall be governed by the laws of the jurisdiction in which the developer resides.

## 8. Termination
This Agreement is effective until terminated by you or nvusdev. Your rights under this Agreement will terminate automatically without notice if you fail to comply with any of its terms.
