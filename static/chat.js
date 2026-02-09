// Chat State Management
let conversationState = {
    step: 'initial', // initial, business_name, business_type, language, template, generating, complete
    userData: null,
    businessName: '',
    businessType: '',
    language: '',
    template: '',
    generatedPosters: [],
    conversationHistory: []
};

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    const userData = sessionStorage.getItem('userData');
    if (!userData) {
        window.location.href = '/login.html';
        return;
    }

    conversationState.userData = JSON.parse(userData);

    // Load conversation history
    const history = sessionStorage.getItem('conversationHistory');
    if (history) {
        conversationState.conversationHistory = JSON.parse(history);
    }

    // Check if demo mode
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('demo') === 'true' && conversationState.userData.isDemo) {
        startDemoFlow();
    } else {
        // Start normal flow
        addBotMessage(`Hi ${conversationState.userData.name}! 👋\n\nI'm BrandBot, your AI marketing assistant powered by Google Gemini.\n\nI can help you create stunning marketing posters in Punjabi, Hindi, or English!\n\nWhat would you like to create today?`);

        setTimeout(() => {
            addQuickReplies([
                { text: '🎉 Festival Poster', value: 'festival_poster' },
                { text: '💰 Sale/Offer Poster', value: 'sale_poster' },
                { text: '📦 Product Launch', value: 'product_poster' },
                { text: '📅 Event Poster', value: 'event_poster' }
            ]);
        }, 500);
    }
});

// Demo Flow
function startDemoFlow() {
    addBotMessage(`Hi ${conversationState.userData.name}! 👋\n\nWelcome to the quick demo!`);

    // Simulate conversational flow
    setTimeout(() => {
        addBotMessage("What would you like to create today?");

        setTimeout(() => {
            // Simulate user clicking Festival Poster
            addUserMessage("🎉 Festival Poster");

            setTimeout(() => {
                addBotMessage("Great choice! 🎨\n\nWhat's your business name?");
                conversationState.businessName = conversationState.userData.businessName;

                setTimeout(() => {
                    // Simulate user typing business name
                    addUserMessage(conversationState.userData.businessName);

                    setTimeout(() => {
                        addBotMessage(`Nice! ${conversationState.userData.businessName} sounds great. 🎯\n\nWhat type of business is it?`);
                        conversationState.businessType = conversationState.userData.businessType;

                        setTimeout(() => {
                            // Simulate user choosing Restaurant
                            addUserMessage("🍽️ Restaurant");

                            setTimeout(() => {
                                addBotMessage("Perfect! Which language should I use for the poster?");
                                conversationState.language = conversationState.userData.language;

                                setTimeout(() => {
                                    // Simulate user choosing Punjabi
                                    addUserMessage("ਪੰਜਾਬੀ Punjabi");

                                    setTimeout(() => {
                                        addBotMessage("Excellent! Now choose your template style:");
                                        conversationState.template = conversationState.userData.template;

                                        setTimeout(() => {
                                            // Simulate user choosing Festival template
                                            addUserMessage("🎉 Festival");

                                            setTimeout(() => {
                                                generatePoster();
                                            }, 1000);
                                        }, 1000);
                                    }, 1000);
                                }, 1500);
                            }, 1000);
                        }, 1500);
                    }, 1000);
                }, 1500);
            }, 1000);
        }, 1000);
    }, 1000);
}

// Add Bot Message
function addBotMessage(text, options = {}) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';

    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${text.replace(/\n/g, '<br>')}
            <div class="message-time">${time}</div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();

    // Save to history
    conversationState.conversationHistory.push({
        type: 'bot',
        text: text,
        time: time
    });
    saveHistory();
}

// Add User Message
function addUserMessage(text) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';

    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-bubble">
            ${text}
            <div class="message-time">${time}</div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();

    // Save to history
    conversationState.conversationHistory.push({
        type: 'user',
        text: text,
        time: time
    });
    saveHistory();
}

