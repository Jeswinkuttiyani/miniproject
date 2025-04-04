// script.js
document.addEventListener('DOMContentLoaded', function() {
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotContainer = document.getElementById('chatbot-container');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');
    const chatbotMessages = document.getElementById('chatbot-messages');

    chatbotToggle.addEventListener('click', function() {
        chatbotContainer.classList.toggle('visible');
    });

    chatbotClose.addEventListener('click', function() {
        chatbotContainer.classList.remove('visible');
    });

    chatbotSend.addEventListener('click', function() {
        sendMessage();
    });

    chatbotInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const userMessage = chatbotInput.value.trim();
        if (userMessage) {
            appendMessage(userMessage, 'user');
            chatbotInput.value = '';
            getBotResponse(userMessage);
        }
    }

    function appendMessage(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);
        messageElement.textContent = message;
        chatbotMessages.appendChild(messageElement);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    async function getBotResponse(userMessage) {
        const apiKey = 'AIzaSyANngrLpAav9F0mXtqDDY95p2foV88aCGE';
        const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;

        const requestBody = {
            contents: [{
                parts: [{
                    text: userMessage
                }]
            }]
        };

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            const botMessage = data.candidates[0].content.parts[0].text;
            appendMessage(botMessage, 'bot');
        } catch (error) {
            console.error('Error fetching bot response:', error);
            appendMessage('Sorry, something went wrong. Please try again.', 'bot');
        }
    }
});