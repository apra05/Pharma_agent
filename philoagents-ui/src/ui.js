import ApiService from './services/ApiService';
import WebSocketApiService from './services/WebSocketApiService';

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const gameModal = document.getElementById('game-modal');
    const closeGameModalBtn = document.getElementById('close-game-modal-btn');
    const heroLaunchBtn = document.getElementById('hero-launch-btn');
    const navLaunchBtn = document.getElementById('nav-launch-btn');
    const cardExploreTown = document.getElementById('card-explore-town');

    const floatingAgentBtn = document.getElementById('floating-agent-btn');
    const agentChatDrawer = document.getElementById('agent-chat-drawer');
    const closeDrawerBtn = document.getElementById('close-drawer-btn');
    const philosopherSelect = document.getElementById('philosopher-select');
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');

    // --- State Variables ---
    let activePhilosopher = { id: 'jnj', name: 'J&J Corporate Assistant' };
    const philosopherGreetings = {
        jnj: "Welcome! I am the Johnson & Johnson Assistant. I can help you understand our mission, divisions (Innovative Medicine and MedTech), history, or Our Credo. What would you like to know?"
    };

    // --- Modal Management (Phaser Simulator) ---
    const openGameModal = () => {
        gameModal.classList.remove('modal-hidden');
        // Enable Phaser inputs
        if (window.game) {
            if (window.game.input) {
                window.game.input.enabled = true;
                if (window.game.input.keyboard) {
                    window.game.input.keyboard.enabled = true;
                }
            }
            // Resume the Phaser scenes
            window.game.scene.scenes.forEach(scene => {
                if (scene.sys.isPaused()) {
                    scene.sys.resume();
                }
            });
            // Focus on Phaser canvas
            const canvas = document.querySelector('#game-container canvas');
            if (canvas) canvas.focus();
        }
    };

    const closeGameModal = () => {
        gameModal.classList.add('modal-hidden');
        // Disable Phaser inputs so typing in page doesn't affect Phaser character
        if (window.game) {
            if (window.game.input) {
                window.game.input.enabled = false;
                if (window.game.input.keyboard) {
                    window.game.input.keyboard.enabled = false;
                }
            }
            // Pause the Phaser scenes
            window.game.scene.scenes.forEach(scene => {
                if (scene.sys.isActive()) {
                    scene.sys.pause();
                }
            });
        }
    };

    // Event listeners for modal
    if (heroLaunchBtn) heroLaunchBtn.addEventListener('click', openGameModal);
    if (navLaunchBtn) navLaunchBtn.addEventListener('click', openGameModal);
    if (cardExploreTown) cardExploreTown.addEventListener('click', openGameModal);
    if (closeGameModalBtn) closeGameModalBtn.addEventListener('click', closeGameModal);

    // Escape key closes modal (only if game modal is open, and not in direct chat input)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !gameModal.classList.contains('modal-hidden') && document.activeElement !== chatInput) {
            closeGameModal();
        }
    });

    // --- Chat Drawer Management (Agent Chat) ---
    const toggleChatDrawer = () => {
        agentChatDrawer.classList.toggle('drawer-hidden');
        if (!agentChatDrawer.classList.contains('drawer-hidden')) {
            chatInput.focus();
        } else {
            WebSocketApiService.disconnect();
        }
    };

    if (floatingAgentBtn) floatingAgentBtn.addEventListener('click', toggleChatDrawer);
    if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', toggleChatDrawer);

    // --- Philosopher Dropdown Selection ---
    const updatePhilosopherSelection = () => {
        const selectedId = philosopherSelect.value;
        const selectedName = philosopherSelect.options[philosopherSelect.selectedIndex].text;
        activePhilosopher = { id: selectedId, name: selectedName };

        // Update placeholder
        chatInput.placeholder = `Ask ${selectedName} a question...`;

        // Clear previous messages and show philosopher greeting
        chatMessages.innerHTML = '';
        const greeting = philosopherGreetings[selectedId] || `Hello, I am ${selectedName}.`;
        appendMessage(greeting, 'agent-msg', selectedName);
    };

    if (philosopherSelect) {
        philosopherSelect.addEventListener('change', updatePhilosopherSelection);
    }

    // --- Message Appending ---
    const appendMessage = (text, className, senderName) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', className);

        const avatar = document.createElement('div');
        avatar.classList.add('message-avatar');
        avatar.innerText = senderName ? senderName[0] : (className === 'user-msg' ? 'U' : 'A');

        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');
        bubble.innerHTML = text.replace(/\n/g, '<br/>');

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(bubble);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return bubble;
    };

    const appendTypingIndicator = () => {
        const indicatorDiv = document.createElement('div');
        indicatorDiv.classList.add('chat-message', 'agent-msg');
        indicatorDiv.id = 'typing-indicator';

        const avatar = document.createElement('div');
        avatar.classList.add('message-avatar');
        avatar.innerText = activePhilosopher.name[0];

        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');
        
        const typing = document.createElement('div');
        typing.classList.add('typing-indicator');
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('typing-dot');
            typing.appendChild(dot);
        }
        
        bubble.appendChild(typing);
        indicatorDiv.appendChild(avatar);
        indicatorDiv.appendChild(bubble);
        chatMessages.appendChild(indicatorDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return indicatorDiv;
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    };

    // --- Message Sending and Websocket Chat ---
    const handleSendMessage = async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user message to UI
        appendMessage(message, 'user-msg', 'You');
        chatInput.value = '';

        // Add typing indicator
        appendTypingIndicator();

        // Prepare streaming bubble
        let streamBubble = null;
        let responseText = '';

        try {
            // Connect to websocket
            await WebSocketApiService.connect();
            removeTypingIndicator();

            streamBubble = appendMessage('', 'agent-msg', activePhilosopher.name);
            streamBubble.classList.add('streaming');

            const callbacks = {
                onMessage: (response) => {
                    if (streamBubble) {
                        streamBubble.classList.remove('streaming');
                        streamBubble.innerHTML = response.replace(/\n/g, '<br/>');
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                },
                onChunk: (chunk) => {
                    responseText += chunk;
                    if (streamBubble) {
                        streamBubble.innerHTML = responseText.replace(/\n/g, '<br/>');
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                },
                onStreamingStart: () => {},
                onStreamingEnd: () => {
                    if (streamBubble) {
                        streamBubble.classList.remove('streaming');
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    }
                    WebSocketApiService.disconnect();
                }
            };

            await WebSocketApiService.sendMessage(activePhilosopher, message, callbacks);

        } catch (error) {
            console.warn('Websocket failed, falling back to HTTP API:', error);
            removeTypingIndicator();

            try {
                const httpResponse = await ApiService.sendMessage(activePhilosopher, message);
                appendMessage(httpResponse, 'agent-msg', activePhilosopher.name);
            } catch (httpError) {
                console.error('HTTP API also failed:', httpError);
                appendMessage(
                    `I'm sorry, ${activePhilosopher.name} is currently offline. Please ensure your backend server is running on http://localhost:8000 and try again.`,
                    'agent-msg',
                    activePhilosopher.name
                );
            }
        }
    };

    if (chatSendBtn) chatSendBtn.addEventListener('click', handleSendMessage);
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                handleSendMessage();
            }
        });
    }

    // Initialize philosopher selector state
    updatePhilosopherSelection();
});
