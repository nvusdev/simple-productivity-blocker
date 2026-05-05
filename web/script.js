document.addEventListener('DOMContentLoaded', () => {
    // Dynamic Tagline
    const taglineElement = document.getElementById('dynamic-tagline');
    const phrases = [
        "students",
        "deep work",
        "focused professionals",
        "neurodivergent minds",
        "the office",
        "those who want to lock in",
        "digital minimalists"
    ];
    
    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    let typeSpeed = 100;

    function type() {
        const currentPhrase = phrases[phraseIndex];
        
        if (isDeleting) {
            taglineElement.textContent = currentPhrase.substring(0, charIndex - 1);
            charIndex--;
            typeSpeed = 50;
        } else {
            taglineElement.textContent = currentPhrase.substring(0, charIndex + 1);
            charIndex++;
            typeSpeed = 100;
        }

        if (!isDeleting && charIndex === currentPhrase.length) {
            isDeleting = true;
            typeSpeed = 2000; // Pause at end
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            phraseIndex = (phraseIndex + 1) % phrases.length;
            typeSpeed = 500;
        }

        setTimeout(type, typeSpeed);
    }

    type();

    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const themeIcon = document.getElementById('theme-icon');

    const updateIcon = (theme) => {
        if (theme === 'dark') {
            themeIcon.innerHTML = `
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            `;
        } else {
            themeIcon.innerHTML = `
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            `;
        }
    };

    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    body.setAttribute('data-theme', savedTheme);
    updateIcon(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = body.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        body.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateIcon(newTheme);
    });

    // GitHub Release Link (Simulated logic to find latest assets)
    const GITHUB_REPO = 'nvusdev/simple-productivity-blocker';
    const GITHUB_API = `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`;

    const downloadWin = document.getElementById('download-win');
    const downloadLinux = document.getElementById('download-linux');

    fetch(GITHUB_API)
        .then(response => response.json())
        .then(data => {
            const assets = data.assets;
            
            // Look for Windows asset (SimpleProductivityBlocker-vX.X.X.zip)
            const winAsset = assets.find(a => a.name.includes('Windows') || a.name.includes('.exe') || a.name.includes('win'));
            if (winAsset) downloadWin.href = winAsset.browser_download_url;
            else downloadWin.href = `https://github.com/${GITHUB_REPO}/releases/latest`;

            // Look for Linux asset
            const linuxAsset = assets.find(a => a.name.includes('Linux') || a.name.includes('.sh') || a.name.includes('linux'));
            if (linuxAsset) downloadLinux.href = linuxAsset.browser_download_url;
            else downloadLinux.href = `https://github.com/${GITHUB_REPO}/releases/latest`;
        })
        .catch(err => {
            console.error("Failed to fetch latest release:", err);
            const latestUrl = `https://github.com/${GITHUB_REPO}/releases/latest`;
            downloadWin.href = latestUrl;
            downloadLinux.href = latestUrl;
        });
});
