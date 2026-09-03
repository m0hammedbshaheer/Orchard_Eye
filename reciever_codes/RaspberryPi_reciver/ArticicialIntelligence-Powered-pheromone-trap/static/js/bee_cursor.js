document.addEventListener('DOMContentLoaded', () => {
    // Create the bee cursor element
    const beeCursor = document.createElement('div');
    beeCursor.id = 'bee-cursor';

    // High-quality SVG Bee Icon (Black and Yellow)
    beeCursor.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: 100%; height: 100%; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">
            <path d="M16.5 10.5C16.5 10.5 19 9.5 20 8C21 6.5 20.5 4.5 19 4C17.5 3.5 15.5 4.5 15 6C14.5 7.5 14 9 14 9" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M7.5 10.5C7.5 10.5 5 9.5 4 8C3 6.5 3.5 4.5 5 4C6.5 3.5 8.5 4.5 9 6C9.5 7.5 10 9 10 9" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
            <ellipse cx="12" cy="14" rx="6" ry="8" fill="#F1C40F" stroke="#333" stroke-width="1.5"/>
            <path d="M12 8L12 10" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M8 12L16 12" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M8 16L16 16" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M9 19L15 19" stroke="#333" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
    `;

    // Style the cursor
    Object.assign(beeCursor.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '40px',
        height: '40px',
        pointerEvents: 'none',
        zIndex: '9999',
        transform: 'translate(-50%, -50%)',
        transition: 'transform 0.1s ease-out', // Smooth catch-up
        willChange: 'transform, left, top'
    });

    document.body.appendChild(beeCursor);

    // Track mouse movement
    let mouseX = 0;
    let mouseY = 0;
    let beeX = 0;
    let beeY = 0;

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    // Smooth animation loop
    function animateBee() {
        // Linear interpolation for smooth following (lag effect)
        // Reduced to 0.05 for a "lazy follow" feel
        beeX += (mouseX - beeX) * 0.05;
        beeY += (mouseY - beeY) * 0.05;

        // Calculate rotation based on movement direction
        const deltaX = mouseX - beeX;
        const rotation = deltaX * 1.5; // Reduced tilt sensitivity

        beeCursor.style.left = `${beeX}px`;
        beeCursor.style.top = `${beeY}px`;
        // Apply tilt and ensure it stays centered
        beeCursor.style.transform = `translate(-50%, -50%) rotate(${Math.min(Math.max(rotation, -45), 45)}deg)`;

        requestAnimationFrame(animateBee);
    }

    animateBee();

    // Optional: Hide default cursor if desired (uncomment to enable)
    // document.body.style.cursor = 'none';
    // const links = document.querySelectorAll('a, button, input, textarea');
    // links.forEach(link => {
    //     link.style.cursor = 'none'; // Or keep pointer
    // });
});
