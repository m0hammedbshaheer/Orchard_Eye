document.addEventListener('DOMContentLoaded', () => {
    const parallaxElements = document.querySelectorAll('.parallax-float');

    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY;

        parallaxElements.forEach((el) => {
            const speed = el.getAttribute('data-speed');
            const direction = el.getAttribute('data-direction') === 'up' ? -1 : 1;
            const yPos = scrolled * speed * direction;

            // Apply translation
            el.style.transform = `translateY(${yPos}px)`;
        });
    });
});
