const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');

function appendMessage(sender, text) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
    messageElement.innerText = text;
    chatBox.appendChild(messageElement);
    // Rola para o fim da caixa de chat
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage(url) {
    const pergunta = userInput.value.trim();
    if (pergunta === '') return;

    appendMessage('user', pergunta);
    userInput.value = '';

    const loadingMessage = document.createElement('div');
    loadingMessage.classList.add('message', 'bot-message');
    loadingMessage.innerText = 'Digitanto...';
    loadingMessage.id = 'loading-message';
    chatBox.appendChild(loadingMessage);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pergunta: pergunta })
        });

        const data = await response.json();
        
        const loader = document.getElementById('loading-message');
        if(loader) loader.remove();
        
        appendMessage('bot', data.resposta);

    } catch (error) {
        console.error('Erro ao enviar mensagem:', error);
        const loader = document.getElementById('loading-message');
        if(loader) loader.remove();
        appendMessage('bot', 'Ocorreu um erro de conexão.');
    }
}