// Add Quick Reply Buttons
function addQuickReplies(replies) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';

    let buttonsHTML = '<div class="quick-replies">';
    replies.forEach(reply => {
        buttonsHTML += `<button class="quick-reply-btn" onclick="handleQuickReply('${reply.value}')">${reply.text}</button>`;
    });
    buttonsHTML += '</div>';

    messageDiv.innerHTML = `<div class="message-bubble">${buttonsHTML}</div>`;
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Add Template Cards
function addTemplateCards() {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';

    const templates = [
        { id: 'festival', icon: '🎉', name: 'Festival', desc: 'Centered' },
        { id: 'offer', icon: '💰', name: 'Offer', desc: 'Top-heavy' },
        { id: 'product', icon: '📦', name: 'Product', desc: 'Bottom-third' },
        { id: 'event', icon: '📅', name: 'Event', desc: 'Asymmetric' }
    ];

    let cardsHTML = '<div class="template-cards">';
    templates.forEach(template => {
        cardsHTML += `
            <div class="template-card" onclick="selectTemplate('${template.id}')">
                <div class="icon">${template.icon}</div>
                <div class="name">${template.name}</div>
                <div class="desc">${template.desc}</div>
            </div>
        `;
    });
    cardsHTML += '</div>';

    messageDiv.innerHTML = `<div class="message-bubble">${cardsHTML}</div>`;
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Handle Quick Reply
function handleQuickReply(value) {
    try {
        console.log("Handling Quick Reply:", value); // Debug logging

        // Remove quick reply buttons
        const quickReplies = document.querySelectorAll('.quick-replies');
        quickReplies.forEach(qr => qr.remove());

        if (value.includes('_poster')) {
            const posterType = value.replace('_poster', '');
            // Capitalize first letter for nicer display
            const displayType = posterType.charAt(0).toUpperCase() + posterType.slice(1);
            addUserMessage(`I want to create a ${displayType} poster`);
            conversationState.step = 'business_name';

            setTimeout(() => {
                addBotMessage("Great choice! 🎨\n\nWhat's your business name?");
            }, 500);
        } else if (['retail', 'restaurant', 'services', 'other'].includes(value)) {
            const labels = {
                retail: '🏪 Retail',
                restaurant: '🍽️ Restaurant',
                services: '💼 Services',
                other: '🏭 Other'
            };
            addUserMessage(labels[value] || value);
            conversationState.businessType = value;
            conversationState.step = 'language';

            setTimeout(() => {
                addBotMessage("Perfect! Which language should I use for the poster?");
                setTimeout(() => {
                    addQuickReplies([
                        { text: 'ਪੰਜਾਬੀ Punjabi', value: 'punjabi' },
                        { text: 'हिंदी Hindi', value: 'hindi' },
                        { text: '🌐 English', value: 'english' }
                    ]);
                }, 500);
            }, 500);
        } else if (['punjabi', 'hindi', 'english'].includes(value)) {
            const labels = {
                punjabi: 'ਪੰਜਾਬੀ Punjabi',
                hindi: 'हिंदी Hindi',
                english: '🌐 English'
            };
            addUserMessage(labels[value] || value);
            conversationState.language = value;
            conversationState.step = 'template';

            setTimeout(() => {
                addBotMessage("Excellent! Now choose your template style:");
                setTimeout(() => {
                    addTemplateCards();
                }, 500);
            }, 500);
        } else if (value.startsWith('var_')) {
            // Handle variation selection (if triggered via quick reply mechanism)
            const count = parseInt(value.split('_')[1]);
            addUserMessage(`${count} variations`);

            setTimeout(() => {
                addBotMessage(`Great! Generating ${count} unique variations for you...`);
                generatePoster(count);
            }, 500);
        } else {
            console.warn("Unknown quick reply value:", value);
            addBotMessage("I didn't quite catch that option. Could you try again?");
            // Optionally re-show options based on state
        }
    } catch (error) {
        console.error("Error in handleQuickReply:", error);
        addBotMessage("Sorry, I encountered an error processing your selection. Please try refreshing the page.");
    }
}

// Select Template
function selectTemplate(templateId) {
    // Remove template cards
    const templateCards = document.querySelectorAll('.template-cards');
    templateCards.forEach(tc => tc.remove());

    const templateNames = {
        festival: '🎉 Festival',
        offer: '💰 Offer',
        product: '📦 Product',
        event: '📅 Event'
    };

    addUserMessage(templateNames[templateId]);
    conversationState.template = templateId;
    conversationState.step = 'generating';

    setTimeout(() => {
        generatePoster();
    }, 500);
}

// Generate Poster
async function generatePoster(count = 1) {
    showTypingIndicator();

    addBotMessage("Perfect! Let me create your poster... 🎨");

    showLoadingOverlay("Generating AI content with Gemini...");

    try {
        // Call backend API to generate poster
        const response = await fetch('/api/generate-poster', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                business_name: conversationState.businessName,
                business_type: conversationState.businessType,
                language: conversationState.language,
                template_type: conversationState.template,
                count: count
            })
        });

        if (!response.ok) {
            throw new Error('Generation failed');
        }

        const result = await response.json();

        hideLoadingOverlay();
        hideTypingIndicator();

        if (count === 1) {
            // Single poster
            displayPoster(result.posters[0]);
        } else {
            // Multiple variations
            displayVariations(result.posters);
        }

        conversationState.step = 'complete';
        conversationState.generatedPosters = result.posters;

    } catch (error) {
        console.error('Error:', error);
        hideLoadingOverlay();
        hideTypingIndicator();

        addBotMessage("Oops! Something went wrong. Let me try again with a simpler approach...");

        // Fallback: use template text
        setTimeout(() => {
            generateFallbackPoster();
        }, 1000);
    }
}

