# Privacy Policy for Simple Productivity Blocker (SPB)

**Last Updated: May 15, 2026**

Simple Productivity Blocker ("SPB", "we", "us", or "our") is committed to protecting your privacy. This Privacy Policy explains how we handle your data.

## 1. Local-First Architecture
SPB is designed with a **privacy-first, local-only architecture**. 
- **No Data Collection:** We do not collect, store, or transmit any of your personal data, browsing history, application usage, or blocking configurations to external servers.
- **Local Storage:** All configuration files (e.g., `config.json`), blocklists, schedules, and logs are stored exclusively on your local device (typically in `%ProgramData%\SimpleProductivityBlocker`).
- **No Accounts:** No user accounts or registrations are required to use the software.

## 2. Network Interception
To provide website blocking functionality, SPB intercepts DNS requests on your local machine using a local DNS proxy or by modifying the system `hosts` file.
- **Local Processing:** All filtering decisions are made locally on your device.
- **Upstream DNS:** When a request is not blocked, it is forwarded to your system's configured DNS providers (e.g., Google DNS, Cloudflare) or your ISP's DNS. We do not control or monitor these upstream requests.

## 3. System Permissions
SPB requires Administrative privileges to perform its core functions:
- Modifying system-level network settings (DNS).
- Managing Windows Scheduled Tasks (for persistence).
- Modifying NTFS Access Control Lists (ACLs) to protect files and folders.
- Terminating unauthorized processes.

These permissions are used **strictly** for the purpose of enforcing your productivity rules.

## 4. Third-Party Services
If you use the "Custom List" feature to download external adblocker or filter lists:
- **Direct Downloads:** SPB downloads these lists directly from the URLs you provide.
- **SSRF Protection:** We implement security checks to ensure these downloads do not access your local network.
- **Provider Privacy:** The providers of these external lists may be able to see your IP address when you download their lists, subject to their own privacy policies.

## 5. Changes to This Policy
We may update this Privacy Policy from time to time to reflect changes in our practices. Any updates will be included in the project repository and distribution package.

## 6. Contact
Since SPB is a local-only tool, there is no centralized data to manage. For questions regarding the software's behavior, please refer to the documentation or the GitHub repository at [https://github.com/nvusdev/simple-productivity-blocker](https://github.com/nvusdev/simple-productivity-blocker).
