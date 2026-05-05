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

    // GitHub Release Link
    const GITHUB_REPO = 'nvusdev/simple-productivity-blocker';
    const GITHUB_API = `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`;

    const downloadBtn = document.getElementById('download-btn');

    fetch(GITHUB_API)
        .then(response => response.json())
        .then(data => {
            const assets = data.assets;
            
            // Look for the consolidated zip (SPB_Windows_vX.X.X.zip)
            const zipAsset = assets.find(a => 
                a.name.includes('SPB_Windows') || 
                (a.name.endsWith('.zip') && !a.name.includes('Source'))
            );
            
            if (zipAsset) {
                downloadBtn.href = zipAsset.browser_download_url;
            } else {
                // Fallback to the latest release page if specific asset not found
                downloadBtn.href = `https://github.com/${GITHUB_REPO}/releases/latest`;
            }
        })
        .catch(err => {
            console.error("Failed to fetch latest release:", err);
            downloadBtn.href = `https://github.com/${GITHUB_REPO}/releases/latest`;
        });
});