// Fallback Poster Generation
async function generateFallbackPoster() {
    showLoadingOverlay("Creating poster with template...");

    try {
        const templateTexts = {
            punjabi: {
                festival: { headline: 'ਵਿਸ਼ੇਸ਼ ਪੇਸ਼ਕਸ਼', subtext: conversationState.businessName, cta: 'ਹੁਣੇ ਆਰਡਰ ਕਰੋ' },
                offer: { headline: '50% ਤੱਕ ਛੋਟ', subtext: conversationState.businessName, cta: 'ਖਰੀਦੋ ਹੁਣ' },
                product: { headline: 'ਨਵਾਂ ਉਤਪਾਦ', subtext: conversationState.businessName, cta: 'ਖਰੀਦੋ' },
                event: { headline: 'ਵਿਸ਼ੇਸ਼ ਸਮਾਗਮ', subtext: conversationState.businessName, cta: 'ਰਜਿਸਟਰ ਕਰੋ' }
            },
            hindi: {
                festival: { headline: 'विशेष ऑफर', subtext: conversationState.businessName, cta: 'अभी ऑर्डर करें' },
                offer: { headline: '50% तक छूट', subtext: conversationState.businessName, cta: 'अभी खरीदें' },
                product: { headline: 'नया उत्पाद', subtext: conversationState.businessName, cta: 'खरीदें' },
                event: { headline: 'विशेष कार्यक्रम', subtext: conversationState.businessName, cta: 'पंजीकरण करें' }
            },
            english: {
                festival: { headline: 'Special Offer', subtext: conversationState.businessName, cta: 'Order Now' },
                offer: { headline: 'Up to 50% Off', subtext: conversationState.businessName, cta: 'Shop Now' },
                product: { headline: 'New Product', subtext: conversationState.businessName, cta: 'Buy Now' },
                event: { headline: 'Special Event', subtext: conversationState.businessName, cta: 'Register' }
            }
        };

        const texts = templateTexts[conversationState.language][conversationState.template];

        // Generate with basic overlay
        const response = await fetch('/api/generate-overlay', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                background_url: 'https://images.unsplash.com/photo-1557683316-973673baf926?w=1080&h=1080&fit=crop',
                texts: [
                    { content: texts.headline, type: 'headline', color: '#FFFFFF', weight: 'black' },
                    { content: texts.subtext, type: 'subtext', color: '#FFD700', weight: 'bold' },
                    { content: texts.cta, type: 'cta', color: '#FFFFFF', weight: 'bold' }
                ],
                language: conversationState.language,
                template_type: conversationState.template,
                brand_color: '#FF6B35',
                output_width: 1080,
                output_height: 1080
            })
        });

        const result = await response.json();

        hideLoadingOverlay();

        displayPoster({
            image_url: result.image_url,
            headline: texts.headline,
            subtext: texts.subtext,
            cta: texts.cta
        });

    } catch (error) {
        console.error('Fallback error:', error);
        hideLoadingOverlay();
        addBotMessage("I'm having trouble generating the poster. Please try again or contact support.");
    }
}

