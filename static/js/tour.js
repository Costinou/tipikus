/**
 * Tipikus Onboarding Tour
 * Interactive tour for first-time users
 */

class TipikusTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.isActive = false;
        this.tourType = 'default'; // 'default' or 'lesson'
    }

    // Initialize the tour
    init(steps, tourType = 'default') {
        this.steps = steps;
        this.tourType = tourType;
        this.createOverlay();
        this.createTooltip();
    }

    // Create overlay backdrop
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 10000;
            display: none;
            transition: opacity 0.3s ease;
        `;
        document.body.appendChild(this.overlay);
    }

    // Create tooltip element
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        this.tooltip.style.cssText = `
            position: fixed;
            background: white;
            color: #14213d;
            padding: 1.2rem;
            border-radius: 10px;
            max-width: 320px;
            width: 90%;
            z-index: 10001;
            display: none;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        `;
        document.body.appendChild(this.tooltip);
    }

    // Check if device is mobile
    isMobile() {
        return window.innerWidth <= 768;
    }

    // Start the tour
    start() {
        if (this.steps.length === 0) return;

        this.isActive = true;
        this.currentStep = 0;

        // Show overlay and tooltip
        this.overlay.style.display = 'block';
        this.overlay.style.opacity = '0';
        this.tooltip.style.display = 'block';
        this.tooltip.style.opacity = '1';

        // Fade in overlay
        setTimeout(() => {
            this.overlay.style.opacity = '1';
        }, 10);

        // Show first step with delay to ensure rendering
        setTimeout(() => {
            this.showStep(0);
        }, 100);
    }

    // Show a specific step
    async showStep(index) {
        if (index < 0 || index >= this.steps.length) return;

        const step = this.steps[index];
        this.currentStep = index;

        // Remove previous highlights first
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
            el.style.zIndex = '';
        });

        // Ensure tooltip is visible
        this.tooltip.style.display = 'block';

        // Highlight target element and wait for scroll
        if (step.element) {
            await this.highlightElement(step.element);
        }

        // Position and populate tooltip (with slight delay for render)
        setTimeout(() => {
            this.updateTooltip(step);
        }, 50);
    }

    // Highlight an element
    highlightElement(selector) {
        // Remove previous highlights
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });

        const element = document.querySelector(selector);
        if (element) {
            element.classList.add('tour-highlight');
            element.style.position = 'relative';
            element.style.zIndex = '9999';

            // Scroll into view
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Wait for scroll animation to complete
            return new Promise(resolve => setTimeout(resolve, 300));
        }
        return Promise.resolve();
    }

    // Update tooltip content and position
    updateTooltip(step) {
        const isLast = this.currentStep === this.steps.length - 1;
        const isFirst = this.currentStep === 0;

        this.tooltip.innerHTML = `
            <div>
                <div style="font-size: 1.2rem; margin-bottom: 0.4rem;">${step.icon || '👋'}</div>
                <h3 style="margin: 0 0 0.4rem 0; color: #14213d; font-size: 1rem;">
                    ${step.title}
                </h3>
                <p style="margin: 0 0 0.8rem 0; color: #5a6c7d; line-height: 1.4; font-size: 0.875rem;">
                    ${step.description}
                </p>
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.4rem;">
                    <div style="font-size: 0.75rem; color: #5a6c7d;">
                        ${this.currentStep + 1} / ${this.steps.length}
                    </div>
                    <div style="display: flex; gap: 0.4rem;">
                        ${!isFirst ? `
                            <button onclick="tour.previous()" class="tour-btn tour-btn-secondary">
                                ← Back
                            </button>
                        ` : ''}
                        ${!isLast ? `
                            <button onclick="tour.next()" class="tour-btn tour-btn-primary">
                                Next →
                            </button>
                        ` : `
                            <button onclick="tour.finish()" class="tour-btn tour-btn-primary">
                                ✓ Got it!
                            </button>
                        `}
                    </div>
                </div>
                <button onclick="tour.skip()" style="
                    position: absolute;
                    top: 0.4rem;
                    right: 0.4rem;
                    background: none;
                    border: none;
                    font-size: 1.2rem;
                    cursor: pointer;
                    color: #5a6c7d;
                    padding: 0.2rem;
                    line-height: 1;
                " title="Skip tour">×</button>
            </div>
        `;

        // Position tooltip
        this.positionTooltip(step.element, step.position || 'bottom');
    }

    // Position tooltip relative to target element
    positionTooltip(selector, position) {
        // Helper function to center tooltip
        const centerTooltip = () => {
            this.tooltip.style.position = 'fixed';
            this.tooltip.style.top = '50%';
            this.tooltip.style.left = '50%';
            this.tooltip.style.transform = 'translate(-50%, -50%)';
            this.tooltip.style.maxWidth = '90%';
        };

        // Always center on mobile or when no selector
        if (this.isMobile() || !selector) {
            centerTooltip();
            return;
        }

        const element = document.querySelector(selector);
        if (!element) {
            centerTooltip();
            return;
        }

        // Try to position relative to element
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;

        // Check if element is visible on screen
        if (rect.bottom < 0 || rect.top > viewportHeight ||
            rect.right < 0 || rect.left > viewportWidth) {
            // Element not in viewport, center tooltip
            centerTooltip();
            return;
        }

        let top, left;

        switch (position) {
            case 'top':
                top = rect.top - tooltipRect.height - 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - 20;
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + 20;
                break;
            default:
                top = rect.bottom + 20;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        }

        // Constrain to viewport
        left = Math.max(10, Math.min(left, viewportWidth - tooltipRect.width - 10));
        top = Math.max(10, Math.min(top, viewportHeight - tooltipRect.height - 10));

        // Check if constrained position is still reasonable
        // If tooltip would be too far from element or off-screen, just center it
        if (Math.abs(top - (rect.top + rect.height / 2)) > viewportHeight / 2 ||
            Math.abs(left - (rect.left + rect.width / 2)) > viewportWidth / 2) {
            centerTooltip();
            return;
        }

        // Apply position
        this.tooltip.style.position = 'fixed';
        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
        this.tooltip.style.transform = 'none';
        this.tooltip.style.maxWidth = '320px';
    }

    // Navigate to next step
    next() {
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        }
    }

    // Navigate to previous step
    previous() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    // Skip tour
    skip() {
        if (confirm('Are you sure you want to skip the tour? You can restart it later from the help menu.')) {
            this.finish();
        }
    }


    // Finish tour
    finish() {
        this.isActive = false;
        this.overlay.style.opacity = '0';
        this.tooltip.style.display = 'none';

        setTimeout(() => {
            this.overlay.style.display = 'none';
        }, 300);

        // Remove highlights
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
            el.style.zIndex = '';
        });

        // Mark tour as completed (call appropriate endpoint based on tour type)
        const endpoint = this.tourType === 'lesson' ? '/api/lesson-tour-completed' : '/api/tour-completed';
        fetch(endpoint, { method: 'POST' })
            .catch(err => console.error('Failed to mark tour as completed:', err));
    }
}

// Global tour instance
const tour = new TipikusTour();

// Home page tour steps
const homeTourSteps = [
    {
        icon: '👋',
        title: 'Welcome to Tipikus!',
        description: 'Let\'s take a quick tour to help you get started with learning Hungarian. This will only take a minute!',
        element: null,
        position: 'center'
    },
    {
        icon: '🎯',
        title: 'Choose Your Level',
        description: 'These are the different learning levels (A1, A2, B1, B2, C1, C2). Start with the level that matches your current knowledge!',
        element: '.niveaux-grid',
        position: 'bottom'
    },
    {
        icon: '🔒',
        title: 'Unlock System',
        description: 'Levels are unlocked progressively. Complete 80% of a level\'s XP to unlock the next one! This keeps your learning structured and motivated.',
        element: '.niveau-card.locked',
        position: 'top'
    },
    {
        icon: '⭐',
        title: 'XP Progress',
        description: 'Track your progress with XP (experience points). Every activity earns you points - flashcards (10 XP), quizzes (20 XP), and exercises (25 XP)!',
        element: '.progress-container',
        position: 'bottom'
    }
];

// Lesson page tour steps
const lessonTourSteps = [
    {
        icon: '👋',
        title: 'Welcome to Your First Lesson!',
        description: 'Let\'s quickly explore how lessons work. This will help you learn more effectively!',
        element: null,
        position: 'center'
    },
    {
        icon: '📖',
        title: 'Lesson Content',
        description: 'This is the main lesson content with theory, explanations, and examples. Read it carefully before practicing!',
        element: '#markdown-content',
        position: 'top'
    },
    {
        icon: '📚',
        title: 'Flashcard Decks',
        description: 'After reading the theory, practice with flashcards! Click "📚" to see all words, or "🎯 Quiz" to test yourself.',
        element: '.lesson-decks-section',
        position: 'bottom'
    },
    {
        icon: '✍️',
        title: 'Practice Exercises',
        description: 'Test your knowledge with exercises! These help you apply what you\'ve learned in real sentences.',
        element: '.lesson-exercices-section',
        position: 'bottom'
    }
];

// Initialize tour on home page
if (window.location.pathname === '/' || window.location.pathname === '/index') {
    const initHomeTour = () => {
        // Check if user is new (will be set by backend)
        if (window.showTour === true) {
            tour.init(homeTourSteps, 'default');
            setTimeout(() => tour.start(), 500);
        }
    };

    // Check if DOM is already loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHomeTour);
    } else {
        // DOM is already loaded, run immediately
        initHomeTour();
    }
}

// Initialize tour on lesson page
if (window.location.pathname.startsWith('/lesson/')) {
    const initLessonTour = () => {
        // Check if user should see lesson tour (will be set by backend)
        if (window.showLessonTour === true) {
            tour.init(lessonTourSteps, 'lesson');
            setTimeout(() => tour.start(), 500);
        }
    };

    // Check if DOM is already loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLessonTour);
    } else {
        // DOM is already loaded, run immediately
        initLessonTour();
    }
}
