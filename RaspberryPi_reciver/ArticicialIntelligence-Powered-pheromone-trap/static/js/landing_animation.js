const bgCanvas = document.getElementById('bgCanvas');
const bgCtx = bgCanvas.getContext('2d');
bgCanvas.width = window.innerWidth;
bgCanvas.height = window.innerHeight;

const fgCanvas = document.getElementById('fgCanvas');
const fgCtx = fgCanvas.getContext('2d');
fgCanvas.width = window.innerWidth;
fgCanvas.height = window.innerHeight;

let particlesArray;
let insectsArray;

// Mouse position
const mouse = {
    x: null,
    y: null,
    radius: (bgCanvas.height / 80) * (bgCanvas.width / 80)
}

window.addEventListener('mousemove', function (event) {
    mouse.x = event.x;
    mouse.y = event.y;
});

// --- PARTICLE CLASS (Background Network) ---
class Particle {
    constructor(x, y, directionX, directionY, size, color) {
        this.x = x;
        this.y = y;
        this.directionX = directionX;
        this.directionY = directionY;
        this.size = size;
        this.color = color;
        this.speed = Math.random() * 0.5 + 0.2;
    }

    draw() {
        bgCtx.beginPath();
        bgCtx.arc(this.x, this.y, this.size, 0, Math.PI * 2, false);
        bgCtx.fillStyle = this.color; // Opacity handled in color string
        bgCtx.fill();
    }

    update() {
        if (this.x > bgCanvas.width || this.x < 0) {
            this.directionX = -this.directionX;
        }
        if (this.y > bgCanvas.height || this.y < 0) {
            this.directionY = -this.directionY;
        }

        // Mouse collision/interaction
        let dx = mouse.x - this.x;
        let dy = mouse.y - this.y;
        let distance = Math.sqrt(dx * dx + dy * dy);
        if (distance < mouse.radius + this.size) {
            if (mouse.x < this.x && this.x < bgCanvas.width - this.size * 10) {
                this.x += 3;
            }
            if (mouse.x > this.x && this.x > this.size * 10) {
                this.x -= 3;
            }
            if (mouse.y < this.y && this.y < bgCanvas.height - this.size * 10) {
                this.y += 3;
            }
            if (mouse.y > this.y && this.y > this.size * 10) {
                this.y -= 3;
            }
        }

        this.x += this.directionX * this.speed;
        this.y += this.directionY * this.speed;
        this.draw();
    }
}

// --- INSECT CLASS (Foreground Ladybugs 🐞) ---
class Insect {
    constructor(x, y, size) {
        this.x = x;
        this.y = y;
        this.size = size;
        this.type = '🐞';
        this.angle = Math.random() * Math.PI * 2;
        this.speed = Math.random() * 0.2 + 0.1;
        this.spin = (Math.random() - 0.5) * 0.02;
    }

    draw() {
        fgCtx.save();
        fgCtx.translate(this.x, this.y);
        fgCtx.rotate(this.angle + Math.PI / 2);
        fgCtx.font = `${this.size * 14}px Arial`;
        fgCtx.globalAlpha = 1.0; // Fully opaque
        fgCtx.fillText(this.type, 0, 0);
        fgCtx.restore();
    }

    update() {
        this.angle += this.spin;
        if (Math.random() < 0.05) this.spin = (Math.random() - 0.5) * 0.05;

        this.x += Math.cos(this.angle) * this.speed;
        this.y += Math.sin(this.angle) * this.speed;

        // Wrap around screen
        if (this.x < -30) this.x = fgCanvas.width + 30;
        if (this.x > fgCanvas.width + 30) this.x = -30;
        if (this.y < -30) this.y = fgCanvas.height + 30;
        if (this.y > fgCanvas.height + 30) this.y = -30;

        this.draw();
    }
}

function init() {
    particlesArray = [];
    insectsArray = [];

    // 1. PARTICLES (Background)
    let numberOfParticles = (bgCanvas.height * bgCanvas.width) / 25000;
    for (let i = 0; i < numberOfParticles; i++) {
        let size = (Math.random() * 2) + 1;
        let x = Math.random() * (innerWidth - size * 2) + size * 2;
        let y = Math.random() * (innerHeight - size * 2) + size * 2;
        let directionX = (Math.random() * 2) - 1;
        let directionY = (Math.random() * 2) - 1;

        // 70% transparent relative to original. Original was ~1.0 opacity. 
        // New opacity = 0.3
        let color = 'rgba(44, 62, 80, 0.3)';

        particlesArray.push(new Particle(x, y, directionX, directionY, size, color));
    }

    // 2. INSECTS (Foreground)
    let numberOfInsects = 4;
    for (let i = 0; i < 2; i++) {
        let size = (Math.random() * 0.5) + 1.2;
        let x = innerWidth / 2 + (Math.random() - 0.5) * 200;
        let y = innerHeight / 2 + (Math.random() - 0.5) * 100;
        insectsArray.push(new Insect(x, y, size));
    }
    for (let i = 0; i < 2; i++) {
        let size = (Math.random() * 0.5) + 1.2;
        let x = Math.random() * innerWidth;
        let y = Math.random() * innerHeight;
        insectsArray.push(new Insect(x, y, size));
    }
}

function connect() {
    let opacityValue = 1;
    for (let a = 0; a < particlesArray.length; a++) {
        for (let b = a; b < particlesArray.length; b++) {
            let distance = ((particlesArray[a].x - particlesArray[b].x) * (particlesArray[a].x - particlesArray[b].x))
                + ((particlesArray[a].y - particlesArray[b].y) * (particlesArray[a].y - particlesArray[b].y));

            if (distance < (bgCanvas.width / 9) * (bgCanvas.height / 9)) {
                // Reduce max line opacity to 0.3 as well
                opacityValue = 0.3 - (distance / 20000);
                if (opacityValue > 0) {
                    bgCtx.strokeStyle = 'rgba(44, 62, 80,' + opacityValue + ')';
                    bgCtx.lineWidth = 1;
                    bgCtx.beginPath();
                    bgCtx.moveTo(particlesArray[a].x, particlesArray[a].y);
                    bgCtx.lineTo(particlesArray[b].x, particlesArray[b].y);
                    bgCtx.stroke();
                }
            }
        }
    }
}

function animate() {
    requestAnimationFrame(animate);

    // Clear both canvases
    bgCtx.clearRect(0, 0, innerWidth, innerHeight);
    fgCtx.clearRect(0, 0, innerWidth, innerHeight);

    // Draw Background Layer
    for (let i = 0; i < particlesArray.length; i++) {
        particlesArray[i].update();
    }
    connect();

    // Draw Foreground Layer
    for (let i = 0; i < insectsArray.length; i++) {
        insectsArray[i].update();
    }
}

window.addEventListener('resize', function () {
    bgCanvas.width = innerWidth;
    bgCanvas.height = innerHeight;
    fgCanvas.width = innerWidth;
    fgCanvas.height = innerHeight;
    init();
});

window.addEventListener('mouseout', function () {
    mouse.x = undefined;
    mouse.y = undefined;
});

init();
animate();