// Display Single Poster
function displayPoster(poster) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';

    const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-bubble" style="max-width: 90%;">
            Here's your poster! 🎉
            
            <div class="image-preview">
                <img src="${poster.image_url}" alt="Generated Poster">
            </div>
            
            <div style="margin-top: 10px; font-size: 0.9rem; color: #666;">
                📝 <strong>Headline:</strong> ${poster.headline}<br>
                💬 <strong>Subtext:</strong> ${poster.subtext}<br>
                🎯 <strong>CTA:</strong> ${poster.cta}
            </div>
            
            <div class="image-actions">
                <button class="image-action-btn download" onclick="downloadPoster('${poster.image_url}')">
                    ⬇️ Download
                </button>
                <button class="image-action-btn variations" onclick="requestVariations()">
                    🔄 More Variations
                </button>
                <button class="image-action-btn restart" onclick="restartChat()">
                    ✏️ Start Over
                </button>
            </div>
            
            <div class="message-time">${time}</div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Display Multiple Variations
function displayVariations(posters) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';

    let gridHTML = '<div class="variations-grid">';
    posters.forEach((poster, index) => {
        gridHTML += `
            <div class="variation-item">
                <img src="${poster.image_url}" alt="Variation ${index + 1}">
                <div class="actions">
                    <button class="download-small" onclick="downloadPoster('${poster.image_url}')">
                        ⬇️ Download
                    </button>
                </div>
            </div>
        `;
    });
    gridHTML += '</div>';

    messageDiv.innerHTML = `
        <div class="message-bubble" style="max-width: 95%;">
            Here are ${posters.length} variations for you! 🎨
            ${gridHTML}
            <div style="margin-top: 15px;">
                <button class="image-action-btn restart" onclick="restartChat()" style="width: 100%;">
                    ✏️ Create New Poster
                </button>
            </div>
        </div>
    `;

    chatContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Request Variations
function requestVariations() {
    addBotMessage("How many variations would you like?");
    setTimeout(() => {
        addQuickReplies([
            { text: '2️⃣ Two', value: 'var_2' },
            { text: '3️⃣ Three', value: 'var_3' },
            { text: '5️⃣ Five', value: 'var_5' }
        ]);
    }, 500);
}

// Download Poster
function downloadPoster(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = `poster-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Restart Chat
function restartChat() {
    conversationState = {
        step: 'initial',
        userData: conversationState.userData,
        businessName: '',
        businessType: '',
        language: '',
        template: '',
        generatedPosters: [],
        conversationHistory: []
    };

    document.getElementById('chatContainer').innerHTML = '';
    sessionStorage.removeItem('conversationHistory');

    addBotMessage(`Let's create something new! 🎨\n\nWhat would you like to create?`);

    setTimeout(() => {
        addQuickReplies([
            { text: '🎉 Festival Poster', value: 'festival_poster' },
            { text: '💰 Sale/Offer Poster', value: 'sale_poster' },
            { text: '📦 Product Launch', value: 'product_poster' },
            { text: '📅 Event Poster', value: 'event_poster' }
        ]);
    }, 500);
}

// Send Message (Text Input)
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message) return;

    addUserMessage(message);
    input.value = '';

    // Handle based on current step
    if (conversationState.step === 'business_name') {
        conversationState.businessName = message;
        conversationState.step = 'business_type';

        setTimeout(() => {
            addBotMessage(`Nice! ${message} sounds great. 🎯\n\nWhat type of business is it?`);
            setTimeout(() => {
                addQuickReplies([
                    { text: '🏪 Retail', value: 'retail' },
                    { text: '🍽️ Restaurant', value: 'restaurant' },
                    { text: '💼 Services', value: 'services' },
                    { text: '🏭 Other', value: 'other' }
                ]);
            }, 500);
        }, 500);
    }
}

// Handle Enter Key
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Typing Indicator
function showTypingIndicator() {
    const chatContainer = document.getElementById('chatContainer');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="typing-indicator show">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatContainer.appendChild(typingDiv);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Loading Overlay
function showLoadingOverlay(text = "Creating your poster...") {
    document.getElementById('loadingOverlay').classList.add('show');
    document.getElementById('loadingSubtext').textContent = text;
}

function hideLoadingOverlay() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

// Scroll to Bottom
function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Save History
function saveHistory() {
    sessionStorage.setItem('conversationHistory', JSON.stringify(conversationState.conversationHistory));
}

// Logout
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        sessionStorage.clear();
        // Redirect to root which serves login.html
        window.location.href = '/';
    }
}
